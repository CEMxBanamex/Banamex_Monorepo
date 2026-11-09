"""Contratos de las tools del MCP (tarea 0.7.2): entradas y salidas en Pydantic.

Las tools de Agentes (leer_pdf_o_excel, extraer_campos_factura) entregan FacturaExtraida y TablaRegistros;
las tools de Datos (validar_reglas, buscar_politicas, registrar_hallazgo, consultar_caso, buscar_facturas)
las consumen. Cualquier cambio aquí se revisa en la sesión de contratos (0.7.4).
"""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Resultado = Literal["aceptado", "rechazado", "humana"]
Efecto = Literal["rechazo", "revision", "informativo"]
Severidad = Literal["error", "adv", "info"]

CAMPOS_FACTURA = (
    "folio", "fecha", "emisor_nombre", "emisor_rfc", "emisor_direccion", "receptor_nombre", "receptor_rfc",
    "moneda", "subtotal", "impuestos", "tasa_iva", "retenciones", "total", "condiciones_pago",
)

ETIQUETAS = {
    "folio": "Folio", "fecha": "Fecha", "emisor_nombre": "Proveedor", "emisor_rfc": "RFC del proveedor",
    "emisor_direccion": "Dirección del proveedor", "receptor_nombre": "Receptor", "receptor_rfc": "RFC del receptor",
    "moneda": "Moneda", "subtotal": "Subtotal", "impuestos": "Impuestos", "tasa_iva": "Tasa de IVA",
    "retenciones": "Retenciones", "total": "Total", "condiciones_pago": "Condiciones de pago",
}


# Salida de extraer_campos_factura (Agentes) = entrada de validar_reglas (Datos)


class CampoLeido(BaseModel):
    valor: Optional[str] = Field(None, description="Texto tal como aparece en el documento; null si no aparece")
    confianza: Optional[int] = Field(None, ge=0, le=100, description="Si el modelo no la da, R-003 no se evalúa para el campo")
    etiqueta: Optional[str] = Field(None, description="Etiqueta impresa junto al valor, como evidencia (p. ej. 'Total')")
    pagina: Optional[int] = 1
    bbox: Optional[list[float]] = Field(None, description="[x0, y0, x1, y1] en píxeles, origen arriba a la izquierda")


class ConceptoLeido(BaseModel):
    descripcion: str
    cantidad: Optional[str] = None
    precio_unitario: Optional[str] = None
    importe: Optional[str] = None


class FacturaExtraida(BaseModel):
    tipo_documento: str = Field("factura", description="factura, nota_credito, recibo, otro")
    campos: dict[str, CampoLeido] = Field(default_factory=dict, description=f"Claves admitidas: {', '.join(CAMPOS_FACTURA)}")
    conceptos: list[ConceptoLeido] = Field(default_factory=list)
    texto_completo: Optional[str] = Field(None, description="Texto plano del documento; lo usa R-030 para detectar instrucciones inyectadas")
    modelo: Optional[str] = Field(None, description="Etiqueta exacta del modelo de visión")
    paginas: int = 1


# Salida de leer_pdf_o_excel para archivos tabulares (Historia 2)


class TablaRegistros(BaseModel):
    archivo: str
    hoja: Optional[str] = None
    columnas: list[str]
    filas: list[dict[str, Optional[str]]] = Field(description="Valores como texto; la fila n del archivo es filas[n-1]")


# validar_reglas


class Antecedente(BaseModel):
    """Factura ya registrada, para detectar duplicados (R-015). validar_reglas la consulta sola si no se le pasa."""
    caso_id: str
    emisor_rfc: Optional[str]
    folio: Optional[str]
    sha256: Optional[str]


class ValidarReglasEntrada(BaseModel):
    caso_id: str
    historia: Literal[1, 2]
    factura: Optional[FacturaExtraida] = None
    registros: Optional[TablaRegistros] = None
    sha256: Optional[str] = Field(None, description="Hash del archivo original")
    fecha_recepcion: Optional[date] = Field(None, description="Por defecto, hoy")


class HallazgoOut(BaseModel):
    regla_id: str
    regla_version: str
    politica_id: str
    efecto: Efecto
    severidad: Severidad
    titulo: str
    texto: str
    cifras: Optional[list[tuple[str, str]]] = None
    campos: list[str] = Field(default_factory=list)
    filas: Optional[list[int]] = None
    evidencia: Optional[str] = None
    evidencia_detalle: Optional[dict] = None


class ResultadoValidacion(BaseModel):
    caso_id: str
    reglas_evaluadas: list[str] = Field(description="R-014@2.1, ...")
    hallazgos: list[HallazgoOut]
    resultado_sugerido: Resultado
    motivo: str = Field(description="Por qué se eligió el resultado, en una frase")


# buscar_politicas


class BuscarPoliticasEntrada(BaseModel):
    consulta: str
    k: int = Field(5, ge=1, le=20)
    tipo: Optional[Literal["facturas", "gobernanza"]] = None
    historia: Optional[Literal[1, 2]] = None
    fecha: Optional[date] = Field(None, description="Solo políticas vigentes en esta fecha; por defecto, hoy")
    reglas: Optional[list[str]] = Field(None, description="Filtra fragmentos que mencionan estas reglas")


class FragmentoOut(BaseModel):
    fragmento_id: int
    politica_id: str
    politica_nombre: str
    tipo: str
    version: str
    vigente_desde: date
    vigente_hasta: Optional[date]
    seccion: str
    texto: str
    reglas: list[str]
    similitud: float


class BuscarPoliticasSalida(BaseModel):
    fragmentos: list[FragmentoOut]
    modelo_embedding: str
    sin_resultados: bool = Field(description="True si ninguna política vigente supera el umbral; el agente debe pedir revisión humana")


# registrar_hallazgo


class RegistrarHallazgoEntrada(BaseModel):
    caso_id: str
    hallazgo: HallazgoOut
    origen: Literal["codigo", "llm", "lstm", "humano"] = "codigo"
    fragmentos_ids: list[int] = Field(default_factory=list)
    actor_nombre: str = "Agente"


class RegistrarHallazgoSalida(BaseModel):
    hallazgo_id: int
    evento_id: int


# consultar_caso


class CampoCaso(BaseModel):
    campo: str
    etiqueta: str
    valor: Optional[str]
    confianza: Optional[int]
    valor_corregido: Optional[str] = None


class EventoOut(BaseModel):
    id: str  # EV-3112
    fecha: datetime
    actor: str
    accion: str
    tono: str
    detalle: str
    regla: Optional[str] = None


class CasoOut(BaseModel):
    id: str
    tipo: str
    estado: str
    resultado_sugerido: Optional[Resultado]
    resultado_final: Optional[Resultado]
    explicacion: Optional[str]
    archivo: Optional[str]
    responsable: str
    creado_en: datetime
    campos: list[CampoCaso] = Field(default_factory=list)
    hallazgos: list[HallazgoOut] = Field(default_factory=list)
    eventos: list[EventoOut] = Field(default_factory=list)


# buscar_facturas


class BuscarFacturasEntrada(BaseModel):
    """Filtros cerrados: el LLM no escribe SQL, solo llena estos campos."""
    emisor: Optional[str] = Field(None, description="Parte del nombre o RFC del proveedor")
    folio: Optional[str] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_min: Optional[float] = None
    total_max: Optional[float] = None
    moneda: Optional[str] = None
    resultado: Optional[Resultado] = None
    estado: Optional[Literal["procesando", "revision", "revisado", "error"]] = None
    con_regla: Optional[str] = Field(None, description="Solo casos con un hallazgo de esta regla, p. ej. R-014")
    orden: Literal["fecha_desc", "fecha_asc", "total_desc", "total_asc"] = "fecha_desc"
    limite: int = Field(20, ge=1, le=100)


class FacturaResumen(BaseModel):
    caso_id: str
    folio: Optional[str]
    fecha_emision: Optional[date]
    emisor_nombre: Optional[str]
    emisor_rfc: Optional[str]
    total: Optional[float]
    moneda: Optional[str]
    estado: str
    resultado_sugerido: Optional[str]
    reglas_con_hallazgo: list[str]


class BuscarFacturasSalida(BaseModel):
    total_coincidencias: int
    facturas: list[FacturaResumen]
