"""Esquema de la base de datos (tareas 0.3.1 a 0.3.4).

Convenciones:
- Los catálogos de valores (estado, resultado, etc.) son texto con CHECK, no ENUM de PostgreSQL,
  para poder agregar valores sin migraciones complicadas.
- Los montos son NUMERIC(14, 2). Las fechas con hora son TIMESTAMPTZ.
- Las tablas de checkpoints de LangGraph las crea PostgresSaver.setup(); no se definen aquí.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint,
    Identity, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..config import EMBEDDING_DIM

TIPOS_CASO = ("factura", "validacion")
ESTADOS_CASO = ("procesando", "revision", "revisado", "error")
RESULTADOS = ("aceptado", "rechazado", "humana")
EFECTOS = ("rechazo", "revision", "informativo")
SEVERIDADES = ("error", "adv", "info")
ACCIONES_BITACORA = (
    "caso_creado", "extraccion", "politicas_consultadas", "regla_aplicada", "resultado_sugerido",
    "correccion", "comentario", "confirmacion", "escalamiento", "error", "politica_cargada",
)
TONOS = ("info", "exito", "adv", "error")


def _en(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


class Base(DeclarativeBase):
    pass


# Catálogos


class Proveedor(Base):
    """Padrón sintético de proveedores autorizados (regla R-017)."""
    __tablename__ = "proveedores"

    rfc: Mapped[str] = mapped_column(String(13), primary_key=True)
    razon_social: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    alta: Mapped[Optional[date]] = mapped_column(Date)


class EntidadReceptora(Base):
    """Entidades del grupo que pueden recibir facturas (regla R-018)."""
    __tablename__ = "entidades_receptoras"

    rfc: Mapped[str] = mapped_column(String(13), primary_key=True)
    razon_social: Mapped[str] = mapped_column(Text)


# Casos y documentos (0.3.1)


class Caso(Base):
    __tablename__ = "casos"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_en(TIPOS_CASO)})", name="ck_casos_tipo"),
        CheckConstraint(f"estado IN ({_en(ESTADOS_CASO)})", name="ck_casos_estado"),
        CheckConstraint(f"resultado_sugerido IN ({_en(RESULTADOS)})", name="ck_casos_resultado_sugerido"),
        CheckConstraint(f"resultado_final IN ({_en(RESULTADOS)})", name="ck_casos_resultado_final"),
        Index("ix_casos_estado_creado", "estado", "creado_en"),
        Index("ix_casos_responsable", "responsable_id"),
    )

    id: Mapped[str] = mapped_column(String(12), primary_key=True)  # F-1042, V-0207
    tipo: Mapped[str] = mapped_column(String(12))
    estado: Mapped[str] = mapped_column(String(12), default="procesando", server_default="procesando")
    resultado_sugerido: Mapped[Optional[str]] = mapped_column(String(10))
    resultado_final: Mapped[Optional[str]] = mapped_column(String(10))
    explicacion: Mapped[Optional[str]] = mapped_column(Text)
    error_detalle: Mapped[Optional[str]] = mapped_column(Text)
    thread_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), unique=True, server_default=func.gen_random_uuid())
    responsable_id: Mapped[str] = mapped_column(Text)  # sub de Cognito (o X-Usuario en dev)
    responsable_nombre: Mapped[str] = mapped_column(Text)
    revisado_por: Mapped[Optional[str]] = mapped_column(Text)
    revisado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    documentos: Mapped[list["Documento"]] = relationship(back_populates="caso", cascade="all, delete-orphan")
    factura: Mapped[Optional["Factura"]] = relationship(back_populates="caso", cascade="all, delete-orphan", uselist=False)
    hallazgos: Mapped[list["Hallazgo"]] = relationship(back_populates="caso", cascade="all, delete-orphan")


class Documento(Base):
    """Archivo original del caso, guardado en S3."""
    __tablename__ = "documentos"
    __table_args__ = (Index("ix_documentos_sha256", "sha256"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    caso_id: Mapped[str] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(Text)
    s3_key: Mapped[str] = mapped_column(Text, unique=True)
    mime: Mapped[str] = mapped_column(Text)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    paginas: Mapped[Optional[int]] = mapped_column(SmallInteger)
    principal: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    subido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    caso: Mapped[Caso] = relationship(back_populates="documentos")


class Factura(Base):
    """Valores normalizados de la factura (una por caso). El detalle por campo está en campos_extraidos."""
    __tablename__ = "facturas"
    __table_args__ = (
        Index("ix_facturas_emisor_folio", "emisor_rfc", "folio"),
        Index("ix_facturas_fecha", "fecha_emision"),
    )

    caso_id: Mapped[str] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), primary_key=True)
    tipo_documento: Mapped[str] = mapped_column(Text, default="factura", server_default="factura")
    folio: Mapped[Optional[str]] = mapped_column(Text)
    fecha_emision: Mapped[Optional[date]] = mapped_column(Date)
    emisor_nombre: Mapped[Optional[str]] = mapped_column(Text)
    emisor_rfc: Mapped[Optional[str]] = mapped_column(String(13))
    receptor_nombre: Mapped[Optional[str]] = mapped_column(Text)
    receptor_rfc: Mapped[Optional[str]] = mapped_column(String(13))
    moneda: Mapped[Optional[str]] = mapped_column(String(3))
    subtotal: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    impuestos: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    retenciones: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    total: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    tasa_iva: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    modelo_extraccion: Mapped[Optional[str]] = mapped_column(Text)  # etiqueta exacta del modelo de visión
    extraido_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    salida_cruda: Mapped[Optional[dict]] = mapped_column(JSONB)  # JSON tal cual lo devolvió el modelo

    caso: Mapped[Caso] = relationship(back_populates="factura")
    conceptos: Mapped[list["ConceptoFactura"]] = relationship(cascade="all, delete-orphan", order_by="ConceptoFactura.orden")


class ConceptoFactura(Base):
    __tablename__ = "conceptos_factura"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    caso_id: Mapped[str] = mapped_column(ForeignKey("facturas.caso_id", ondelete="CASCADE"), index=True)
    orden: Mapped[int] = mapped_column(SmallInteger)
    descripcion: Mapped[str] = mapped_column(Text)
    cantidad: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    precio_unitario: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    importe: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))


class CampoExtraido(Base):
    """Un campo leído por el modelo de visión, con su confianza y su posible corrección humana."""
    __tablename__ = "campos_extraidos"
    __table_args__ = (
        UniqueConstraint("caso_id", "campo", name="uq_campos_caso_campo"),
        CheckConstraint("confianza BETWEEN 0 AND 100", name="ck_campos_confianza"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    caso_id: Mapped[str] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    campo: Mapped[str] = mapped_column(Text)  # proveedor, fecha, subtotal...
    etiqueta: Mapped[str] = mapped_column(Text)  # texto que muestra la interfaz
    valor: Mapped[Optional[str]] = mapped_column(Text)  # tal como se leyó
    confianza: Mapped[Optional[int]] = mapped_column(SmallInteger)
    pagina: Mapped[Optional[int]] = mapped_column(SmallInteger)
    bbox: Mapped[Optional[list]] = mapped_column(JSONB)  # [x0, y0, x1, y1] en píxeles de la página
    valor_corregido: Mapped[Optional[str]] = mapped_column(Text)
    corregido_por: Mapped[Optional[str]] = mapped_column(Text)
    corregido_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# Hallazgos y bitácora (0.3.2)


class Regla(Base):
    """Catálogo de reglas (1.5.3). Se carga desde reglas/catalogo.yaml."""
    __tablename__ = "reglas"
    __table_args__ = (
        CheckConstraint(f"efecto IN ({_en(EFECTOS)})", name="ck_reglas_efecto"),
        CheckConstraint("historia IN (1, 2)", name="ck_reglas_historia"),
    )

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    version: Mapped[str] = mapped_column(String(10), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    descripcion: Mapped[str] = mapped_column(Text)
    historia: Mapped[int] = mapped_column(SmallInteger)
    politica_id: Mapped[str] = mapped_column(String(10))
    politica_version: Mapped[str] = mapped_column(String(10))
    seccion: Mapped[Optional[str]] = mapped_column(Text)
    efecto: Mapped[str] = mapped_column(String(12))
    parametros: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Hallazgo(Base):
    __tablename__ = "hallazgos"
    __table_args__ = (
        CheckConstraint(f"efecto IN ({_en(EFECTOS)})", name="ck_hallazgos_efecto"),
        CheckConstraint(f"severidad IN ({_en(SEVERIDADES)})", name="ck_hallazgos_severidad"),
        CheckConstraint("origen IN ('codigo', 'llm', 'lstm', 'humano')", name="ck_hallazgos_origen"),
        ForeignKeyConstraint(["regla_id", "regla_version"], ["reglas.id", "reglas.version"], name="fk_hallazgos_regla"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    caso_id: Mapped[str] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    regla_id: Mapped[str] = mapped_column(String(10))
    regla_version: Mapped[str] = mapped_column(String(10))
    politica_id: Mapped[Optional[str]] = mapped_column(String(10))
    efecto: Mapped[str] = mapped_column(String(12))
    severidad: Mapped[str] = mapped_column(String(5))  # tipo visual: error, adv, info
    titulo: Mapped[str] = mapped_column(Text)
    texto: Mapped[str] = mapped_column(Text)
    cifras: Mapped[Optional[list]] = mapped_column(JSONB)  # [["Esperado", "11,600.00"], ...]
    campos: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))  # campos implicados
    filas: Mapped[Optional[list[int]]] = mapped_column(ARRAY(Integer))  # Historia 2
    evidencia: Mapped[Optional[str]] = mapped_column(Text)  # "página 1, total"
    evidencia_detalle: Mapped[Optional[dict]] = mapped_column(JSONB)  # pagina, bbox, columna
    fragmentos_ids: Mapped[Optional[list[int]]] = mapped_column(ARRAY(BigInteger))  # fragmentos de política citados
    origen: Mapped[str] = mapped_column(String(8), default="codigo", server_default="codigo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    caso: Mapped[Caso] = relationship(back_populates="hallazgos")


class EventoBitacora(Base):
    """Registro oficial de auditoría. Solo inserción: un trigger bloquea UPDATE y DELETE."""
    __tablename__ = "bitacora"
    __table_args__ = (
        CheckConstraint(f"accion IN ({_en(ACCIONES_BITACORA)})", name="ck_bitacora_accion"),
        CheckConstraint(f"tono IN ({_en(TONOS)})", name="ck_bitacora_tono"),
        CheckConstraint("actor_tipo IN ('agente', 'usuario', 'sistema')", name="ck_bitacora_actor"),
        Index("ix_bitacora_caso_fecha", "caso_id", "fecha"),
        Index("ix_bitacora_fecha", "fecha"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(start=3000), primary_key=True)  # se muestra como EV-3112
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    caso_id: Mapped[Optional[str]] = mapped_column(ForeignKey("casos.id", ondelete="RESTRICT"))
    actor_tipo: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[Optional[str]] = mapped_column(Text)
    actor_nombre: Mapped[str] = mapped_column(Text)
    accion: Mapped[str] = mapped_column(String(24))
    tono: Mapped[str] = mapped_column(String(6), default="info", server_default="info")
    detalle: Mapped[str] = mapped_column(Text)
    regla_id: Mapped[Optional[str]] = mapped_column(String(10))
    regla_version: Mapped[Optional[str]] = mapped_column(String(10))
    hallazgo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hallazgos.id", ondelete="SET NULL"))
    datos: Mapped[Optional[dict]] = mapped_column(JSONB)  # {"texto", "antes", "despues", ...}


# Políticas y RAG (0.3.3)


class Politica(Base):
    __tablename__ = "politicas"
    __table_args__ = (
        CheckConstraint("estado IN ('vigente', 'reemplazada', 'borrador')", name="ck_politicas_estado"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="ck_politicas_vigencia"),
    )

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    version: Mapped[str] = mapped_column(String(10), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    historia: Mapped[Optional[int]] = mapped_column(SmallInteger)  # NULL = aplica a ambas historias
    area_responsable: Mapped[Optional[str]] = mapped_column(Text)
    vigente_desde: Mapped[date] = mapped_column(Date)
    vigente_hasta: Mapped[Optional[date]] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(12), default="vigente", server_default="vigente")
    fuente_s3_key: Mapped[Optional[str]] = mapped_column(Text)
    fuente_nombre: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    cargada_por: Mapped[Optional[str]] = mapped_column(Text)
    cargada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fragmentos: Mapped[list["FragmentoPolitica"]] = relationship(cascade="all, delete-orphan", order_by="FragmentoPolitica.orden")


class FragmentoPolitica(Base):
    __tablename__ = "politica_fragmentos"
    __table_args__ = (
        ForeignKeyConstraint(["politica_id", "politica_version"], ["politicas.id", "politicas.version"],
                             ondelete="CASCADE", name="fk_fragmentos_politica"),
        UniqueConstraint("politica_id", "politica_version", "orden", name="uq_fragmentos_orden"),
        Index("ix_fragmentos_politica", "politica_id", "politica_version"),
        Index("ix_fragmentos_embedding", "embedding", postgresql_using="hnsw",
              postgresql_ops={"embedding": "vector_cosine_ops"}),  # se crea en la migración 0001
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    politica_id: Mapped[str] = mapped_column(String(10))
    politica_version: Mapped[str] = mapped_column(String(10))
    orden: Mapped[int] = mapped_column(SmallInteger)
    seccion: Mapped[str] = mapped_column(Text)
    texto: Mapped[str] = mapped_column(Text)
    reglas: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    tokens_aprox: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(EMBEDDING_DIM))
    modelo_embedding: Mapped[Optional[str]] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Chat (0.3.4)


class Conversacion(Base):
    __tablename__ = "conversaciones"
    __table_args__ = (Index("ix_conversaciones_usuario", "usuario_id", "actualizada_en"),)

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    usuario_id: Mapped[str] = mapped_column(Text)
    usuario_nombre: Mapped[str] = mapped_column(Text)
    caso_id: Mapped[Optional[str]] = mapped_column(ForeignKey("casos.id", ondelete="SET NULL"))  # NULL = Asistente general
    titulo: Mapped[Optional[str]] = mapped_column(Text)
    thread_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), unique=True, server_default=func.gen_random_uuid())
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    mensajes: Mapped[list["Mensaje"]] = relationship(cascade="all, delete-orphan", order_by="Mensaje.creado_en")


class Mensaje(Base):
    __tablename__ = "mensajes"
    __table_args__ = (
        CheckConstraint("rol IN ('usuario', 'asistente', 'sistema')", name="ck_mensajes_rol"),
        Index("ix_mensajes_conversacion", "conversacion_id", "creado_en"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    conversacion_id: Mapped[Any] = mapped_column(ForeignKey("conversaciones.id", ondelete="CASCADE"))
    rol: Mapped[str] = mapped_column(String(10))
    contenido: Mapped[str] = mapped_column(Text)
    # Pasos que mostró la línea de pasos del chat:
    # [{"id", "tipo": "tool"|"pensamiento", "tool", "etiqueta", "estado": "ok"|"error", "inicio", "fin", "duracion_ms", "detalle"}]
    pasos: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    citas: Mapped[Optional[list]] = mapped_column(JSONB)  # [{"fragmento_id", "politica_id", "version", "seccion"}]
    duracion_ms: Mapped[Optional[int]] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
