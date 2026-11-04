"""Integración contra PostgreSQL: migración, semilla y tools de datos. La base de DATABASE_URL_PRUEBAS se borra."""
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.bd
RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module", autouse=True)
def base_lista():
    url = os.environ["DATABASE_URL_PRUEBAS"]
    with create_engine(url, isolation_level="AUTOCOMMIT").connect() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    env = {**os.environ, "DATABASE_URL": url, "EMBEDDING_PROVEEDOR": "falso"}
    subprocess.run(["alembic", "upgrade", "head"], cwd=RAIZ, env=env, check=True, capture_output=True)
    subprocess.run([sys.executable, "scripts/cargar_semilla.py", "--embeddings"], cwd=RAIZ, env=env, check=True, capture_output=True)


def test_semilla_reproduce_el_frontend():
    from steward_datos.tools.consultas_chat import consultar_caso
    c = consultar_caso("F-1042")
    assert (c.estado, c.resultado_sugerido) == ("revision", "humana")
    assert [h.regla_id for h in c.hallazgos] == ["R-003", "R-014"]
    fecha = next(x for x in c.campos if x.campo == "fecha")
    assert (fecha.valor, fecha.confianza, fecha.valor_corregido) == ("12/03/2026", 62, "12/08/2026")
    v = consultar_caso("V-0207")
    assert v.resultado_sugerido == "rechazado" and v.hallazgos[0].filas == [14, 27, 33, 48, 61, 79, 95, 112]
    assert consultar_caso("V-0206").estado == "error"
    assert consultar_caso("f-1040").resultado_final == "rechazado"


def test_buscar_facturas():
    from steward_datos.contratos import BuscarFacturasEntrada
    from steward_datos.tools.consultas_chat import buscar_facturas
    r = buscar_facturas(BuscarFacturasEntrada(con_regla="R-014"))
    assert {f.caso_id for f in r.facturas} == {"F-1040", "F-1042"}
    r = buscar_facturas(BuscarFacturasEntrada(emisor="proveedor demo"))
    assert [f.caso_id for f in r.facturas] == ["F-1042"]
    r = buscar_facturas(BuscarFacturasEntrada(resultado="aceptado", limite=5))
    assert r.total_coincidencias == 31 and len(r.facturas) == 5
    r = buscar_facturas(BuscarFacturasEntrada(emisor="'; DROP TABLE casos; --"))
    assert r.total_coincidencias == 0


def test_validar_reglas_detecta_duplicados_contra_la_base():
    from steward_datos.contratos import ValidarReglasEntrada
    from steward_datos.sinteticos import anotaciones, factura_desde_anotacion
    from steward_datos.tools.validar_reglas import validar_reglas
    for d in anotaciones("evaluacion"):
        if d["escenario"] in ("duplicado_exacto", "duplicado_folio", "proveedor_no_padron", "receptor_ajeno", "correcta"):
            r = validar_reglas(ValidarReglasEntrada(caso_id="F-9000", historia=1, factura=factura_desde_anotacion(d),
                                                    sha256=d["sha256"], fecha_recepcion=date(2026, 11, 2)))
            assert r.resultado_sugerido == d["esperado"]["resultado"], d["archivo"]
            assert sorted({h.regla_id for h in r.hallazgos}) == d["esperado"]["reglas"]


def test_buscar_politicas_respeta_vigencia():
    from steward_datos.contratos import BuscarPoliticasEntrada
    from steward_datos.tools.buscar_politicas import buscar_politicas
    hoy = buscar_politicas(BuscarPoliticasEntrada(consulta="tolerancia del total de la factura", fecha=date(2026, 11, 2)))
    assert {(f.politica_id, f.version) for f in hoy.fragmentos if f.politica_id == "P-002"} == {("P-002", "2.0")}
    antes = buscar_politicas(BuscarPoliticasEntrada(consulta="tolerancia del total de la factura", fecha=date(2025, 6, 1)))
    assert antes.fragmentos and all(f.politica_id == "P-002" and f.version == "1.0" for f in antes.fragmentos)
    r = buscar_politicas(BuscarPoliticasEntrada(consulta="tasas de IVA", reglas=["R-011"]))
    assert r.fragmentos and all("R-011" in f.reglas for f in r.fragmentos)


def test_registrar_hallazgo_y_bitacora_inmutable():
    from steward_datos.contratos import HallazgoOut, RegistrarHallazgoEntrada
    from steward_datos.db.sesion import sesion
    from steward_datos.tools.registrar_hallazgo import registrar_hallazgo
    h = HallazgoOut(regla_id="R-014", regla_version="2.1", politica_id="P-002", efecto="rechazo", severidad="error",
                    titulo="Prueba", texto="Prueba de integración")
    r = registrar_hallazgo(RegistrarHallazgoEntrada(caso_id="F-1041", hallazgo=h))
    assert r.hallazgo_id and r.evento_id
    with pytest.raises(ValueError):
        registrar_hallazgo(RegistrarHallazgoEntrada(caso_id="F-1041", hallazgo=h.model_copy(update={"regla_version": "9.9"})))
    with pytest.raises(Exception, match="no admite"):
        with sesion() as s:
            s.execute(text("UPDATE bitacora SET detalle = 'alterado' WHERE id = :i"), {"i": r.evento_id})


def test_ingesta_de_nueva_version_cierra_la_anterior():
    from steward_datos.db.models import Politica
    from steward_datos.db.sesion import sesion
    from steward_datos.rag.ingesta import ingestar_politica
    nueva = (RAIZ / "politicas" / "P-018_unicidad_clientes_v1.0.md").read_text(encoding="utf-8")
    nueva = nueva.replace('version: "1.0"', 'version: "1.1"').replace("vigente_desde: 2026-03-01", "vigente_desde: 2026-12-01")
    with sesion() as s:
        p, accion = ingestar_politica(s, nueva, "P-018_v1.1.md", cargada_por="Admin de prueba")
        assert accion == "nueva" and all(f.embedding is not None for f in p.fragmentos)
        assert ingestar_politica(s, nueva, "P-018_v1.1.md")[1] == "sin_cambios"
        anterior = s.get(Politica, ("P-018", "1.0"))
        assert anterior.estado == "reemplazada" and anterior.vigente_hasta == date(2026, 11, 30)


def test_endpoint_politicas():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from steward_datos.api.politicas import crear_router
    rol = {"valor": "analista"}
    app = FastAPI()
    app.include_router(crear_router(lambda: SimpleNamespace(nombre="Prueba", rol=rol["valor"])), prefix="/api")
    cli = TestClient(app)
    texto = (RAIZ / "politicas" / "P-015_fechas_alta_v1.1.md").read_bytes()
    assert cli.post("/api/politicas", files={"archivo": ("P-015.md", texto)}).status_code == 403
    rol["valor"] = "administrador"
    assert cli.post("/api/politicas", files={"archivo": ("x.pdf", b"%PDF")}).status_code == 415
    assert cli.post("/api/politicas", files={"archivo": ("x.md", b"# sin metadatos")}).status_code == 422
    r = cli.post("/api/politicas", files={"archivo": ("P-015.md", texto)})
    assert r.status_code == 201 and r.json()["accion"] == "sin_cambios"
    assert any(p["id"] == "P-007" for p in cli.get("/api/politicas").json())


def test_tools_se_registran_en_mcp():
    pytest.importorskip("mcp")
    try:
        from mcp.server.mcpserver import MCPServer as Servidor
    except ImportError:
        from mcp.server.fastmcp import FastMCP as Servidor
    import anyio
    from steward_datos.mcp_registro import registrar_tools_datos
    mcp = Servidor("prueba")
    registrar_tools_datos(mcp)
    nombres = {t.name for t in anyio.run(mcp.list_tools)}
    assert nombres == {"validar_reglas", "buscar_politicas", "registrar_hallazgo", "consultar_caso", "buscar_facturas"}
