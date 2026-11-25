
"""Grafo asíncrono de chat con ejecución autenticada de herramientas MCP."""

import json
import re
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from langgraph.graph import END, START, StateGraph
from steward_datos.contratos import ContextoUsuario
from steward_datos.gobernanza import metricas as catalogo_metricas

from backend.api.cliente_mcp import ClienteMCP
from contratos.eventos_sse import (
    EstadoPaso,
    PasoEvent,
    RespuestaEvent,
    TipoRespuesta,
)

from .enrutador import _normalizar, clasificar_dominio
from .estado import EstadoChat, RolUsuario
from .herramientas_demo import (
    responder_fuera_alcance,
    responder_general,
)
from .presentacion_caso import formatear_caso


def _texto_resultado_mcp(resultado: Any) -> str:
    """Convierte la respuesta estructurada de MCP en texto legible."""

    datos = getattr(resultado, "structuredContent", None)

    if datos is None:
        datos = getattr(resultado, "structured_content", None)

    if datos is not None:
        return json.dumps(datos, ensure_ascii=False, indent=2, default=str)

    contenidos = getattr(resultado, "content", None) or []
    textos = [
        elemento.text
        for elemento in contenidos
        if hasattr(elemento, "text")
    ]

    if textos:
        salida = "\n".join(textos)

        try:
            return json.dumps(
                json.loads(salida),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        except (ValueError, TypeError):
            return salida

    return "La herramienta terminó sin devolver contenido."


def _formatear_resultado_calidad(resultado: Any) -> str:
    """Resume las reglas de calidad devueltas por MCP."""

    datos = getattr(resultado, "structuredContent", None)

    if datos is None:
        datos = getattr(resultado, "structured_content", None)

    if not isinstance(datos, dict):
        return _texto_resultado_mcp(resultado)

    reglas = datos.get("reglas") or []
    tablas = datos.get("tablas_con_reglas") or []

    dimensiones = sorted({
        regla.get("dimension")
        for regla in reglas
        if isinstance(regla, dict) and regla.get("dimension")
    })

    incumplidas = [
        regla for regla in reglas
        if isinstance(regla, dict)
        and regla.get("cumple_umbral") is False
    ]

    lineas = [
        "Resultados de calidad de datos",
        f"Reglas evaluadas: {len(reglas)}",
        f"Tablas evaluadas: {', '.join(map(str, tablas)) if tablas else 'No especificadas'}",
        f"Dimensiones registradas: {', '.join(dimensiones) if dimensiones else 'No especificadas'}",
        f"Reglas que no cumplen su umbral: {len(incumplidas)}",
    ]

    if incumplidas:
        lineas.extend(["", "Reglas que requieren atención:"])

        for regla in incumplidas:
            lineas.append(
                f"- {regla.get('regla_id', 'Sin ID')} "
                f"[{regla.get('tabla', 'Sin tabla')}]: "
                f"{regla.get('descripcion', 'Sin descripción')} "
                f"Resultado: {regla.get('porcentaje', 'No disponible')}% "
                f"(umbral: {regla.get('umbral', 'No disponible')})."
            )
    else:
        lineas.append("Todas las reglas cumplen su umbral.")

    lineas.extend([
        "",
        "Nota: estos resultados describen las reglas registradas; no constituyen una definición conceptual oficial del glosario.",
    ])

    return "\n".join(lineas)


def _extraer_termino(pregunta: str) -> str:
    """Extrae el término solicitado para una consulta del glosario."""

    patron = (
        r"(?:que significa|qué significa|definicion de|definición de|"
        r"define|glosario de)\s+(.+?)\s*[?.!]*$"
    )
    coincidencia = re.search(patron, pregunta.strip(), re.IGNORECASE)

    if coincidencia:
        return coincidencia.group(1).strip()

    return pregunta.strip()


ALIAS_DIMENSIONES = {
    "proveedor": ("proveedor", "proveedores"),
    "mes": ("mes",),
    "entidad": ("entidad", "entidades"),
    "centro_costo": ("centro de costo", "centro costo"),
    "moneda": ("moneda", "divisa"),
    "resultado": ("resultado",),
    "regla": ("regla", "reglas"),
    "efecto": ("efecto",),
    "tipo": ("tipo", "tipo de caso"),
    "responsable": ("responsable",),
    "estado": ("estado",),
    "segmento": ("segmento",),
    "tipo_persona": ("tipo de persona",),
    "mes_alta": ("mes de alta",),
}


def _extraer_dimensiones(texto: str, metrica: str) -> list[str]:
    """Extrae dimensiones solicitadas y valida contra el catálogo oficial."""

    catalogo = catalogo_metricas()["metricas"]
    definicion = catalogo.get(metrica, {})
    permitidas = definicion.get("dimensiones", {})

    encontradas = []

    for dimension in permitidas:
        alias = ALIAS_DIMENSIONES.get(
            dimension,
            (dimension.replace("_", " "),),
        )

        for nombre in alias:
            patron = (
                rf"\b(?:por|desglosado por|desglosada por|"
                rf"agrupado por|agrupada por)\s+"
                rf"(?:cada\s+)?{re.escape(nombre)}\b"
            )

            if re.search(patron, texto):
                encontradas.append(dimension)
                break

    return encontradas[:2]


def _seleccionar_herramienta(
    dominio: str,
    pregunta: str,
    caso_id: str | None,
) -> tuple[str | None, dict[str, Any], str | None]:
    """Selecciona una herramienta MCP para un único dominio."""

    texto = _normalizar(pregunta)

    if dominio == "analista":
        mapa_metricas = {
            "monto_facturado": (
                "monto_facturado",
                ("monto facturado", "total facturado", "importe facturado"),
            ),
            "numero_facturas": (
                "numero_facturas",
                ("numero de facturas", "cantidad de facturas", "facturas recibidas"),
            ),
            "facturas_rechazadas": (
                "facturas_rechazadas",
                ("facturas rechazadas",),
            ),
            "tasa_rechazo": (
                "tasa_rechazo",
                ("tasa de rechazo", "porcentaje de rechazo"),
            ),
            "tasa_conciliacion": (
                "tasa_conciliacion",
                ("tasa de conciliacion", "tasa de conciliación"),
            ),
            "tiempo_promedio_revision": (
                "tiempo_promedio_revision",
                ("tiempo promedio de revision", "tiempo promedio de revisión"),
            ),
            "facturas_por_regla": (
                "facturas_por_regla",
                ("facturas por regla", "facturas con hallazgos por regla"),
            ),
            "casos_pendientes": (
                "casos_pendientes",
                ("casos pendientes",),
            ),
            "monto_pagado": (
                "monto_pagado",
                ("monto pagado", "total pagado"),
            ),
            "pagos_a_tiempo": (
                "pagos_a_tiempo",
                ("pagos a tiempo", "pagos puntuales"),
            ),
            "monto_comprometido": (
                "monto_comprometido",
                ("monto comprometido",),
            ),
            "clientes_activos": (
                "clientes_activos",
                ("clientes activos",),
            ),
        }

        for metrica, (_, sinonimos) in mapa_metricas.items():
            if any(sinonimo in texto for sinonimo in sinonimos):
                return (
                    "obtener_metrica",
                    {
                        "entrada": {
                            "metrica": metrica,
                            "dimensiones": _extraer_dimensiones(texto, metrica),
                            "filtros": {},
                        }
                    },
                    None,
                )

        return (
            None,
            {},
            (
                "No pude identificar una métrica específica. "
                "Puedes preguntar por monto facturado, número de facturas, "
                "facturas rechazadas, tasa de rechazo, tasa de conciliación, "
                "tiempo promedio de revisión, facturas por regla, casos "
                "pendientes, monto pagado, pagos a tiempo, monto comprometido "
                "o clientes activos."
            ),
        )

    if dominio == "gobernanza":
        if any(
            frase in texto
            for frase in (
                "calidad de datos",
                "dimensiones de calidad",
                "dimension de calidad",
                "reglas de calidad",
            )
        ):
            return "consultar_calidad", {}, None

        if any(
            palabra in texto
            for palabra in ("glosario", "significa", "definición", "definicion")
        ):
            return (
                "consultar_glosario",
                {"termino": _extraer_termino(pregunta)},
                None,
            )

        if "calidad" in texto or "regla" in texto:
            return "consultar_calidad", {}, None

        return (
            "buscar_politicas",
            {"entrada": {"consulta": pregunta}},
            None,
        )

    if dominio == "casos":
        identificador = caso_id.strip() if caso_id else None
        encontrado = re.search(r"\b[FV]-\d{4,}\b", pregunta, re.IGNORECASE)

        if encontrado:
            en_pregunta = encontrado.group(0).upper()

            if identificador and identificador.upper() != en_pregunta:
                return (
                    None,
                    {},
                    "El identificador de la pregunta no coincide con el caso abierto. "
                    "Abre el caso correcto para continuar.",
                )

            identificador = en_pregunta

        if identificador:
            return (
                "consultar_caso",
                {"entrada": {"caso_id": identificador.upper()}},
                None,
            )

        if "factura" in texto:
            return (
                "buscar_facturas",
                {"entrada": {"limite": 20}},
                None,
            )

        if not caso_id or not caso_id.strip():
            return (
                None,
                {},
                "Para consultar un caso necesito su identificador. "
                "Indícame el caso_id para continuar.",
            )

        return (
            "consultar_caso",
            {"entrada": {"caso_id": caso_id.strip()}},
            None,
        )

    raise ValueError(f"Dominio no soportado: {dominio}")


def obtener_tipo_respuesta(estado: EstadoChat) -> TipoRespuesta:
    """Determina el tipo del evento de respuesta final."""

    dominio = estado["dominio"]

    if dominio == "gobernanza":
        return TipoRespuesta.POLITICAS

    if dominio == "casos":
        return TipoRespuesta.DATOS

    if dominio == "analista":
        return TipoRespuesta.DATOS

    return TipoRespuesta.INFORMACION_GENERAL


class FlujoChat:
    """Orquestador asíncrono del grafo de chat."""

    def __init__(self, cliente_mcp: ClienteMCP | None = None):
        self._cliente_mcp = cliente_mcp or ClienteMCP()

        grafo = StateGraph(EstadoChat)

        grafo.add_node("enrutador", clasificar_dominio)
        grafo.add_node("ejecutor", self._ejecutar_dominios)

        grafo.add_edge(START, "enrutador")
        grafo.add_edge("enrutador", "ejecutor")
        grafo.add_edge("ejecutor", END)

        self._grafo = grafo.compile()

    async def _ejecutar_dominios(self, estado: EstadoChat) -> dict:
        """Ejecuta los dominios y combina los resultados."""

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

            return {
                "resultados_dominio": [resultado],
                "dominios_ejecutados": [],
                "respuesta": resultado["respuesta"],
                "fuentes": [],
                # Textos fijos de orientación o rechazo: no son respuestas inventadas.
                "simulado": False,
            }

        dominios_validos = {"gobernanza", "casos", "analista"}

        if dominio not in dominios_validos:
            raise ValueError(f"Dominio no soportado: {dominio}")

        if dominios != [dominio]:
            raise ValueError(
                f"El dominio {dominio} debe coincidir con su único dominio objetivo."
            )

        usuario = ContextoUsuario(
            usuario_id=estado["usuario_id"],
            rol=estado["rol"],
        )

        resultados = []
        fuentes = []
        ejecutados = []
        respuestas = []

        for dominio_objetivo in dominios:
            herramienta, argumentos, aviso = _seleccionar_herramienta(
                dominio_objetivo,
                pregunta,
                estado.get("caso_id"),
            )

            if aviso:
                resultados.append({
                    "dominio": dominio_objetivo,
                    "respuesta": aviso,
                    "fuentes": [],
                    "ejecutado": False,
                })
                respuestas.append(aviso)
                continue

            resultado_mcp = await self._cliente_mcp.ejecutar(
                herramienta,
                argumentos,
                usuario,
            )

            respuesta = _texto_resultado_mcp(resultado_mcp)
            detalle_paso = None

            # S3-16: conservar el detalle de la métrica y el SQL generado.
            if herramienta == "obtener_metrica":
                datos = getattr(resultado_mcp, "structuredContent", None)

                if datos is None:
                    datos = getattr(resultado_mcp, "structured_content", None)

                if isinstance(datos, dict):
                    detalle_paso = (
                        f"Métrica: {datos.get('etiqueta', datos.get('metrica', 'No disponible'))}\n"
                        f"Definición: {datos.get('definicion', 'No disponible')}\n"
                        f"SQL generado:\n{datos.get('sql', 'No disponible')}"
                    )

            # Dev: conservar el formato de presentación de los casos.
            if herramienta == "consultar_caso":
                respuesta = formatear_caso(resultado_mcp) or respuesta

            # Conservar el formato especializado de calidad de datos.
            if herramienta == "consultar_calidad":
                respuesta = _formatear_resultado_calidad(resultado_mcp)

            resultados.append({
                "dominio": dominio_objetivo,
                "herramienta": herramienta,
                "respuesta": respuesta,
                "detalle_paso": detalle_paso,
                "fuentes": [herramienta],
                "ejecutado": True,
            })

            respuestas.append(
                f"Resultado de {herramienta}:\n{respuesta}"
            )
            fuentes.append(herramienta)
            ejecutados.append(dominio_objetivo)

        return {
            "resultados_dominio": resultados,
            "dominios_ejecutados": ejecutados,
            "respuesta": "\n\n".join(respuestas),
            "fuentes": list(dict.fromkeys(fuentes)),
            "simulado": False,
        }

    async def astream_chat(
        self,
        pregunta: str,
        usuario_id: str,
        rol: RolUsuario,
        historial: list[dict] | None = None,
        caso_id: str | None = None,
    ) -> AsyncIterator[PasoEvent | RespuestaEvent]:
        """Ejecuta el grafo y emite eventos tipados de manera asíncrona."""

        if not isinstance(pregunta, str) or not pregunta.strip():
            raise ValueError("La pregunta debe ser texto no vacío.")

        if not isinstance(usuario_id, str) or not usuario_id.strip():
            raise ValueError("El usuario debe tener un identificador válido.")

        if rol not in ("analista", "administrador"):
            raise ValueError("El rol del usuario no es válido.")

        inicio = perf_counter()

        estado: EstadoChat = {
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

            async for actualizacion in self._grafo.astream(
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
                        resultados = cambios.get("resultados_dominio", [])

                        detalle = next(
                            (
                                resultado.get("detalle_paso")
                                for resultado in resultados
                                if resultado.get("detalle_paso")
                            ),
                            None,
                        )

                        yield PasoEvent(
                            id="ejecutor",
                            texto="Consulta terminada",
                            detalle=detalle,
                            estado=EstadoPaso.COMPLETADO,
                        )

            yield RespuestaEvent(
                respuesta=estado["respuesta"],
                caso_id=caso_id,
                simulado=estado.get("simulado", False),
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
