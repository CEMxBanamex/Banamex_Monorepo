"""Flujo local con extracción Ollama, herramientas de Datos y revisión humana."""
from datetime import date
import hashlib
import logging
from pathlib import Path
import re
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from steward_datos.contratos import ContextoUsuario

from .extraccion import extraer_campos_factura
from .flujo import DecisionAnalista
from .herramientas_reales import HerramientasReales


logger = logging.getLogger(__name__)


class EstadoReal(TypedDict, total=False):
    caso_id: str
    archivo: str
    fecha: str
    sha256: str
    factura: dict
    resultado: dict
    politicas: dict
    fragmentos: dict
    explicacion: str
    decision_analista: dict
    evento_decision_id: int | None


def redactar_evidencia(resultado: dict, politicas: dict) -> str:
    # La explicación conserva el resultado de código; no necesita otra inferencia.
    lineas = [resultado["motivo"]]
    for item in politicas["hallazgos"]:
        h, p = item["hallazgo"], item["politica"]
        regla = f"{h['regla_id']} v{h['regla_version']}"
        if all(p[campo].strip() for campo in ("politica_id", "version", "seccion")):
            cita = f"{regla} · {p['politica_id']} v{p['version']} §{p['seccion']}"
            fuente = "Fragmento recuperado." if p["origen"] == "rag" else "Solo cita del catálogo; sin fragmento recuperado."
        else:
            cita = regla
            fuente = "Política incompleta. Revisión humana requerida."

        detalle = f"{h['titulo']}: {h['texto']} ({cita}). {fuente}"
        if h.get("evidencia"):
            detalle += f" Evidencia: {h['evidencia']}."
        elif h.get("campos"):
            detalle += f" Campos que se deben verificar: {', '.join(h['campos'])}."
        for etiqueta, valor in h.get("cifras") or []:
            detalle += f" {etiqueta}: {valor}."
        lineas.append(detalle)
    return "\n".join(lineas + ["La decisión final corresponde al analista."])


class FlujoCasosReal:
    def __init__(self, usuario: ContextoUsuario, *, herramientas=None, extraer=extraer_campos_factura, checkpointer=None):
        if usuario.rol != "analista":
            raise PermissionError("El flujo requiere un analista autenticado por el llamador.")
        self.usuario = usuario
        self.tools = herramientas if herramientas is not None else HerramientasReales(usuario)
        self.extraer = extraer
        self._threads = {}
        grafo = StateGraph(EstadoReal)
        for nombre in ("extractor", "validador", "politicas", "redactor", "guardar", "revision", "cerrar"):
            grafo.add_node(nombre, getattr(self, "_" + nombre))
        nombres = [START, "extractor", "validador", "politicas", "redactor", "guardar", "revision", "cerrar", END]
        for desde, hasta in zip(nombres, nombres[1:]):
            grafo.add_edge(desde, hasta)
        self._grafo = grafo.compile(checkpointer=checkpointer if checkpointer is not None else InMemorySaver())

    def _config(self, caso_id):
        if caso_id not in self._threads:
            raise ValueError("El caso no fue iniciado por esta instancia.")
        return {"configurable": {"thread_id": self._threads[caso_id]}}

    def procesar_caso(self, caso_id: str, archivo: str, *, fecha_recepcion: date | None = None):
        if not re.fullmatch(r"F-[0-9]{4,10}", caso_id):
            raise ValueError("Usar un identificador F- seguido de 4 a 10 dígitos.")
        ruta = Path(archivo).resolve(strict=True)
        if not ruta.is_file():
            raise ValueError("Seleccionar un archivo de imagen.")
        if caso_id in self._threads:
            raise ValueError("El caso ya fue iniciado.")
        sha = hashlib.sha256(ruta.read_bytes()).hexdigest()
        self._threads[caso_id] = self.tools.iniciar(caso_id)
        try:
            return self._grafo.invoke({"caso_id": caso_id, "archivo": str(ruta), "sha256": sha,
                                       "fecha": (fecha_recepcion or date.today()).isoformat()}, self._config(caso_id))
        except Exception:
            self.tools.error(caso_id)
            raise

    def reanudar_caso(self, caso_id: str, decision: dict):
        datos = DecisionAnalista.model_validate(decision).model_dump()
        config = self._config(caso_id)
        if not self._grafo.get_state(config).interrupts:
            raise ValueError("El caso no está esperando una decisión.")
        return self._grafo.invoke(Command(resume=datos), config)

    def _extractor(self, estado):
        factura = self.extraer(estado["archivo"])
        if hashlib.sha256(Path(estado["archivo"]).read_bytes()).hexdigest() != estado["sha256"]:
            raise ValueError("La imagen cambió durante la extracción.")
        return {"factura": factura.model_dump(mode="json")}

    def _validador(self, estado):
        resultado = self.tools.validar(estado["caso_id"], estado["factura"], estado["sha256"], estado["fecha"])
        return {"resultado": resultado.model_dump(mode="json")}

    def _politicas(self, estado):
        salida, fragmentos = self.tools.politicas(estado["resultado"], estado["fecha"])
        return {"politicas": salida, "fragmentos": fragmentos}

    def _redactor(self, estado):
        resultado = estado["resultado"]
        politicas = estado["politicas"]
        if any(not h["politica_id"].strip() for h in resultado["hallazgos"]):
            resultado = {**resultado, "resultado_sugerido": "humana"}
            politicas = {**politicas, "resultado_sugerido": "humana"}
        return {"resultado": resultado, "politicas": politicas, "explicacion": redactar_evidencia(resultado, politicas)}

    def _guardar(self, estado):
        try:
            self.tools.guardar(estado["caso_id"], estado["factura"], estado["resultado"], estado["explicacion"], estado["fragmentos"])
        except Exception:
            logger.exception("Falló el registro de hallazgos del caso %s", estado["caso_id"])
            raise
        return {}

    def _revision(self, estado):
        decision = interrupt({"caso_id": estado["caso_id"], "factura": estado["factura"],
                              "resultado_sugerido": estado["resultado"]["resultado_sugerido"],
                              "explicacion": estado["explicacion"], "politicas": estado["politicas"]})
        return {"decision_analista": DecisionAnalista.model_validate(decision).model_dump()}

    def _cerrar(self, estado):
        return {"evento_decision_id": self.tools.cerrar(estado["caso_id"], estado["decision_analista"])}
