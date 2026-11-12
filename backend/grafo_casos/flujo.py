"""Grafo de casos de prueba, con una decisión explícita del analista."""
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, ConfigDict, Field

from datos.steward_datos.contratos import FacturaExtraida, Resultado

from .herramientas_demo import extraer_factura_demo, redactar_demo, validar_factura_demo


class DecisionAnalista(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    resultado: Literal["aceptado", "rechazado"]
    motivo: str = Field(min_length=1)


class EstadoCaso(TypedDict, total=False):
    caso_id: str
    factura: dict
    resultado_sugerido: Resultado
    motivo: str
    explicacion: str
    decision_analista: dict


def extractor(_: EstadoCaso) -> dict:
    return {"factura": extraer_factura_demo().model_dump(mode="json")}


def validador(estado: EstadoCaso) -> dict:
    factura = FacturaExtraida.model_validate(estado["factura"])
    resultado, motivo = validar_factura_demo(factura)
    return {"resultado_sugerido": resultado, "motivo": motivo}


def redactor(estado: EstadoCaso) -> dict:
    return {"explicacion": redactar_demo(estado["motivo"])}


def revision_analista(estado: EstadoCaso) -> dict:
    respuesta = interrupt({
        "caso_id": estado["caso_id"],
        "resultado_sugerido": estado["resultado_sugerido"],
        "explicacion": estado["explicacion"],
    })
    return {"decision_analista": DecisionAnalista.model_validate(respuesta).model_dump()}


class FlujoCasos:
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
    def _config(caso_id: str):
        if not caso_id.strip():
            raise ValueError("El identificador del caso es obligatorio.")
        return {"configurable": {"thread_id": caso_id}}

    def procesar_caso(self, caso_id: str) -> dict:
        config = self._config(caso_id)
        if self._grafo.get_state(config).values:
            raise ValueError("El caso ya fue iniciado.")
        return self._grafo.invoke({"caso_id": caso_id}, config)

    def reanudar_caso(self, caso_id: str, decision: dict) -> dict:
        config = self._config(caso_id)
        if not self._grafo.get_state(config).interrupts:
            raise ValueError("El caso no está esperando una decisión.")
        datos = DecisionAnalista.model_validate(decision).model_dump()
        return self._grafo.invoke(Command(resume=datos), config)
