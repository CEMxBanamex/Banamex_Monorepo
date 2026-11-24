"""Grafo de chat con enrutamiento y herramientas falsas."""

from time import perf_counter
from typing import Iterator

from langgraph.graph import END, START, StateGraph

from contratos.eventos_sse import (
    EstadoPaso,
    PasoEvent,
    RespuestaEvent,
    TipoRespuesta,
)

from .estado import EstadoChat, RolUsuario
from .enrutador import clasificar_dominio
from .herramientas_demo import (
    buscar_politicas,
    consultar_datos,
    consultar_casos,
    responder_general,
    responder_fuera_alcance,
)


HERRAMIENTAS = {
    "gobernanza": buscar_politicas,
    "consultas": consultar_datos,
    "casos": consultar_casos,
}



def ejecutar_dominios(estado: EstadoChat) -> dict:
    """Ejecuta los dominios correspondientes y combina sus resultados."""

    dominio = estado["dominio"]
    pregunta = estado["pregunta"]
    dominios = estado.get("dominios_objetivo", [])

    if dominio in ("general", "fuera_de_alcance"):
        if dominios:
            raise ValueError(
                f"El dominio {dominio} no debe tener dominios objetivo."
            )

        if dominio == "general":
            resultado = responder_general(pregunta)
        else:
            resultado = responder_fuera_alcance(pregunta)

        resultados = [resultado]

    else:
        if not dominios or len(dominios) > 2:
            raise ValueError(
                "Debe haber uno o dos dominios objetivo."
            )

        dominios_invalidos = [
            objetivo
            for objetivo in dominios
            if objetivo not in HERRAMIENTAS
        ]

        if dominios_invalidos:
            raise ValueError(
                f"Dominios no soportados: {dominios_invalidos}"
            )

        if dominio == "mixta":
            if len(dominios) != 2 or len(set(dominios)) != 2:
                raise ValueError(
                    "Una intención mixta debe tener exactamente "
                    "dos dominios objetivo diferentes."
                )

        elif dominio in HERRAMIENTAS:
            if dominios != [dominio]:
                raise ValueError(
                    f"El dominio {dominio} debe coincidir "
                    "con su único dominio objetivo."
                )

        else:
            raise ValueError(f"Dominio no soportado: {dominio}")

        resultados = []

        for dominio_objetivo in dominios:
            herramienta = HERRAMIENTAS[dominio_objetivo]
            resultados.append(herramienta(pregunta))

    respuesta = "\n\n".join(
        resultado["respuesta"] for resultado in resultados
    )

    fuentes = list(dict.fromkeys(
        fuente
        for resultado in resultados
        for fuente in resultado["fuentes"]
    ))

    return {
        "resultados_dominio": resultados,
        "dominios_ejecutados": [
            resultado["dominio"]
            for resultado in resultados
            if resultado["dominio"] in HERRAMIENTAS
        ],
        "respuesta": respuesta,
        "fuentes": fuentes,
    }


def obtener_tipo_respuesta(estado: EstadoChat) -> TipoRespuesta:
    """Determina el tipo del evento de respuesta final."""

    dominio = estado["dominio"]

    if dominio == "gobernanza":
        return TipoRespuesta.POLITICAS

    if dominio in ("consultas", "casos"):
        return TipoRespuesta.DATOS

    if dominio == "mixta":
        return TipoRespuesta.MIXTA

    return TipoRespuesta.INFORMACION_GENERAL


class FlujoChat:
    """Orquestador del grafo de chat."""

    def __init__(self):
        grafo = StateGraph(EstadoChat)

        grafo.add_node("enrutador", clasificar_dominio)
        grafo.add_node("ejecutor", ejecutar_dominios)

        grafo.add_edge(START, "enrutador")
        grafo.add_edge("enrutador", "ejecutor")
        grafo.add_edge("ejecutor", END)

        self._grafo = grafo.compile()


    def stream_chat(
        self,
        pregunta: str,
        usuario_id: str,
        rol: RolUsuario,
        historial: list[dict] | None = None,
        caso_id: str | None = None,
    ) -> Iterator[PasoEvent | RespuestaEvent]:
        """Ejecuta el chat y emite eventos tipados."""

        if not isinstance(pregunta, str) or not pregunta.strip():
            raise ValueError("La pregunta debe ser texto no vacío.")

        if not isinstance(usuario_id, str) or not usuario_id.strip():
            raise ValueError("El usuario debe tener un identificador válido.")

        if rol not in ("analista", "administrador"):
            raise ValueError("El rol del usuario no es válido.")

        inicio = perf_counter()

        estado = {
            "pregunta": pregunta.strip(),
            "usuario_id": usuario_id.strip(),
            "rol": rol,
            "historial": historial or [],
            "caso_id": caso_id,
        }

        etapa_actual = "enrutador"

        try:
            yield PasoEvent(
                id="enrutador",
                texto="Clasificando solicitud",
                estado=EstadoPaso.EN_CURSO,
            )

            for actualizacion in self._grafo.stream(
                estado,
                stream_mode="updates",
            ):
                for nodo, cambios in actualizacion.items():
                    estado.update(cambios)

                    if nodo == "enrutador":
                        etapa_actual = "ejecutor"
                        yield PasoEvent(
                            id="enrutador",
                            texto="Clasificando solicitud",
                            estado=EstadoPaso.COMPLETADO,
                        )

                        yield PasoEvent(
                            id="ejecutor",
                            texto="Consultando información",
                            estado=EstadoPaso.EN_CURSO,
                        )

                    elif nodo == "ejecutor":
                        yield PasoEvent(
                            id="ejecutor",
                            texto="Consultando información",
                            estado=EstadoPaso.COMPLETADO,
                        )

            yield RespuestaEvent(
                respuesta=estado["respuesta"],
                caso_id=caso_id,
                simulado=True,
                duracion_ms=int((perf_counter() - inicio) * 1000),
                tipo=obtener_tipo_respuesta(estado),
                fuentes=estado.get("fuentes", []),
            )

        except Exception:
            yield PasoEvent(
                id=etapa_actual,
                texto="Error al procesar solicitud",
                estado=EstadoPaso.ERROR,
            )
            raise
