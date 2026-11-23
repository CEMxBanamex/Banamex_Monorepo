"""Endpoint de bitácora de auditoría para la interfaz de analistas (tarea S1-36).

Proporciona el stub para la pantalla de bitácora, con filtros por caso, usuario,
acción y fechas, paginación y detalle para filas expandibles.
"""
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

# --- Modelos Pydantic (Contratos de Bitácora) ---

TonoEvento = Literal["exito", "adv", "info", "error"]


class DetalleExtraBitacora(BaseModel):
    texto: Optional[str] = None
    antes: Optional[str] = None
    despues: Optional[str] = None


class EventoBitacoraOut(BaseModel):
    id: str
    fecha: str
    caso: Optional[str] = None
    quien: str
    ini: Optional[str] = None
    accion: str
    tono: TonoEvento
    detalle: str
    regla: Optional[str] = None
    extra: Optional[DetalleExtraBitacora] = None


class FiltrosDisponibles(BaseModel):
    casos: list[str]
    acciones: list[str]
    usuarios: list[str]


class ListarBitacoraSalida(BaseModel):
    eventos: list[EventoBitacoraOut]
    total: int
    limite: int
    offset: int
    filtros: FiltrosDisponibles


# --- Datos Fijos / Mocks para Stubs (Fase 0/1) ---

EVENTOS_MOCK: list[dict] = [
    {
        "id": "EV-3112", "fecha": "26 oct 2026 · 11:58", "caso": "F-1041", "quien": "Ana López", "ini": "AL",
        "accion": "Confirmación", "tono": "exito", "detalle": "Confirmó el resultado sugerido: Aceptado", "regla": None,
    },
    {
        "id": "EV-3108", "fecha": "26 oct 2026 · 11:42", "caso": "F-1042", "quien": "Ana López", "ini": "AL",
        "accion": "Corrección de dato", "tono": "adv", "detalle": "Campo fecha corregido", "regla": "R-003 · v1.0",
        "extra": {
            "texto": "Se corrigió el campo fecha después de verificarlo contra el documento original (página 1).",
            "antes": "12/03/2026",
            "despues": "12/08/2026",
        },
    },
    {
        "id": "EV-3104", "fecha": "26 oct 2026 · 10:15", "caso": "F-1042", "quien": "Agente", "ini": "AG",
        "accion": "Regla aplicada", "tono": "info", "detalle": "El total no coincide con subtotal más impuestos", "regla": "R-014 · v2.1",
    },
    {
        "id": "EV-3103", "fecha": "26 oct 2026 · 10:15", "caso": "F-1042", "quien": "Agente", "ini": "AG",
        "accion": "Regla aplicada", "tono": "info", "detalle": "Fecha leída con baja confianza (62 %)", "regla": "R-003 · v1.0",
    },
    {
        "id": "EV-3102", "fecha": "26 oct 2026 · 10:14", "caso": "F-1042", "quien": "Agente", "ini": "AG",
        "accion": "Extracción de datos", "tono": "info", "detalle": "6 campos extraídos de factura_1042.pdf", "regla": None,
    },
    {
        "id": "EV-3087", "fecha": "25 oct 2026 · 17:30", "caso": "F-1040", "quien": "Luis Ortega", "ini": "LO",
        "accion": "Escalamiento", "tono": "error", "detalle": "Caso escalado a supervisión", "regla": "R-021 · v1.2",
    },
    {
        "id": "EV-3079", "fecha": "25 oct 2026 · 16:02", "caso": "V-0206", "quien": "Agente", "ini": "AG",
        "accion": "Error de procesamiento", "tono": "error", "detalle": "No se pudo leer registros_prueba.csv", "regla": None,
    },
]


def crear_router(get_usuario_actual: Callable) -> APIRouter:
    router = APIRouter(prefix="/bitacora", tags=["bitácora"])

    @router.get("", response_model=ListarBitacoraSalida)
    def listar_bitacora(
        caso: Optional[str] = None,
        quien: Optional[str] = None,
        accion: Optional[str] = None,
        limite: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        _=Depends(get_usuario_actual),
    ):
        filtrados = EVENTOS_MOCK
        if caso:
            c_upper = caso.strip().upper()
            filtrados = [e for e in filtrados if e.get("caso") == c_upper]
        if quien:
            filtrados = [e for e in filtrados if quien.lower() in e.get("quien", "").lower()]
        if accion:
            filtrados = [e for e in filtrados if accion.lower() in e.get("accion", "").lower()]

        total = len(filtrados)
        paginados = filtrados[offset: offset + limite]

        filtros_info = FiltrosDisponibles(
            casos=sorted(list({e.get("caso") for e in EVENTOS_MOCK if e.get("caso")})),
            acciones=sorted(list({e.get("accion") for e in EVENTOS_MOCK if e.get("accion")})),
            usuarios=sorted(list({e.get("quien") for e in EVENTOS_MOCK if e.get("quien")})),
        )

        return ListarBitacoraSalida(
            eventos=paginados,
            total=total,
            limite=limite,
            offset=offset,
            filtros=filtros_info,
        )

    return router
