"""Recorrido HTTP con grafo y PostgreSQL reales; S3 y extracción se controlan en la prueba."""
from contextlib import contextmanager
from functools import partial
from io import BytesIO
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from steward_datos import config
from steward_datos.sinteticos import anotaciones, factura_desde_anotacion

from backend.api import casos, subidas
from backend.api.main import app
from backend.grafo_casos.flujo_real import FlujoCasosReal

BD_PRUEBAS = os.getenv("GRAFO_DATABASE_URL_PRUEBAS") or os.getenv("DATABASE_URL_PRUEBAS")
CABECERAS = {"X-Usuario": "dev-ana", "X-Rol": "analista"}


@unittest.skipUnless(BD_PRUEBAS, "Requiere PostgreSQL de pruebas migrado y con semillas")
class TestCasosE2E(unittest.TestCase):
    def test_subir_revisar_decidir_y_consultar_bitacora(self):
        motor = create_engine(BD_PRUEBAS)
        self.addCleanup(motor.dispose)

        @contextmanager
        def abrir():
            with Session(motor) as sesion, sesion.begin():
                yield sesion

        archivo = "piloto_012.png"
        original = Path(config.CARPETA_SINTETICOS, "facturas", "evaluacion", archivo).read_bytes()
        referencia = next(a for a in anotaciones("evaluacion") if a["archivo"] == archivo)
        factura = factura_desde_anotacion(referencia)
        s3 = MagicMock()
        s3.generate_presigned_url.return_value = "https://almacen.test/archivo"
        s3.get_object.return_value = {"ContentLength": len(original), "ContentType": "image/png", "Body": BytesIO(original)}

        with (
            TestClient(app) as cliente,
            patch.dict(os.environ, {"AUTH_MODE": "dev", "S3_BUCKET": "casos-pruebas"}),
            patch.object(casos, "_cliente_s3", return_value=s3),
            patch.object(subidas, "_cliente_s3", return_value=s3),
            patch.object(casos, "FLUJOS", {}),
            patch.object(casos, "sesion", abrir),
            patch("steward_datos.tools.consultas_chat_seguras.sesion", abrir),
            patch("backend.grafo_casos.herramientas_reales.sesion", abrir),
            patch.object(casos, "FlujoCasosReal", partial(FlujoCasosReal, extraer=lambda _: factura)),
            patch.object(config, "EMBEDDING_PROVEEDOR", "falso"),
        ):
            firma = cliente.post("/api/casos/url-subida", headers=CABECERAS,
                                 json={"nombre_archivo": archivo, "tipo_documento": "Factura", "tamano_bytes": len(original)})
            self.assertEqual(firma.status_code, 200, firma.text)
            entrada = {"archivo": archivo, "tipo": "Factura", "s3_key": firma.json()["s3_key"]}
            otro = {**CABECERAS, "X-Usuario": "dev-otro"}
            self.assertEqual(cliente.post("/api/casos", headers=otro, json=entrada).status_code, 422)
            nuevo = cliente.post("/api/casos", headers=CABECERAS, json=entrada)
            self.assertEqual(nuevo.status_code, 201, nuevo.text)
            caso_id = nuevo.json()["id"]
            self.assertEqual(nuevo.json()["estado"], "revision")
            repetido = cliente.post("/api/casos", headers=CABECERAS, json=entrada)
            self.assertEqual(repetido.json()["id"], caso_id)

            bandeja = cliente.get("/api/casos", headers=CABECERAS, params={"tipo": "Factura", "estado": "revision"})
            self.assertEqual(bandeja.status_code, 200, bandeja.text)
            self.assertIn(caso_id, {c["id"] for c in bandeja.json()["casos"]})

            self.assertEqual(cliente.get(f"/api/casos/{caso_id}", headers=otro).status_code, 404)
            detalle = cliente.get(f"/api/casos/{caso_id}", headers=CABECERAS)
            self.assertEqual(detalle.status_code, 200, detalle.text)
            self.assertTrue(any(h["regla"] == "R-014" for h in detalle.json()["hallazgos"]))

            decision = {"accion": "confirmar", "resultado": "rechazado", "comentario": "Comprobé la suma de la factura."}
            ruta = f"/api/casos/{caso_id}/decision"
            self.assertEqual(cliente.post(ruta, headers=otro, json=decision).status_code, 404)
            resultado = cliente.post(ruta, headers=CABECERAS, json=decision)
            self.assertEqual(resultado.status_code, 200, resultado.text)
            repetido = cliente.post(ruta, headers=CABECERAS, json=decision)
            self.assertEqual(repetido.json()["evento_id"], resultado.json()["evento_id"])

            historial = cliente.get("/api/bitacora", headers=CABECERAS, params={"caso": caso_id, "accion": "confirmacion"})
            self.assertEqual(historial.status_code, 200, historial.text)
            self.assertEqual(historial.json()["total"], 1)
            self.assertEqual(historial.json()["eventos"][0]["detalle"], decision["comentario"])
            oculto = cliente.get("/api/bitacora", headers=otro, params={"caso": caso_id})
            self.assertEqual(oculto.json()["total"], 0)
