from contextlib import contextmanager
from io import BytesIO
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from steward_datos.contratos import ContextoUsuario, FacturaExtraida

from backend.api import casos
from backend.api.main import app
from backend.api.subidas import prefijo_subida
from backend.grafo_casos.tests.test_flujo_real import AdaptadorPrueba


class TestCasosQwen(unittest.TestCase):
    def setUp(self):
        self.entorno = patch.dict(os.environ, {"AUTH_MODE": "dev", "S3_BUCKET": "prueba"})
        self.entorno.start()
        self.addCleanup(self.entorno.stop)
        self.client = TestClient(app)
        self.headers = {"X-Usuario": "dev-ana", "X-Rol": "analista"}
        self.usuario = ContextoUsuario(usuario_id="dev-ana", rol="analista")
        casos.FLUJOS.clear()
        self.addCleanup(casos.FLUJOS.clear)

    def test_pdf_llega_al_grafo_con_lecturas_y_decision_explicita(self):
        datos = b"%PDF-fixture del transporte; rasterizador cubierto por test_pdf"
        s3 = MagicMock()
        s3.get_object.return_value = {"ContentLength": len(datos), "ContentType": "application/pdf", "Body": BytesIO(datos)}
        tools = AdaptadorPrueba()
        factura = FacturaExtraida.model_validate({"campos": {
            "folio": {"valor": "F-8", "etiqueta": "Folio"},
            "subtotal": {"valor": "100", "etiqueta": "Subtotal"},
            "impuestos": {"valor": "16", "etiqueta": "IVA"},
            "total": {"valor": "116", "etiqueta": "Total"},
        }, "texto_completo": "Total 116"})

        @contextmanager
        def abrir():
            yield MagicMock()

        with patch.object(casos, "sesion", abrir), patch.object(casos, "caso_ya_subido", return_value=None), \
                patch.object(casos, "siguiente_id_caso", return_value="F-9601"), \
                patch.object(casos, "_cliente_s3", return_value=s3), \
                patch.object(casos, "HerramientasReales", return_value=tools), \
                patch("backend.grafo_casos.flujo_real.extraer_campos_factura", return_value=factura) as extraer:
            respuesta = self.client.post("/api/casos", headers=self.headers, json={
                "archivo": "prueba.pdf", "tipo": "Factura",
                "s3_key": prefijo_subida(self.usuario) + "a" * 32 + "/prueba.pdf"})
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        self.assertTrue(extraer.call_args.kwargs["conservar_lecturas"])
        self.assertEqual(tools.guardados[0][1]["campos"]["subtotal"]["valor"], "100")
        self.assertEqual(tools.guardados[0][2]["resultado_sugerido"], "humana")
        self.assertEqual(tools.revisiones[0]["revision_evidencia"]["campos"]["subtotal"]["estado"], "pendiente_revision")
        self.assertEqual(tools.cerrados, [])
        decision = {"accion": "confirmar", "resultado": "rechazado", "comentario": "Revisé el original"}
        otro = self.client.post("/api/casos/F-9601/decision", headers={**self.headers, "X-Usuario": "otro"}, json=decision)
        self.assertEqual(otro.status_code, 404)
        self.assertEqual(tools.cerrados, [])
        final = self.client.post("/api/casos/F-9601/decision", headers=self.headers, json=decision)
        self.assertEqual(final.status_code, 200, final.text)
        self.assertEqual(len(tools.cerrados), 1)

    def test_detalle_muestra_informe_y_conceptos_sin_reinferir(self):
        c = SimpleNamespace(id="F-9602", archivo="prueba.pdf", tipo="factura", estado="revision",
                            resultado_sugerido="humana", resultado_final=None, explicacion="Pendiente",
                            creado_en=__import__("datetime").datetime(2026, 11, 24), responsable="dev-ana",
                            campos=[SimpleNamespace(campo="subtotal", etiqueta="Subtotal", valor="100",
                                                    confianza=None, valor_corregido=None)], hallazgos=[], eventos=[])
        informe = {"campos": {"subtotal": {"estado": "pendiente_revision"}}, "requiere_revision_humana": True}
        session = MagicMock()
        session.scalar.side_effect = [{"revision_evidencia": informe},
                                      {"conceptos": [{"descripcion": "Servicio", "importe": "100"}]}]
        @contextmanager
        def abrir(_):
            yield session
        with patch.dict(os.environ, {"S3_BUCKET": ""}), \
                patch.object(casos, "consultar_caso", return_value=c), \
                patch.object(casos, "sesion_autorizada", abrir):
            respuesta = self.client.get("/api/casos/F-9602", headers=self.headers)
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["campos"][0]["estado_evidencia"], "pendiente_revision")
        self.assertEqual(respuesta.json()["conceptos"][0]["descripcion"], "Servicio")
        self.assertTrue(respuesta.json()["revision_evidencia"]["requiere_revision_humana"])

    def test_sin_autenticacion_no_puede_crear_casos(self):
        respuesta = self.client.post("/api/casos", json={"archivo": "prueba.pdf", "tipo": "Factura"})
        self.assertEqual(respuesta.status_code, 401)
