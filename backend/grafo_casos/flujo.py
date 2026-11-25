"""Grafo de casos de prueba con decisión explícita del analista."""

from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from steward_datos.contratos import FacturaExtraida, Resultado

from .herramientas_demo import extraer_factura_demo, validar_factura_demo
from .redactor import redactar_explicacion_caso


class DecisionAnalista(BaseModel):
    """Contrato de entrada para la decisión humana."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    resultado: Literal["aceptado", "rechazado"]
    motivo: str = Field(min_length=1)


class EstadoCaso(TypedDict, total=False):
    """Estado compartido entre los nodos del grafo."""

    caso_id: str
    factura: dict
    resultado_sugerido: Resultado
    motivo: str
    hallazgos: list[dict]
    explicacion: str
    decision_analista: dict


def extractor(_: EstadoCaso) -> dict:
    """Extrae una factura de demostración."""
    factura = extraer_factura_demo()
    return {"factura": factura.model_dump(mode="json")}


def validador(estado: EstadoCaso) -> dict:
    """Valida la estructura de la factura y sus importes."""
    datos_factura = estado.get("factura")

    if not isinstance(datos_factura, dict):
        raise ValueError("El estado no contiene una factura válida.")

    try:
        factura = FacturaExtraida.model_validate(datos_factura)
    except ValidationError as exc:
        raise ValueError(
            "La estructura de la factura no cumple el contrato."
        ) from exc

    resultado, motivo = validar_factura_demo(factura)

    return {
        "resultado_sugerido": resultado,
        "motivo": motivo,
    }


def redactor(estado: EstadoCaso) -> dict:
    """Construye la explicación que recibirá el analista."""
    motivo = estado.get("motivo")
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError("No existe un motivo válido para redactar.")

    explicacion, _ = redactar_explicacion_caso(
        estado["caso_id"], estado["resultado_sugerido"], motivo, estado.get("hallazgos"),
    )
    return {"explicacion": explicacion}


def revision_analista(estado: EstadoCaso) -> dict:
    """Interrumpe el grafo hasta recibir una decisión humana."""
    respuesta = interrupt({
        "caso_id": estado["caso_id"],
        "resultado_sugerido": estado["resultado_sugerido"],
        "explicacion": estado["explicacion"],
    })

    decision = DecisionAnalista.model_validate(respuesta)

    return {
        "decision_analista": decision.model_dump()
    }


class FlujoCasos:
    """Orquestador del grafo de demostración."""

    def __init__(self):
        grafo = StateGraph(EstadoCaso)

        for nodo in (extractor, validador, redactor, revision_analista):
            grafo.add_node(nodo)

        grafo.add_edge(START, "extractor")
        grafo.add_edge("extractor", "validador")
        grafo.add_edge("validador", "redactor")
        grafo.add_edge("redactor", "revision_analista")
        grafo.add_edge("revision_analista", END)

        self._grafo = grafo.compile(checkpointer=InMemorySaver())

    @staticmethod
    def _config(caso_id: str) -> dict:
        """Valida el identificador y construye la configuración."""
        if not isinstance(caso_id, str) or not caso_id.strip():
            raise ValueError(
                "El identificador del caso debe ser texto no vacío."
            )

        return {"configurable": {"thread_id": caso_id.strip()}}

    def procesar_caso(self, caso_id: str) -> dict:
        """Inicia un caso nuevo y evita reutilizar identificadores."""
        config = self._config(caso_id)

        if self._grafo.get_state(config).values:
            raise ValueError("El caso ya fue iniciado.")

        return self._grafo.invoke(
            {"caso_id": caso_id.strip()},
            config,
        )

    def reanudar_caso(self, caso_id: str, decision: dict) -> dict:
        """Reanuda un caso pausado con una decisión humana válida."""
        config = self._config(caso_id)

        if not self._grafo.get_state(config).interrupts:
            raise ValueError(
                "El caso no está esperando una decisión."
            )

        datos = DecisionAnalista.model_validate(decision).model_dump()

        return self._grafo.invoke(
            Command(resume=datos),
            config,
        )
