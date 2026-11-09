"""negocio gobernanza y vistas

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09 16:48:11.445605
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('catalogo_tablas',
    sa.Column('tabla', sa.Text(), nullable=False),
    sa.Column('nombre_negocio', sa.Text(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('dominio', sa.Text(), nullable=False),
    sa.Column('data_owner', sa.Text(), nullable=False),
    sa.Column('data_steward', sa.Text(), nullable=False),
    sa.Column('sensibilidad', sa.String(length=12), nullable=False),
    sa.Column('origen', sa.Text(), nullable=False),
    sa.Column('consultable', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('relacionadas', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.CheckConstraint("sensibilidad IN ('publico', 'interno', 'confidencial', 'restringido')", name='ck_catalogo_tablas_sensibilidad'),
    sa.PrimaryKeyConstraint('tabla')
    )
    op.create_table('consultas_libres',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('usuario_id', sa.Text(), nullable=False),
    sa.Column('rol', sa.Text(), nullable=False),
    sa.Column('pregunta', sa.Text(), nullable=False),
    sa.Column('sql', sa.Text(), nullable=False),
    sa.Column('valida', sa.Boolean(), nullable=False),
    sa.Column('motivo_rechazo', sa.Text(), nullable=True),
    sa.Column('filas', sa.Integer(), nullable=True),
    sa.Column('duracion_ms', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('glosario_terminos',
    sa.Column('termino', sa.Text(), nullable=False),
    sa.Column('definicion', sa.Text(), nullable=False),
    sa.Column('sinonimos', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('dominio', sa.Text(), nullable=False),
    sa.Column('dueno', sa.Text(), nullable=False),
    sa.Column('relacionados', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('fuente', sa.Text(), nullable=True),
    sa.Column('actualizado_en', sa.Date(), nullable=False),
    sa.PrimaryKeyConstraint('termino')
    )
    op.create_table('metricas',
    sa.Column('nombre', sa.Text(), nullable=False),
    sa.Column('etiqueta', sa.Text(), nullable=False),
    sa.Column('definicion', sa.Text(), nullable=False),
    sa.Column('unidad', sa.Text(), nullable=False),
    sa.Column('vista', sa.Text(), nullable=False),
    sa.Column('dimensiones', postgresql.ARRAY(sa.Text()), nullable=False),
    sa.Column('dueno', sa.Text(), nullable=False),
    sa.Column('version', sa.String(length=10), nullable=False),
    sa.PrimaryKeyConstraint('nombre')
    )
    op.create_table('reglas_calidad',
    sa.Column('id', sa.String(length=8), nullable=False),
    sa.Column('tabla', sa.Text(), nullable=False),
    sa.Column('columna', sa.Text(), nullable=True),
    sa.Column('dimension', sa.String(length=14), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('umbral', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('sql_medicion', sa.Text(), nullable=False),
    sa.Column('politica_id', sa.String(length=10), nullable=True),
    sa.Column('activa', sa.Boolean(), server_default='true', nullable=False),
    sa.CheckConstraint("dimension IN ('completitud', 'unicidad', 'validez', 'oportunidad', 'consistencia')", name='ck_calidad_dimension'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reglas_calidad_tabla'), 'reglas_calidad', ['tabla'], unique=False)
    op.create_table('catalogo_columnas',
    sa.Column('tabla', sa.Text(), nullable=False),
    sa.Column('columna', sa.Text(), nullable=False),
    sa.Column('orden', sa.SmallInteger(), nullable=False),
    sa.Column('tipo', sa.Text(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('sensibilidad', sa.String(length=12), nullable=False),
    sa.Column('enmascarada', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('ejemplos', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.Column('termino_glosario', sa.Text(), nullable=True),
    sa.CheckConstraint("sensibilidad IN ('publico', 'interno', 'confidencial', 'restringido')", name='ck_catalogo_columnas_sensibilidad'),
    sa.ForeignKeyConstraint(['tabla'], ['catalogo_tablas.tabla'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tabla', 'columna')
    )
    op.create_table('centros_costo',
    sa.Column('id', sa.String(length=10), nullable=False),
    sa.Column('nombre', sa.Text(), nullable=False),
    sa.Column('area', sa.Text(), nullable=False),
    sa.Column('entidad_rfc', sa.String(length=13), nullable=False),
    sa.Column('responsable', sa.Text(), nullable=False),
    sa.Column('presupuesto_anual', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['entidad_rfc'], ['entidades_receptoras.rfc'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('clientes',
    sa.Column('id_cliente', sa.String(length=12), nullable=False),
    sa.Column('nombre', sa.Text(), nullable=False),
    sa.Column('tipo_persona', sa.String(length=6), nullable=False),
    sa.Column('rfc', sa.Text(), nullable=True),
    sa.Column('correo_contacto', sa.Text(), nullable=True),
    sa.Column('segmento', sa.Text(), nullable=False),
    sa.Column('entidad_rfc', sa.String(length=13), nullable=False),
    sa.Column('alta', sa.Date(), nullable=True),
    sa.Column('activo', sa.Boolean(), server_default='true', nullable=False),
    sa.CheckConstraint("tipo_persona IN ('fisica', 'moral')", name='ck_clientes_tipo'),
    sa.ForeignKeyConstraint(['entidad_rfc'], ['entidades_receptoras.rfc'], ),
    sa.PrimaryKeyConstraint('id_cliente')
    )
    op.create_table('pagos',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('caso_id', sa.String(length=12), nullable=False),
    sa.Column('fecha_programada', sa.Date(), nullable=False),
    sa.Column('fecha_pago', sa.Date(), nullable=True),
    sa.Column('moneda', sa.String(length=3), nullable=False),
    sa.Column('monto', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.CheckConstraint("estado IN ('programado', 'pagado', 'cancelado')", name='ck_pagos_estado'),
    sa.ForeignKeyConstraint(['caso_id'], ['casos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pagos_caso_id'), 'pagos', ['caso_id'], unique=False)
    op.create_table('resultados_calidad',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('regla_id', sa.String(length=8), nullable=False),
    sa.Column('ejecutado_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('registros_evaluados', sa.Integer(), nullable=False),
    sa.Column('registros_cumplen', sa.Integer(), nullable=False),
    sa.Column('porcentaje', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('cumple_umbral', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['regla_id'], ['reglas_calidad.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_resultados_calidad_regla_fecha', 'resultados_calidad', ['regla_id', 'ejecutado_en'], unique=False)
    op.create_table('usuarios_entidades',
    sa.Column('usuario_id', sa.Text(), nullable=False),
    sa.Column('entidad_rfc', sa.String(length=13), nullable=False),
    sa.ForeignKeyConstraint(['entidad_rfc'], ['entidades_receptoras.rfc'], ),
    sa.PrimaryKeyConstraint('usuario_id', 'entidad_rfc')
    )
    op.create_table('ordenes_compra',
    sa.Column('id', sa.String(length=14), nullable=False),
    sa.Column('proveedor_rfc', sa.String(length=13), nullable=False),
    sa.Column('entidad_rfc', sa.String(length=13), nullable=False),
    sa.Column('centro_costo_id', sa.String(length=10), nullable=True),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('moneda', sa.String(length=3), nullable=False),
    sa.Column('monto', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.CheckConstraint("estado IN ('abierta', 'facturada', 'cancelada')", name='ck_oc_estado'),
    sa.ForeignKeyConstraint(['centro_costo_id'], ['centros_costo.id'], ),
    sa.ForeignKeyConstraint(['entidad_rfc'], ['entidades_receptoras.rfc'], ),
    sa.ForeignKeyConstraint(['proveedor_rfc'], ['proveedores.rfc'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_oc_proveedor_fecha', 'ordenes_compra', ['proveedor_rfc', 'fecha'], unique=False)
    op.add_column('casos', sa.Column('origen', sa.String(length=10), server_default='aplicacion', nullable=False))
    op.add_column('facturas', sa.Column('orden_compra_id', sa.String(length=14), nullable=True))
    op.create_index(op.f('ix_facturas_orden_compra_id'), 'facturas', ['orden_compra_id'], unique=False)
    op.create_foreign_key('fk_facturas_orden_compra', 'facturas', 'ordenes_compra', ['orden_compra_id'], ['id'], ondelete='SET NULL')
    op.add_column('proveedores', sa.Column('categoria', sa.Text(), nullable=True))
    op.add_column('proveedores', sa.Column('correo_contacto', sa.Text(), nullable=True))
    op.add_column('proveedores', sa.Column('plazo_pago_dias', sa.SmallInteger(), nullable=True))
    op.create_check_constraint('ck_casos_origen', 'casos', "origen IN ('aplicacion', 'semilla', 'negocio')")
    op.execute(VISTAS_UP)


def downgrade():
    op.execute(VISTAS_DOWN)
    op.drop_constraint('ck_casos_origen', 'casos', type_='check')
    op.drop_column('proveedores', 'plazo_pago_dias')
    op.drop_column('proveedores', 'correo_contacto')
    op.drop_column('proveedores', 'categoria')
    # WARNING: constraint name is None; this directive will fail as
    # rendered.  Add a name, or use a naming convention; see
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    op.drop_constraint('fk_facturas_orden_compra', 'facturas', type_='foreignkey')
    op.drop_index(op.f('ix_facturas_orden_compra_id'), table_name='facturas')
    op.drop_column('facturas', 'orden_compra_id')
    op.drop_column('casos', 'origen')
    op.drop_index('ix_oc_proveedor_fecha', table_name='ordenes_compra')
    op.drop_table('ordenes_compra')
    op.drop_table('usuarios_entidades')
    op.drop_index('ix_resultados_calidad_regla_fecha', table_name='resultados_calidad')
    op.drop_table('resultados_calidad')
    op.drop_index(op.f('ix_pagos_caso_id'), table_name='pagos')
    op.drop_table('pagos')
    op.drop_table('clientes')
    op.drop_table('centros_costo')
    op.drop_table('catalogo_columnas')
    op.drop_index(op.f('ix_reglas_calidad_tabla'), table_name='reglas_calidad')
    op.drop_table('reglas_calidad')
    op.drop_table('metricas')
    op.drop_table('glosario_terminos')
    op.drop_table('consultas_libres')
    op.drop_table('catalogo_tablas')


VISTAS = ["v_facturas", "v_proveedores", "v_casos", "v_hallazgos", "v_ordenes_compra", "v_pagos", "v_centros_costo", "v_clientes"]

VISTAS_UP = """
-- Contexto de la consulta. La tool fija estos valores con SET LOCAL al inicio de cada transacción:
--   SET LOCAL app.rol = 'analista' | 'administrador';  SET LOCAL app.usuario = '<sub de Cognito>';
-- Sin contexto, las vistas no devuelven filas.
CREATE FUNCTION app_rol() RETURNS text LANGUAGE sql STABLE AS
  $$ SELECT coalesce(nullif(current_setting('app.rol', true), ''), 'ninguno') $$;
CREATE FUNCTION app_usuario() RETURNS text LANGUAGE sql STABLE AS
  $$ SELECT coalesce(current_setting('app.usuario', true), '') $$;
CREATE FUNCTION app_es_admin() RETURNS boolean LANGUAGE sql STABLE AS
  $$ SELECT app_rol() = 'administrador' $$;

-- Seguridad por fila: el administrador ve todo; un analista, solo las entidades que tiene asignadas.
-- Las vistas corren con los permisos de su dueño, así que el usuario de consultas no necesita (ni tiene) acceso a las tablas.
CREATE VIEW v_entidades_visibles WITH (security_barrier) AS
  SELECT e.rfc FROM entidades_receptoras e
  WHERE app_es_admin()
     OR (app_rol() = 'analista' AND EXISTS (
           SELECT 1 FROM usuarios_entidades ue WHERE ue.usuario_id = app_usuario() AND ue.entidad_rfc = e.rfc));

CREATE VIEW v_facturas WITH (security_barrier) AS
SELECT
  f.caso_id, f.folio, f.fecha_emision, date_trunc('month', f.fecha_emision)::date AS mes,
  f.emisor_rfc AS proveedor_rfc, coalesce(p.razon_social, f.emisor_nombre) AS proveedor,
  f.receptor_rfc AS entidad_rfc, e.razon_social AS entidad,
  oc.centro_costo_id, cc.nombre AS centro_costo, f.orden_compra_id,
  f.moneda, f.subtotal, f.impuestos, f.retenciones, f.total,
  round(f.total * CASE WHEN f.moneda = 'USD' THEN 18.50 ELSE 1 END, 2) AS total_mxn,
  c.estado, coalesce(c.resultado_final, c.resultado_sugerido) AS resultado, c.resultado_sugerido, c.resultado_final,
  c.origen, c.creado_en AS recibida_en, c.revisado_en AS revisada_en,
  round(extract(epoch FROM c.revisado_en - c.creado_en) / 3600.0, 2) AS horas_revision,
  EXISTS (SELECT 1 FROM pagos pg WHERE pg.caso_id = f.caso_id AND pg.estado = 'pagado') AS pagada,
  (coalesce(c.resultado_final, c.resultado_sugerido) = 'aceptado' AND oc.id IS NOT NULL
     AND abs(oc.monto - f.total) <= 0.05
     AND EXISTS (SELECT 1 FROM pagos pg WHERE pg.caso_id = f.caso_id AND pg.estado = 'pagado' AND abs(pg.monto - f.total) <= 0.05)
  ) AS conciliada
FROM facturas f
JOIN casos c ON c.id = f.caso_id
LEFT JOIN proveedores p ON p.rfc = f.emisor_rfc
LEFT JOIN entidades_receptoras e ON e.rfc = f.receptor_rfc
LEFT JOIN ordenes_compra oc ON oc.id = f.orden_compra_id
LEFT JOIN centros_costo cc ON cc.id = oc.centro_costo_id
WHERE f.tipo_documento = 'factura' AND f.receptor_rfc IN (SELECT rfc FROM v_entidades_visibles);

CREATE VIEW v_proveedores WITH (security_barrier) AS
SELECT rfc, razon_social, categoria, activo, alta, plazo_pago_dias, correo_contacto
FROM proveedores
WHERE app_rol() IN ('analista', 'administrador');

CREATE VIEW v_casos WITH (security_barrier) AS
SELECT
  c.id AS caso_id, c.tipo, c.estado, c.resultado_sugerido, c.resultado_final,
  coalesce(c.resultado_final, c.resultado_sugerido) AS resultado,
  c.responsable_nombre AS responsable, c.revisado_por, c.origen, f.receptor_rfc AS entidad_rfc,
  c.creado_en, c.revisado_en,
  round(extract(epoch FROM c.revisado_en - c.creado_en) / 3600.0, 2) AS horas_revision
FROM casos c
LEFT JOIN facturas f ON f.caso_id = c.id
WHERE f.receptor_rfc IN (SELECT rfc FROM v_entidades_visibles)
   OR (c.tipo = 'validacion' AND (app_es_admin() OR c.responsable_id = app_usuario()))
   OR (c.tipo = 'factura' AND f.caso_id IS NULL AND (app_es_admin() OR c.responsable_id = app_usuario()));

CREATE VIEW v_hallazgos WITH (security_barrier) AS
SELECT h.id AS hallazgo_id, h.caso_id, h.regla_id, h.regla_version, r.nombre AS regla, h.politica_id,
       h.efecto, h.severidad, h.titulo, h.origen, h.creado_en
FROM hallazgos h
JOIN reglas r ON r.id = h.regla_id AND r.version = h.regla_version
WHERE h.caso_id IN (SELECT caso_id FROM v_casos);

CREATE VIEW v_ordenes_compra WITH (security_barrier) AS
SELECT oc.id AS orden_compra_id, oc.proveedor_rfc, p.razon_social AS proveedor, oc.entidad_rfc,
       oc.centro_costo_id, cc.nombre AS centro_costo, oc.fecha, date_trunc('month', oc.fecha)::date AS mes,
       oc.descripcion, oc.moneda, oc.monto, oc.estado
FROM ordenes_compra oc
LEFT JOIN proveedores p ON p.rfc = oc.proveedor_rfc
LEFT JOIN centros_costo cc ON cc.id = oc.centro_costo_id
WHERE oc.entidad_rfc IN (SELECT rfc FROM v_entidades_visibles);

CREATE VIEW v_pagos WITH (security_barrier) AS
SELECT pg.id AS pago_id, pg.caso_id, f.folio, f.emisor_rfc AS proveedor_rfc, coalesce(p.razon_social, f.emisor_nombre) AS proveedor,
       f.receptor_rfc AS entidad_rfc, pg.fecha_programada, pg.fecha_pago,
       CASE WHEN pg.fecha_pago IS NOT NULL THEN greatest(pg.fecha_pago - pg.fecha_programada, 0) END AS dias_atraso,
       pg.moneda, pg.monto, pg.estado
FROM pagos pg
JOIN facturas f ON f.caso_id = pg.caso_id
LEFT JOIN proveedores p ON p.rfc = f.emisor_rfc
WHERE f.receptor_rfc IN (SELECT rfc FROM v_entidades_visibles);

CREATE VIEW v_centros_costo WITH (security_barrier) AS
SELECT cc.id AS centro_costo_id, cc.nombre, cc.area, cc.entidad_rfc, cc.responsable, cc.presupuesto_anual,
       coalesce((SELECT sum(oc.monto * CASE WHEN oc.moneda = 'USD' THEN 18.50 ELSE 1 END) FROM ordenes_compra oc
                 WHERE oc.centro_costo_id = cc.id AND oc.estado <> 'cancelada'), 0)::numeric(14, 2) AS comprometido_mxn
FROM centros_costo cc
WHERE cc.entidad_rfc IN (SELECT rfc FROM v_entidades_visibles);

-- Datos personales: RFC y correo se enmascaran para quien no es administrador.
CREATE VIEW v_clientes WITH (security_barrier) AS
SELECT cl.id_cliente, cl.nombre, cl.tipo_persona,
       CASE WHEN app_es_admin() THEN cl.rfc ELSE left(cl.rfc, 4) || repeat('*', greatest(length(cl.rfc) - 4, 0)) END AS rfc,
       CASE WHEN app_es_admin() THEN cl.correo_contacto
            ELSE regexp_replace(cl.correo_contacto, '^(.).*(@.*)$', '\\1***\\2') END AS correo_contacto,
       cl.segmento, cl.entidad_rfc, cl.alta, date_trunc('month', cl.alta)::date AS mes_alta, cl.activo
FROM clientes cl
WHERE cl.entidad_rfc IN (SELECT rfc FROM v_entidades_visibles);

-- Usuario de consultas del chat (ejecutar_consulta): solo las vistas, con tiempo máximo. Lo crea Infraestructura.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'steward_consultas') THEN
    GRANT USAGE ON SCHEMA public TO steward_consultas;
    GRANT SELECT ON v_facturas, v_proveedores, v_casos, v_hallazgos, v_ordenes_compra, v_pagos, v_centros_costo, v_clientes
      TO steward_consultas;
    ALTER ROLE steward_consultas SET statement_timeout = '5s';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'steward_backend') THEN
    GRANT USAGE ON SCHEMA public TO steward_backend;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO steward_backend;
    REVOKE UPDATE, DELETE ON bitacora FROM steward_backend;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO steward_backend;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'steward_mcp') THEN
    GRANT USAGE ON SCHEMA public TO steward_mcp;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO steward_mcp;
    GRANT INSERT ON consultas_libres TO steward_mcp;
    GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO steward_mcp;
  END IF;
END $$;
"""

VISTAS_DOWN = """
DROP VIEW IF EXISTS v_clientes, v_centros_costo, v_pagos, v_ordenes_compra, v_hallazgos, v_casos, v_proveedores, v_facturas,
  v_entidades_visibles;
DROP FUNCTION IF EXISTS app_es_admin(), app_usuario(), app_rol();
"""
