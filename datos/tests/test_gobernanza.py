"""Vistas consultables con seguridad por fila, capa semántica y tools de gobernanza (requiere la base de test_bd)."""
from datetime import date

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from steward_datos.contexto import fijar_en_bd
from steward_datos.contratos import ContextoUsuario, MetricaNoDisponible, ObtenerMetricaEntrada
from steward_datos.db.sesion import motor, sesion
from steward_datos.gobernanza import catalogo_datos, glosario, metricas
from steward_datos.tools.consultar_calidad import consultar_calidad
from steward_datos.tools.consultar_glosario import consultar_glosario
from steward_datos.tools.obtener_metrica import obtener_metrica

pytestmark = [pytest.mark.bd, pytest.mark.usefixtures("base_lista")]
ADMIN = ContextoUsuario(usuario_id="dev-admin", rol="administrador")
ANA = ContextoUsuario(usuario_id="dev-ana", rol="analista")
LUIS = ContextoUsuario(usuario_id="dev-luis", rol="analista")
VISTAS = ["v_facturas", "v_proveedores", "v_casos", "v_hallazgos", "v_ordenes_compra", "v_pagos", "v_centros_costo", "v_clientes"]


def contar(vista, rol, usuario):
    with sesion() as s:
        s.execute(text("SELECT set_config('app.rol', :r, true), set_config('app.usuario', :u, true)"), {"r": rol, "u": usuario})
        return s.execute(text(f"SELECT count(*) FROM {vista}")).scalar()


def test_sin_contexto_las_vistas_no_devuelven_nada():
    with sesion() as s:
        for v in VISTAS:
            assert s.execute(text(f"SELECT count(*) FROM {v}")).scalar() == 0, v


def test_seguridad_por_fila():
    total = contar("v_facturas", "administrador", "dev-admin")
    ana, luis = contar("v_facturas", "analista", "dev-ana"), contar("v_facturas", "analista", "dev-luis")
    assert ana + luis == total and ana > 0 and luis > 0  # entidades disjuntas que cubren todo
    assert contar("v_facturas", "analista", "nadie") == 0
    assert contar("v_facturas", "auditor", "dev-admin") == 0, "un rol desconocido no ve nada"
    with sesion() as s:
        s.execute(text("SELECT set_config('app.rol', 'analista', true), set_config('app.usuario', 'dev-luis', true)"))
        entidades = set(s.scalars(text("SELECT DISTINCT entidad_rfc FROM v_facturas")))
        assert entidades == {"SCD050920LM8"}
        assert "F-1042" not in set(s.scalars(text("SELECT caso_id FROM v_casos")))
    with sesion() as s:
        s.execute(text("SELECT set_config('app.rol', 'analista', true), set_config('app.usuario', 'dev-ana', true)"))
        assert "F-1042" in set(s.scalars(text("SELECT caso_id FROM v_casos")))


def test_enmascaramiento_de_datos_personales():
    with sesion() as s:
        s.execute(text("SELECT set_config('app.rol', 'analista', true), set_config('app.usuario', 'dev-diego', true)"))
        rfc, correo = s.execute(text("SELECT rfc, correo_contacto FROM v_clientes WHERE rfc IS NOT NULL AND correo_contacto LIKE '%@%' LIMIT 1")).one()
        assert "*" in rfc and "***@" in correo
    with sesion() as s:
        s.execute(text("SELECT set_config('app.rol', 'administrador', true)"))
        rfc, correo = s.execute(text("SELECT rfc, correo_contacto FROM v_clientes WHERE rfc IS NOT NULL AND correo_contacto LIKE '%@%' LIMIT 1")).one()
        assert "*" not in rfc and "***" not in correo


def test_usuario_de_consultas_solo_lee_vistas():
    if not motor().connect().execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'steward_consultas'")).scalar():
        pytest.skip("No existe el rol steward_consultas en este servidor")
    with motor().connect() as c:
        c.execute(text("SET ROLE steward_consultas"))
        c.execute(text("SET app.rol = 'administrador'"))
        assert c.execute(text("SELECT count(*) FROM v_facturas")).scalar() > 0
        with pytest.raises(Exception, match="permission denied"):
            c.execute(text("SELECT count(*) FROM facturas"))
        c.rollback()
        c.execute(text("SET ROLE steward_consultas"))
        with pytest.raises(Exception, match="permission denied"):
            c.execute(text("SELECT count(*) FROM bitacora"))


def _como_consultas():
    if not motor().connect().execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'steward_consultas'")).scalar():
        pytest.skip("No existe el rol steward_consultas en este servidor")
    s = Session(bind=motor().connect())
    s.execute(text("SET LOCAL ROLE steward_consultas"))
    return s


def test_usuario_de_consultas_no_puede_cambiar_su_rol_con_set_config():
    for sql in [
        "SELECT set_config('app.rol', 'administrador', true), * FROM v_clientes",
        "SELECT count(*) FROM (SELECT set_config('app.rol', 'administrador', true)) s, LATERAL (SELECT * FROM v_clientes) c",
        "WITH x AS MATERIALIZED (SELECT set_config('app.rol', 'administrador', true)) SELECT count(*) FROM x, v_clientes",
    ]:
        s = _como_consultas()
        fijar_en_bd(s, LUIS)
        with pytest.raises(Exception, match="permission denied for function set_config"):
            s.execute(text(sql))
        s.close()


def test_fijar_en_bd_funciona_con_el_usuario_de_consultas():
    s = _como_consultas()
    fijar_en_bd(s, LUIS)
    n, rfc = s.execute(text("SELECT count(*), max(rfc) FROM v_clientes")).one()
    assert 0 < n < 600 and "*" in rfc
    s.close()
    s = _como_consultas()
    fijar_en_bd(s, ADMIN)
    assert s.execute(text("SELECT count(*) FROM v_clientes")).scalar() == 600
    s.close()


def test_fijar_en_bd_rechaza_valores_que_romperian_el_set():
    with sesion() as s:
        for u in ["x'; SET app.rol = 'administrador", "a:b", "", "a" * 200]:
            with pytest.raises(ValueError):
                fijar_en_bd(s, ContextoUsuario.model_construct(usuario_id=u, rol="analista"))
        with pytest.raises(ValueError):
            fijar_en_bd(s, ContextoUsuario.model_construct(usuario_id="dev-ana", rol="auditor"))


def test_catalogo_documenta_cada_columna_de_las_vistas_y_cada_tabla():
    cat = {t["tabla"]: t for t in catalogo_datos()["tablas"]}
    insp = inspect(motor())
    for v in VISTAS:
        reales = [c["name"] for c in insp.get_columns(v)]
        documentadas = [c["columna"] for c in cat[v]["columnas"]]
        assert reales == documentadas, v
    tablas = set(insp.get_table_names()) - {"alembic_version"}
    assert tablas <= set(cat), f"Tablas sin ficha en el catálogo: {tablas - set(cat)}"
    terminos = {t["termino"] for t in glosario()["terminos"]}
    for t in cat.values():
        for c in t.get("columnas", []):
            if c.get("termino_glosario"):
                assert c["termino_glosario"] in terminos, c


def test_glosario_relacionados_existen():
    terminos = {t["termino"] for t in glosario()["terminos"]}
    for t in glosario()["terminos"]:
        assert set(t["relacionados"]) <= terminos, t["termino"]


@pytest.mark.parametrize("nombre", list(metricas()["metricas"]))
def test_cada_metrica_con_cada_dimension_se_ejecuta(nombre):
    m = metricas()["metricas"][nombre]
    r = obtener_metrica(ObtenerMetricaEntrada(metrica=nombre), ADMIN)
    assert len(r.filas) == 1 and r.definicion == m["definicion"]
    for d in m["dimensiones"]:
        r = obtener_metrica(ObtenerMetricaEntrada(metrica=nombre, dimensiones=[d], limite=200), ADMIN)
        assert r.filas and set(r.filas[0]) == {d, "valor"}
    for f in m.get("filtros", {}):
        obtener_metrica(ObtenerMetricaEntrada(metrica=nombre, filtros={f: "x"}), ADMIN)


def test_metrica_coincide_con_calculo_directo():
    r = obtener_metrica(ObtenerMetricaEntrada(metrica="monto_facturado", fecha_desde=date(2026, 10, 1), fecha_hasta=date(2026, 10, 31)), ADMIN)
    with sesion() as s:
        directo = s.execute(text("""
            SELECT sum(f.total * CASE WHEN f.moneda = 'USD' THEN 18.50 ELSE 1 END) FROM facturas f JOIN casos c ON c.id = f.caso_id
            WHERE coalesce(c.resultado_final, c.resultado_sugerido) IS DISTINCT FROM 'rechazado'
              AND f.fecha_emision BETWEEN '2026-10-01' AND '2026-10-31' AND f.tipo_documento = 'factura'""")).scalar()
    assert r.filas[0]["valor"] == pytest.approx(float(directo), abs=0.01)
    por_prov = obtener_metrica(ObtenerMetricaEntrada(metrica="monto_facturado", dimensiones=["proveedor"], limite=200,
                                                     fecha_desde=date(2026, 10, 1), fecha_hasta=date(2026, 10, 31)), ADMIN)
    assert sum(f["valor"] for f in por_prov.filas) == pytest.approx(r.filas[0]["valor"], abs=0.1)


def test_metrica_respeta_el_rol():
    total = obtener_metrica(ObtenerMetricaEntrada(metrica="numero_facturas"), ADMIN).filas[0]["valor"]
    ana = obtener_metrica(ObtenerMetricaEntrada(metrica="numero_facturas"), ANA).filas[0]["valor"]
    luis = obtener_metrica(ObtenerMetricaEntrada(metrica="numero_facturas"), LUIS).filas[0]["valor"]
    assert ana + luis == total and luis < ana


def test_metrica_sin_contexto_falla():
    with pytest.raises(PermissionError):
        obtener_metrica(ObtenerMetricaEntrada(metrica="numero_facturas"))


def test_metrica_rechaza_lo_que_no_esta_definido_e_inyeccion():
    assert isinstance(obtener_metrica(ObtenerMetricaEntrada(metrica="ventas_totales"), ADMIN), MetricaNoDisponible)
    r = obtener_metrica(ObtenerMetricaEntrada(metrica="monto_facturado", dimensiones=["proveedor; DROP TABLE casos"]), ADMIN)
    assert isinstance(r, MetricaNoDisponible)
    r = obtener_metrica(ObtenerMetricaEntrada(metrica="monto_facturado", filtros={"proveedor": "x' OR '1'='1"}), ADMIN)
    assert r.filas[0]["valor"] is None
    r = obtener_metrica(ObtenerMetricaEntrada(metrica="monto_facturado", filtros={"color": "rojo"}), ADMIN)
    assert isinstance(r, MetricaNoDisponible) and "no admite" in r.motivo


def test_metrica_trunca_y_paso():
    r = obtener_metrica(ObtenerMetricaEntrada(metrica="facturas_rechazadas", dimensiones=["proveedor"], limite=2), ADMIN)
    assert len(r.filas) == 2 and r.truncado and r.paso == "Contando facturas rechazadas por proveedor…"


@pytest.mark.parametrize("pregunta,esperado,tipo", [
    ("factura conciliada", "Factura conciliada", "exacta"),
    ("¿Qué significa Factura Conciliada?", "Factura conciliada", "exacta"),
    ("OC", "Orden de compra", "sinonimo"),
    ("dueño de los datos", "Data owner", "sinonimo"),
    ("datos personales", "Dato personal", "aproximada"),
])
def test_glosario(pregunta, esperado, tipo):
    r = consultar_glosario(pregunta)
    assert r.encontrado and r.termino.termino == esperado and r.coincidencia == tipo


def test_glosario_no_inventa():
    r = consultar_glosario("hipoteca inversa")
    assert not r.encontrado and r.termino is None


def test_calidad():
    r = consultar_calidad("tabla de facturas")
    assert r.tabla == "facturas" and {x.regla_id for x in r.reglas} == {"RC-001", "RC-002", "RC-003", "RC-004", "RC-005"}
    assert all(x.porcentaje_anterior is not None for x in r.reglas)
    assert all(x.cumple_umbral == (x.porcentaje >= x.umbral) for x in r.reglas)
    assert [x.regla_id for x in consultar_calidad("clientes", "validez").reglas] == ["RC-008", "RC-009"]
    vacia = consultar_calidad("inventario")
    assert vacia.reglas == [] and "facturas" in vacia.tablas_con_reglas
    # El último resultado se midió de verdad sobre los datos
    with sesion() as s:
        cumple, total = s.execute(text("SELECT count(*) FILTER (WHERE correo_contacto IS NOT NULL AND correo_contacto <> ''), count(*) FROM clientes")).one()
    rc7 = next(x for x in consultar_calidad("clientes").reglas if x.regla_id == "RC-007")
    assert rc7.porcentaje == pytest.approx(100 * cumple / total, abs=0.01) and rc7.registros_evaluados == total
