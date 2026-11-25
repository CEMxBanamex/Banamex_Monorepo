from contextlib import contextmanager
from datetime import date
from io import BytesIO
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest
from steward_datos.contratos import ContextoUsuario
from steward_datos.db.models import Factura
from steward_datos.persistencia import guardar_extraccion

from backend.api import casos, subidas
from backend.api.main import app
from backend.grafo_casos.cfdi_xml import extraer_cfdi
from backend.grafo_casos.tests.test_cfdi_xml import CARPETA
from backend.grafo_casos.tests.test_flujo_real import AdaptadorPrueba

HEADERS = {"X-Usuario": "dev-ana", "X-Rol": "analista"}
USUARIO = ContextoUsuario(usuario_id="dev-ana", rol="analista")


@contextmanager
def sesion_prueba(*_):
    yield MagicMock()


@pytest.mark.parametrize("nombre", ["correcto", "total_incorrecto", "rfc_faltante", "invalido"])
def test_xml_por_http_con_parser_real_y_cierre_controlado(nombre):
    datos = b"<xml roto" if nombre == "invalido" else (CARPETA / f"cfdi_{nombre}.xml").read_bytes()
    s3, tools = MagicMock(), AdaptadorPrueba()
    s3.get_object.return_value = {"ContentLength": len(datos), "ContentType": "application/xml", "Body": BytesIO(datos)}
    cliente = TestClient(app)
    casos.FLUJOS.clear()
    try:
        with patch.dict(os.environ, {"AUTH_MODE": "dev", "S3_BUCKET": "prueba"}), \
                patch.object(casos, "sesion", sesion_prueba), \
                patch.object(casos, "caso_ya_subido", return_value=None), \
                patch.object(casos, "siguiente_id_caso", return_value="F-9703"), \
                patch.object(casos, "_cliente_s3", return_value=s3), \
                patch.object(casos, "HerramientasReales", return_value=tools), \
                patch("backend.grafo_casos.extraccion.httpx.Client") as modelo:
            respuesta = cliente.post("/api/casos", headers=HEADERS, json={
                "archivo": "factura.xml", "tipo": "Factura",
                "s3_key": subidas.prefijo_subida(USUARIO) + "a" * 32 + "/factura.xml"})
            modelo.assert_not_called()
            if nombre == "invalido":
                assert respuesta.status_code == 422, respuesta.text
                assert tools.errores == ["F-9703"]
                assert tools.guardados == []
                return
            assert respuesta.status_code == 201, respuesta.text
            assert respuesta.json()["estado"] == "revision"
            f = tools.guardados[0][1]
            assert f["origen_extraccion"] == "xml_cfdi" and f["uuid_fiscal"]
            assert f["modelo"] is None
            assert len(f["conceptos"]) == 2
            assert tools.revisiones[0]["revision_evidencia"]["habilitado_para_decision_automatica"] is False
            assert tools.cerrados == []
            otro = cliente.post("/api/casos/F-9703/decision", headers={**HEADERS, "X-Usuario": "otro"}, json={
                "accion": "confirmar", "resultado": "rechazado", "comentario": "Prueba"})
            assert otro.status_code == 404
            final = cliente.post("/api/casos/F-9703/decision", headers=HEADERS, json={
                "accion": "confirmar", "resultado": "rechazado", "comentario": "Prueba XML revisada"})
            assert final.status_code == 200, final.text
            assert len(tools.cerrados) == 1
    finally:
        casos.FLUJOS.clear()


def test_url_xml_firmada_sin_red_y_con_identidad():
    entorno = {"AUTH_MODE": "dev", "S3_BUCKET": "prueba", "AWS_ACCESS_KEY_ID": "prueba",
               "AWS_SECRET_ACCESS_KEY": "prueba", "AWS_REGION": "us-east-1", "S3_ENDPOINT_URL": "",
               "S3_ENDPOINT_PUBLICO": ""}
    with patch.dict(os.environ, entorno):
        subidas._cliente_s3.cache_clear()
        try:
            cliente = TestClient(app)
            respuesta = cliente.post("/api/casos/url-subida", headers=HEADERS, json={
                "nombre_archivo": "factura.XML", "tipo_documento": "Factura", "tamano_bytes": 1024})
            assert respuesta.status_code == 200, respuesta.text
            assert respuesta.json()["content_type"] == "application/xml"
            assert respuesta.json()["s3_key"].startswith(subidas.prefijo_subida(USUARIO))
            assert "if-none-match" in respuesta.json()["upload_url"]
            assert cliente.post("/api/casos/url-subida", json={
                "nombre_archivo": "factura.xml", "tipo_documento": "Factura"}).status_code == 401
        finally:
            subidas._cliente_s3.cache_clear()


def test_uuid_y_origen_se_guardan_en_salida_cruda_sin_migracion():
    f = extraer_cfdi((CARPETA / "cfdi_correcto.xml").read_bytes())
    s = MagicMock()
    s.get.return_value = Factura(caso_id="F-9704")
    factura = guardar_extraccion(s, "F-9704", f)
    assert factura.salida_cruda["uuid_fiscal"] == f.uuid_fiscal
    assert factura.salida_cruda["origen_extraccion"] == "xml_cfdi"
    assert factura.modelo_extraccion is None


def test_detalle_recupera_uuid_y_origen_con_autorizacion():
    f = extraer_cfdi((CARPETA / "cfdi_correcto.xml").read_bytes())
    c = SimpleNamespace(id="F-9704", archivo="factura.xml", tipo="factura", estado="revision",
                        resultado_sugerido="humana", resultado_final=None, explicacion="Pendiente",
                        creado_en=date(2026, 11, 24), responsable="dev-ana", campos=[], hallazgos=[], eventos=[])
    s = MagicMock()
    s.scalar.side_effect = [None, f.model_dump(mode="json")]

    @contextmanager
    def abrir(_):
        yield s

    with patch.dict(os.environ, {"AUTH_MODE": "dev", "S3_BUCKET": ""}), \
            patch.object(casos, "consultar_caso", return_value=c), patch.object(casos, "sesion_autorizada", abrir):
        r = TestClient(app).get("/api/casos/F-9704", headers=HEADERS)
    assert r.status_code == 200, r.text
    assert r.json()["uuid_fiscal"] == f.uuid_fiscal
    assert r.json()["origen_extraccion"] == "xml_cfdi"
