"""esquema inicial

Revision ID: 0001
Revises:
Create Date: 2026-11-04 17:17:33.128262
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

from steward_datos.config import EMBEDDING_DIM

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('casos',
    sa.Column('id', sa.String(length=12), nullable=False),
    sa.Column('tipo', sa.String(length=12), nullable=False),
    sa.Column('estado', sa.String(length=12), server_default='procesando', nullable=False),
    sa.Column('resultado_sugerido', sa.String(length=10), nullable=True),
    sa.Column('resultado_final', sa.String(length=10), nullable=True),
    sa.Column('explicacion', sa.Text(), nullable=True),
    sa.Column('error_detalle', sa.Text(), nullable=True),
    sa.Column('thread_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('responsable_id', sa.Text(), nullable=False),
    sa.Column('responsable_nombre', sa.Text(), nullable=False),
    sa.Column('revisado_por', sa.Text(), nullable=True),
    sa.Column('revisado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("estado IN ('procesando', 'revision', 'revisado', 'error')", name='ck_casos_estado'),
    sa.CheckConstraint("resultado_final IN ('aceptado', 'rechazado', 'humana')", name='ck_casos_resultado_final'),
    sa.CheckConstraint("resultado_sugerido IN ('aceptado', 'rechazado', 'humana')", name='ck_casos_resultado_sugerido'),
    sa.CheckConstraint("tipo IN ('factura', 'validacion')", name='ck_casos_tipo'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('thread_id')
    )
    op.create_index('ix_casos_estado_creado', 'casos', ['estado', 'creado_en'], unique=False)
    op.create_index('ix_casos_responsable', 'casos', ['responsable_id'], unique=False)
    op.create_table('entidades_receptoras',
    sa.Column('rfc', sa.String(length=13), nullable=False),
    sa.Column('razon_social', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('rfc')
    )
    op.create_table('politicas',
    sa.Column('id', sa.String(length=10), nullable=False),
    sa.Column('version', sa.String(length=10), nullable=False),
    sa.Column('nombre', sa.Text(), nullable=False),
    sa.Column('tipo', sa.String(length=12), server_default='facturas', nullable=False),
    sa.Column('historia', sa.SmallInteger(), nullable=True),
    sa.Column('area_responsable', sa.Text(), nullable=True),
    sa.Column('vigente_desde', sa.Date(), nullable=False),
    sa.Column('vigente_hasta', sa.Date(), nullable=True),
    sa.Column('estado', sa.String(length=12), server_default='vigente', nullable=False),
    sa.Column('fuente_s3_key', sa.Text(), nullable=True),
    sa.Column('fuente_nombre', sa.Text(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('cargada_por', sa.Text(), nullable=True),
    sa.Column('cargada_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("estado IN ('vigente', 'reemplazada', 'borrador')", name='ck_politicas_estado'),
    sa.CheckConstraint('vigente_hasta IS NULL OR vigente_hasta >= vigente_desde', name='ck_politicas_vigencia'),
    sa.CheckConstraint("tipo IN ('facturas', 'gobernanza')", name='ck_politicas_tipo'),
    sa.PrimaryKeyConstraint('id', 'version')
    )
    op.create_table('proveedores',
    sa.Column('rfc', sa.String(length=13), nullable=False),
    sa.Column('razon_social', sa.Text(), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('alta', sa.Date(), nullable=True),
    sa.PrimaryKeyConstraint('rfc')
    )
    op.create_table('reglas',
    sa.Column('id', sa.String(length=10), nullable=False),
    sa.Column('version', sa.String(length=10), nullable=False),
    sa.Column('nombre', sa.Text(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('historia', sa.SmallInteger(), nullable=False),
    sa.Column('politica_id', sa.String(length=10), nullable=False),
    sa.Column('politica_version', sa.String(length=10), nullable=False),
    sa.Column('seccion', sa.Text(), nullable=True),
    sa.Column('efecto', sa.String(length=12), nullable=False),
    sa.Column('parametros', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('activa', sa.Boolean(), server_default='true', nullable=False),
    sa.CheckConstraint("efecto IN ('rechazo', 'revision', 'informativo')", name='ck_reglas_efecto'),
    sa.CheckConstraint('historia IN (1, 2)', name='ck_reglas_historia'),
    sa.PrimaryKeyConstraint('id', 'version')
    )
    op.create_table('campos_extraidos',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('caso_id', sa.String(length=12), nullable=False),
    sa.Column('campo', sa.Text(), nullable=False),
    sa.Column('etiqueta', sa.Text(), nullable=False),
    sa.Column('valor', sa.Text(), nullable=True),
    sa.Column('confianza', sa.SmallInteger(), nullable=True),
    sa.Column('pagina', sa.SmallInteger(), nullable=True),
    sa.Column('bbox', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('valor_corregido', sa.Text(), nullable=True),
    sa.Column('corregido_por', sa.Text(), nullable=True),
    sa.Column('corregido_en', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('confianza BETWEEN 0 AND 100', name='ck_campos_confianza'),
    sa.ForeignKeyConstraint(['caso_id'], ['casos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('caso_id', 'campo', name='uq_campos_caso_campo')
    )
    op.create_index(op.f('ix_campos_extraidos_caso_id'), 'campos_extraidos', ['caso_id'], unique=False)
    op.create_table('conversaciones',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('usuario_id', sa.Text(), nullable=False),
    sa.Column('usuario_nombre', sa.Text(), nullable=False),
    sa.Column('caso_id', sa.String(length=12), nullable=True),
    sa.Column('titulo', sa.Text(), nullable=True),
    sa.Column('thread_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizada_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['caso_id'], ['casos.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('thread_id')
    )
    op.create_index('ix_conversaciones_usuario', 'conversaciones', ['usuario_id', 'actualizada_en'], unique=False)
    op.create_table('documentos',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('caso_id', sa.String(length=12), nullable=False),
    sa.Column('nombre', sa.Text(), nullable=False),
    sa.Column('s3_key', sa.Text(), nullable=False),
    sa.Column('mime', sa.Text(), nullable=False),
    sa.Column('tamano_bytes', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('paginas', sa.SmallInteger(), nullable=True),
    sa.Column('principal', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('subido_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['caso_id'], ['casos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('s3_key')
    )
    op.create_index(op.f('ix_documentos_caso_id'), 'documentos', ['caso_id'], unique=False)
    op.create_index('ix_documentos_sha256', 'documentos', ['sha256'], unique=False)
    op.create_table('facturas',
    sa.Column('caso_id', sa.String(length=12), nullable=False),
    sa.Column('tipo_documento', sa.Text(), server_default='factura', nullable=False),
    sa.Column('folio', sa.Text(), nullable=True),
    sa.Column('fecha_emision', sa.Date(), nullable=True),
    sa.Column('emisor_nombre', sa.Text(), nullable=True),
    sa.Column('emisor_rfc', sa.String(length=13), nullable=True),
    sa.Column('receptor_nombre', sa.Text(), nullable=True),
    sa.Column('receptor_rfc', sa.String(length=13), nullable=True),
    sa.Column('moneda', sa.String(length=3), nullable=True),
    sa.Column('subtotal', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('impuestos', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('retenciones', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('total', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('tasa_iva', sa.Numeric(precision=5, scale=4), nullable=True),
    sa.Column('modelo_extraccion', sa.Text(), nullable=True),
    sa.Column('extraido_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('salida_cruda', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['caso_id'], ['casos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('caso_id')
    )
    op.create_index('ix_facturas_emisor_folio', 'facturas', ['emisor_rfc', 'folio'], unique=False)
    op.create_index('ix_facturas_fecha', 'facturas', ['fecha_emision'], unique=False)
    op.create_table('hallazgos',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('caso_id', sa.String(length=12), nullable=False),
    sa.Column('regla_id', sa.String(length=10), nullable=False),
    sa.Column('regla_version', sa.String(length=10), nullable=False),
    sa.Column('politica_id', sa.String(length=10), nullable=True),
    sa.Column('efecto', sa.String(length=12), nullable=False),
    sa.Column('severidad', sa.String(length=5), nullable=False),
    sa.Column('titulo', sa.Text(), nullable=False),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('cifras', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('campos', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.Column('filas', postgresql.ARRAY(sa.Integer()), nullable=True),
    sa.Column('evidencia', sa.Text(), nullable=True),
    sa.Column('evidencia_detalle', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('fragmentos_ids', postgresql.ARRAY(sa.BigInteger()), nullable=True),
    sa.Column('origen', sa.String(length=8), server_default='codigo', nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("efecto IN ('rechazo', 'revision', 'informativo')", name='ck_hallazgos_efecto'),
    sa.CheckConstraint("origen IN ('codigo', 'llm', 'lstm', 'humano')", name='ck_hallazgos_origen'),
    sa.CheckConstraint("severidad IN ('error', 'adv', 'info')", name='ck_hallazgos_severidad'),
    sa.ForeignKeyConstraint(['caso_id'], ['casos.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['regla_id', 'regla_version'], ['reglas.id', 'reglas.version'], name='fk_hallazgos_regla'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hallazgos_caso_id'), 'hallazgos', ['caso_id'], unique=False)
    op.create_table('politica_fragmentos',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('politica_id', sa.String(length=10), nullable=False),
    sa.Column('politica_version', sa.String(length=10), nullable=False),
    sa.Column('orden', sa.SmallInteger(), nullable=False),
    sa.Column('seccion', sa.Text(), nullable=False),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('reglas', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('tokens_aprox', sa.Integer(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=EMBEDDING_DIM), nullable=True),
    sa.Column('modelo_embedding', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['politica_id', 'politica_version'], ['politicas.id', 'politicas.version'], name='fk_fragmentos_politica', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('politica_id', 'politica_version', 'orden', name='uq_fragmentos_orden')
    )
    op.create_index('ix_fragmentos_politica', 'politica_fragmentos', ['politica_id', 'politica_version'], unique=False)
    op.create_table('bitacora',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False, start=3000), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('caso_id', sa.String(length=12), nullable=True),
    sa.Column('actor_tipo', sa.String(length=8), nullable=False),
    sa.Column('actor_id', sa.Text(), nullable=True),
    sa.Column('actor_nombre', sa.Text(), nullable=False),
    sa.Column('accion', sa.String(length=24), nullable=False),
    sa.Column('tono', sa.String(length=6), server_default='info', nullable=False),
    sa.Column('detalle', sa.Text(), nullable=False),
    sa.Column('regla_id', sa.String(length=10), nullable=True),
    sa.Column('regla_version', sa.String(length=10), nullable=True),
    sa.Column('hallazgo_id', sa.BigInteger(), nullable=True),
    sa.Column('datos', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("accion IN ('caso_creado', 'extraccion', 'politicas_consultadas', 'regla_aplicada', 'resultado_sugerido', 'correccion', 'comentario', 'confirmacion', 'escalamiento', 'error', 'politica_cargada')", name='ck_bitacora_accion'),
    sa.CheckConstraint("actor_tipo IN ('agente', 'usuario', 'sistema')", name='ck_bitacora_actor'),
    sa.CheckConstraint("tono IN ('info', 'exito', 'adv', 'error')", name='ck_bitacora_tono'),
    sa.ForeignKeyConstraint(['caso_id'], ['casos.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['hallazgo_id'], ['hallazgos.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bitacora_caso_fecha', 'bitacora', ['caso_id', 'fecha'], unique=False)
    op.create_index('ix_bitacora_fecha', 'bitacora', ['fecha'], unique=False)
    op.create_table('conceptos_factura',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('caso_id', sa.String(length=12), nullable=False),
    sa.Column('orden', sa.SmallInteger(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('cantidad', sa.Numeric(precision=12, scale=3), nullable=True),
    sa.Column('precio_unitario', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('importe', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.ForeignKeyConstraint(['caso_id'], ['facturas.caso_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conceptos_factura_caso_id'), 'conceptos_factura', ['caso_id'], unique=False)
    op.create_table('mensajes',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('conversacion_id', sa.UUID(), nullable=False),
    sa.Column('rol', sa.String(length=10), nullable=False),
    sa.Column('contenido', sa.Text(), nullable=False),
    sa.Column('pasos', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('citas', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('duracion_ms', sa.Integer(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("rol IN ('usuario', 'asistente', 'sistema')", name='ck_mensajes_rol'),
    sa.ForeignKeyConstraint(['conversacion_id'], ['conversaciones.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mensajes_conversacion', 'mensajes', ['conversacion_id', 'creado_en'], unique=False)
    op.execute(EXTRA_UP)


def downgrade():
    op.execute(EXTRA_DOWN)
    op.drop_index('ix_mensajes_conversacion', table_name='mensajes')
    op.drop_table('mensajes')
    op.drop_index(op.f('ix_conceptos_factura_caso_id'), table_name='conceptos_factura')
    op.drop_table('conceptos_factura')
    op.drop_index('ix_bitacora_fecha', table_name='bitacora')
    op.drop_index('ix_bitacora_caso_fecha', table_name='bitacora')
    op.drop_table('bitacora')
    op.drop_index('ix_fragmentos_politica', table_name='politica_fragmentos')
    op.drop_table('politica_fragmentos')
    op.drop_index(op.f('ix_hallazgos_caso_id'), table_name='hallazgos')
    op.drop_table('hallazgos')
    op.drop_index('ix_facturas_fecha', table_name='facturas')
    op.drop_index('ix_facturas_emisor_folio', table_name='facturas')
    op.drop_table('facturas')
    op.drop_index('ix_documentos_sha256', table_name='documentos')
    op.drop_index(op.f('ix_documentos_caso_id'), table_name='documentos')
    op.drop_table('documentos')
    op.drop_index('ix_conversaciones_usuario', table_name='conversaciones')
    op.drop_table('conversaciones')
    op.drop_index(op.f('ix_campos_extraidos_caso_id'), table_name='campos_extraidos')
    op.drop_table('campos_extraidos')
    op.drop_table('reglas')
    op.drop_table('proveedores')
    op.drop_table('politicas')
    op.drop_table('entidades_receptoras')
    op.drop_index('ix_casos_responsable', table_name='casos')
    op.drop_index('ix_casos_estado_creado', table_name='casos')
    op.drop_table('casos')


EXTRA_UP = """
-- IDs visibles de casos: F-1100 en adelante y V-0208 en adelante (los anteriores los usa la semilla).
CREATE SEQUENCE seq_casos_factura START 1100;
CREATE SEQUENCE seq_casos_validacion START 208;

-- Búsqueda por similitud coseno en el RAG.
CREATE INDEX ix_fragmentos_embedding ON politica_fragmentos USING hnsw (embedding vector_cosine_ops);

-- La bitácora es el registro oficial: solo admite INSERT.
CREATE FUNCTION bitacora_solo_insercion() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'La bitácora de auditoría no admite %', TG_OP;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER tr_bitacora_solo_insercion BEFORE UPDATE OR DELETE ON bitacora
  FOR EACH ROW EXECUTE FUNCTION bitacora_solo_insercion();

-- Mínimo privilegio (README · Seguridad). Los usuarios los crea Infraestructura (1.3.2);
-- aquí solo se otorgan permisos si ya existen.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'steward_backend') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO steward_backend;
    REVOKE UPDATE, DELETE ON bitacora FROM steward_backend;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO steward_backend;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'steward_mcp') THEN
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO steward_mcp;
    GRANT INSERT ON hallazgos, bitacora TO steward_mcp;
    GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO steward_mcp;
  END IF;
END $$;
"""

EXTRA_DOWN = """
DROP TRIGGER IF EXISTS tr_bitacora_solo_insercion ON bitacora;
DROP FUNCTION IF EXISTS bitacora_solo_insercion();
DROP INDEX IF EXISTS ix_fragmentos_embedding;
DROP SEQUENCE IF EXISTS seq_casos_factura;
DROP SEQUENCE IF EXISTS seq_casos_validacion;
"""
