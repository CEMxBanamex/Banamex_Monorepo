"""Endpoints de casos para la interfaz de analistas (tarea S1-36).

Proporciona los stubs para la bandeja de casos, detalle de factura/validación,
subida de casos y registro de decisión humana.
"""
from datetime import datetime
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# --- Modelos Pydantic (Contratos de Casos) ---

TipoCaso = Literal["Factura", "Validación con políticas"]
EstadoCaso = Literal["revision", "revisado", "procesando", "error"]
ResultadoCaso = Optional[Literal["aceptado", "rechazado", "humana"]]


class CasoResumen(BaseModel):
    id: str
    archivo: str
    tipo: TipoCaso
    estado: EstadoCaso
    resultado: ResultadoCaso
    fecha: str
    responsable: str
    variante: Optional[str] = "normal"


class MetricasBandeja(BaseModel):
    total: int
    en_revision: int
    revisados: int
    procesando: int


class ListarCasosSalida(BaseModel):
    casos: list[CasoResumen]
    metricas: MetricasBandeja


class CampoDetalle(BaseModel):
    id: str
    etiqueta: str
    valor: Optional[str]
    conf: Optional[int] = Field(None, ge=0, le=100)
    valor_corregido: Optional[str] = None


class HallazgoDetalle(BaseModel):
    id: str
    tipo: Literal["error", "adv", "info"]
    titulo: str
    texto: str
    cifras: Optional[list[list[str]]] = None
    regla: str
    version: str
    evidencia: str


class EventoDetalle(BaseModel):
    id: str
    fecha: str
    quien: str
    accion: str
    tono: Literal["exito", "adv", "info", "error"]
    detalle: str
    regla: Optional[str] = None
    extra: Optional[dict] = None


class CasoDetalle(BaseModel):
    id: str
    archivo: str
    tipo: TipoCaso
    estado: EstadoCaso
    resultado_sugerido: ResultadoCaso
    resultado_final: Optional[ResultadoCaso] = None
    explicacion: Optional[str] = None
    fecha: str
    responsable: str
    variante: Optional[str] = "normal"
    campos: list[CampoDetalle] = Field(default_factory=list)
    hallazgos: list[HallazgoDetalle] = Field(default_factory=list)
    eventos: list[EventoDetalle] = Field(default_factory=list)


class UrlSubidaEntrada(BaseModel):
    nombre_archivo: str
    tipo_documento: TipoCaso


class UrlSubidaSalida(BaseModel):
    upload_url: str
    s3_key: str
    expira_en_segundos: int = 900


class CrearCasoEntrada(BaseModel):
    archivo: str
    tipo: TipoCaso
    s3_key: Optional[str] = None


class CrearCasoSalida(BaseModel):
    id: str
    estado: EstadoCaso
    mensaje: str


class DecisionCasoEntrada(BaseModel):
    accion: Literal["confirmar", "corregir", "escalar"]
    resultado: Optional[Literal["aceptado", "rechazado"]] = None
    campos_corregidos: Optional[dict[str, str]] = None
    comentario: Optional[str] = None


class DecisionCasoSalida(BaseModel):
    caso_id: str
    estado: EstadoCaso
    resultado_final: Optional[str]
    evento_id: str
    mensaje: str


# --- Datos Fijos / Mocks para Stubs (Fase 0/1) ---

CASOS_MOCK: list[dict] = [
    {"id": "F-1042", "archivo": "factura_1042.pdf", "tipo": "Factura", "estado": "revision", "resultado": "humana", "fecha": "26 oct 2026", "responsable": "Ana López", "variante": "normal"},
    {"id": "F-1041", "archivo": "factura_1041.png", "tipo": "Factura", "estado": "revisado", "resultado": "aceptado", "fecha": "26 oct 2026", "responsable": "Ana López", "variante": "sinHallazgos"},
    {"id": "F-1040", "archivo": "factura_1040.jpg", "tipo": "Factura", "estado": "revisado", "resultado": "rechazado", "fecha": "25 oct 2026", "responsable": "Luis Ortega", "variante": "normal"},
    {"id": "V-0207", "archivo": "clientes_octubre.xlsx", "tipo": "Validación con políticas", "estado": "procesando", "resultado": None, "fecha": "26 oct 2026", "responsable": "Diego Ruiz"},
    {"id": "V-0206", "archivo": "registros_prueba.csv", "tipo": "Validación con políticas", "estado": "error", "resultado": None, "fecha": "25 oct 2026", "responsable": "Diego Ruiz", "variante": "error"},
]

DETALLES_MOCK: dict[str, dict] = {
    "F-1042": {
        "id": "F-1042", "archivo": "factura_1042.pdf", "tipo": "Factura", "estado": "revision", "resultado_sugerido": "humana", "resultado_final": None,
        "explicacion": "Se sugiere revisión humana porque el total no coincide con la suma de subtotal e impuestos, y la fecha presenta baja confianza.",
        "fecha": "26 oct 2026", "responsable": "Ana López", "variante": "normal",
        "campos": [
            {"id": "proveedor", "etiqueta": "Proveedor", "valor": "Proveedor Demo SA", "conf": 98},
            {"id": "fecha", "etiqueta": "Fecha", "valor": "12/03/2026", "conf": 62},
            {"id": "subtotal", "etiqueta": "Subtotal", "valor": "10,000.00", "conf": 97},
            {"id": "impuestos", "etiqueta": "Impuestos", "valor": "1,600.00", "conf": 96},
            {"id": "total", "etiqueta": "Total", "valor": "12,000.00", "conf": 95},
            {"id": "moneda", "etiqueta": "Moneda", "valor": "MXN", "conf": 99},
        ],
        "hallazgos": [
            {
                "id": "total", "tipo": "adv", "titulo": "El total no coincide con subtotal más impuestos",
                "texto": "La suma de subtotal e impuestos da un valor distinto al total impreso en la factura.",
                "cifras": [["Esperado", "11,600.00"], ["Encontrado", "12,000.00"], ["Diferencia", "400.00"]],
                "regla": "R-014", "version": "2.1", "evidencia": "página 1, total",
            },
            {
                "id": "fecha", "tipo": "info", "titulo": "La fecha se leyó con baja confianza",
                "texto": "El mes no es legible con claridad. Verifica la fecha contra el documento original.",
                "regla": "R-003", "version": "1.0", "evidencia": "página 1, fecha",
            },
        ],
        "eventos": [
            {"id": "EV-3104", "fecha": "26 oct 2026 · 10:15", "quien": "Agente", "accion": "Regla aplicada", "tono": "info", "detalle": "El total no coincide con subtotal más impuestos", "regla": "R-014 · v2.1"},
            {"id": "EV-3103", "fecha": "26 oct 2026 · 10:15", "quien": "Agente", "accion": "Regla aplicada", "tono": "info", "detalle": "Fecha leída con baja confianza (62 %)", "regla": "R-003 · v1.0"},
            {"id": "EV-3102", "fecha": "26 oct 2026 · 10:14", "quien": "Agente", "accion": "Extracción de datos", "tono": "info", "detalle": "6 campos extraídos de factura_1042.pdf"},
        ],
    }
}


def crear_router(get_usuario_actual: Callable) -> APIRouter:
    router = APIRouter(prefix="/casos", tags=["casos"])

    @router.get("", response_model=ListarCasosSalida)
    def listar_casos(
        tipo: Optional[TipoCaso] = None,
        estado: Optional[EstadoCaso] = None,
        _=Depends(get_usuario_actual),
    ):
        filtrados = CASOS_MOCK
        if tipo:
            filtrados = [c for c in filtrados if c["tipo"] == tipo]
        if estado:
            filtrados = [c for c in filtrados if c["estado"] == estado]

        metricas = MetricasBandeja(
            total=len(CASOS_MOCK),
            en_revision=len([c for c in CASOS_MOCK if c["estado"] == "revision"]),
            revisados=len([c for c in CASOS_MOCK if c["estado"] == "revisado"]),
            procesando=len([c for c in CASOS_MOCK if c["estado"] == "procesando"]),
        )
        return ListarCasosSalida(casos=filtrados, metricas=metricas)

    @router.get("/{caso_id}", response_model=CasoDetalle)
    def obtener_detalle_caso(caso_id: str, _=Depends(get_usuario_actual)):
        caso_id_upper = caso_id.strip().upper()
        if caso_id_upper in DETALLES_MOCK:
            return DETALLES_MOCK[caso_id_upper]

        # Respaldo de ejemplo si solicitan otro caso de la lista
        base = next((c for c in CASOS_MOCK if c["id"] == caso_id_upper), None)
        if not base:
            raise HTTPException(404, f"No existe el caso {caso_id}.")

        return CasoDetalle(
            id=base["id"],
            archivo=base["archivo"],
            tipo=base["tipo"],
            estado=base["estado"],
            resultado_sugerido=base["resultado"],
            resultado_final=base["resultado"],
            fecha=base["fecha"],
            responsable=base["responsable"],
            variante=base.get("variante", "normal"),
            campos=[],
            hallazgos=[],
            eventos=[],
        )

    @router.post("/url-subida", response_model=UrlSubidaSalida)
    def generar_url_subida(entrada: UrlSubidaEntrada, _=Depends(get_usuario_actual)):
        timestamp = int(datetime.now().timestamp())
        s3_key = f"casos/{timestamp}_{entrada.nombre_archivo}"
        # Stub de URL prefirmada
        upload_url = f"https://s3.amazonaws.com/data-steward-casos-mock/{s3_key}?signature=mock-signature"
        return UrlSubidaSalida(upload_url=upload_url, s3_key=s3_key, expira_en_segundos=900)

    @router.post("", response_model=CrearCasoSalida, status_code=201)
    def crear_caso(entrada: CrearCasoEntrada, usuario=Depends(get_usuario_actual)):
        nuevo_id = f"F-104{len(CASOS_MOCK) + 1}"
        return CrearCasoSalida(
            id=nuevo_id,
            estado="procesando",
            mensaje=f"Caso {nuevo_id} creado y enviado a procesamiento.",
        )

    @router.post("/{caso_id}/decision", response_model=DecisionCasoSalida)
    def registrar_decision(caso_id: str, entrada: DecisionCasoEntrada, usuario=Depends(get_usuario_actual)):
        caso_id_upper = caso_id.strip().upper()
        nuevo_estado = "revisado"
        evento_id = f"EV-31{len(CASOS_MOCK) + 10}"
        resultado_final = entrada.resultado or ("aceptado" if entrada.accion == "confirmar" else "humana")

        return DecisionCasoSalida(
            caso_id=caso_id_upper,
            estado=nuevo_estado,
            resultado_final=resultado_final,
            evento_id=evento_id,
            mensaje=f"Decisión '{entrada.accion}' registrada correctamente para el caso {caso_id_upper}.",
        )

    return router
