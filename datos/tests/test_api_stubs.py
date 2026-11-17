from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from steward_datos.api import crear_router_casos, crear_router_bitacora


class UsuarioFicticio:
    nombre = "Ana López"
    rol = "analista"


def dummy_usuario():
    return UsuarioFicticio()


@pytest.fixture
def client():
    app = FastAPI(title="Data Steward Test API")
    app.include_router(crear_router_casos(dummy_usuario), prefix="/api")
    app.include_router(crear_router_bitacora(dummy_usuario), prefix="/api")
    return TestClient(app)


def test_listar_casos(client):
    res = client.get("/api/casos")
    assert res.status_code == 200
    data = res.json()
    assert "casos" in data
    assert "metricas" in data
    assert len(data["casos"]) > 0
    assert data["metricas"]["total"] >= 5


def test_detalle_caso(client):
    res = client.get("/api/casos/F-1042")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "F-1042"
    assert len(data["campos"]) > 0
    assert len(data["hallazgos"]) > 0


def test_generar_url_subida(client):
    res = client.post("/api/casos/url-subida", json={
        "nombre_archivo": "factura_test.pdf",
        "tipo_documento": "Factura"
    })
    assert res.status_code == 200
    data = res.json()
    assert "upload_url" in data
    assert "s3_key" in data


def test_decision_caso(client):
    res = client.post("/api/casos/F-1042/decision", json={
        "accion": "confirmar",
        "resultado": "aceptado",
        "comentario": "Revisado por analista"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["caso_id"] == "F-1042"
    assert data["estado"] == "revisado"


def test_listar_bitacora(client):
    res = client.get("/api/bitacora")
    assert res.status_code == 200
    data = res.json()
    assert "eventos" in data
    assert "filtros" in data
    assert len(data["eventos"]) > 0
    assert "F-1042" in data["filtros"]["casos"]
