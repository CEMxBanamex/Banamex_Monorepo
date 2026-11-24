"""Pruebas de la URL prefirmada de subida (S3-04). Firmar no llama a AWS, así que no necesitan red."""
import os
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from backend.api import subidas
from backend.api.main import app

ENTORNO_AWS = {
    "S3_BUCKET": "dsa-dev-archivos-pruebas",
    "AWS_REGION": "us-east-1",
    "AWS_ACCESS_KEY_ID": "pruebas",
    "AWS_SECRET_ACCESS_KEY": "pruebas",
    "S3_ENDPOINT_PUBLICO": "",
    "S3_ENDPOINT_URL": "",
}


class TestUrlSubida(unittest.TestCase):
    def setUp(self):
        subidas._cliente_s3.cache_clear()
        self.cliente = TestClient(app)

    def pedir(self, entorno=None, **cuerpo):
        datos = {"nombre_archivo": "factura 1042.pdf", "tipo_documento": "Factura", **cuerpo}
        with mock.patch.dict(os.environ, entorno or ENTORNO_AWS, clear=False):
            subidas._cliente_s3.cache_clear()
            return self.cliente.post("/api/casos/url-subida", json=datos)

    def test_url_firmada_para_el_bucket_del_ambiente(self):
        respuesta = self.pedir()
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        datos = respuesta.json()
        url = urlparse(datos["upload_url"])
        consulta = parse_qs(url.query)
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.hostname, "dsa-dev-archivos-pruebas.s3.amazonaws.com")
        self.assertEqual(url.path, "/" + datos["s3_key"])
        self.assertIn("X-Amz-Signature", consulta)
        self.assertEqual(consulta["X-Amz-Expires"], ["900"])
        # El Content-Type va dentro de la firma: el navegador debe mandar el mismo.
        self.assertIn("content-type", consulta["X-Amz-SignedHeaders"][0])
        self.assertEqual(datos["content_type"], "application/pdf")
        self.assertEqual(datos["expira_en_segundos"], 900)

    def test_llave_unica_y_nombre_saneado(self):
        primera = self.pedir(nombre_archivo="../../etc/factura (copia)#1.PDF").json()
        segunda = self.pedir(nombre_archivo="../../etc/factura (copia)#1.PDF").json()
        self.assertRegex(primera["s3_key"], r"^casos/[0-9a-f]{32}/factura_copia_1\.PDF$")
        self.assertNotEqual(primera["s3_key"], segunda["s3_key"])
        self.assertNotIn("..", primera["s3_key"])

    def test_extensiones_por_tipo_de_caso(self):
        self.assertEqual(self.pedir(nombre_archivo="registros.csv").status_code, 422)
        self.assertEqual(self.pedir(nombre_archivo="malware.exe").status_code, 422)
        self.assertEqual(self.pedir(nombre_archivo="sin_extension").status_code, 422)
        csv = self.pedir(nombre_archivo="registros.csv", tipo_documento="Validación con políticas")
        self.assertEqual(csv.status_code, 200)
        self.assertEqual(csv.json()["content_type"], "text/csv")
        imagen = self.pedir(nombre_archivo="ticket.JPG")
        self.assertEqual(imagen.json()["content_type"], "image/jpeg")

    def test_entradas_invalidas(self):
        self.assertEqual(self.pedir(tipo_documento="Otro").status_code, 422)
        self.assertEqual(self.pedir(nombre_archivo="").status_code, 422)
        self.assertEqual(self.pedir(nombre_archivo="...").status_code, 422)
        self.assertEqual(self.pedir(tamano_bytes=21 * 1024 * 1024).status_code, 422)
        self.assertEqual(self.pedir(tamano_bytes=1024).status_code, 200)
        self.assertEqual(self.pedir(campo_extra=True).status_code, 422)

    def test_sin_bucket_responde_503(self):
        respuesta = self.pedir({**ENTORNO_AWS, "S3_BUCKET": ""})
        self.assertEqual(respuesta.status_code, 503)

    def test_local_firma_con_el_host_que_ve_el_navegador(self):
        entorno = {**ENTORNO_AWS, "S3_BUCKET": "dsa-local", "S3_ENDPOINT_URL": "http://s3:8333",
                   "S3_ENDPOINT_PUBLICO": "http://localhost:8333"}
        url = urlparse(self.pedir(entorno).json()["upload_url"])
        self.assertEqual((url.scheme, url.netloc), ("http", "localhost:8333"))
        self.assertTrue(url.path.startswith("/dsa-local/casos/"))


class TestNombreSeguro(unittest.TestCase):
    def test_recorta_conservando_la_extension(self):
        nombre = subidas.nombre_seguro("a" * 300 + ".xlsx")
        self.assertEqual(len(nombre), 100)
        self.assertTrue(nombre.endswith(".xlsx"))

    def test_rutas_de_windows(self):
        self.assertEqual(subidas.nombre_seguro("C:\\Users\\ana\\factura.pdf"), "factura.pdf")


if __name__ == "__main__":
    unittest.main()
