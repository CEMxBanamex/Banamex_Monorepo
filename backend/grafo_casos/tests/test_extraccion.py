import json
from pathlib import Path
import tempfile
import unittest

import httpx
from PIL import Image

from backend.grafo_casos.extraccion import ErrorExtraccion, extraer_campos_factura


class TestExtraccion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archivo = Path(self.tmp.name) / "factura.png"
        Image.new("RGB", (10, 10), "white").save(self.archivo)

    def extraer(self, salida, **envoltura):
        def responder(request):
            entrada = json.loads(request.content)
            self.assertTrue(entrada["images"])
            self.assertEqual(entrada["options"]["temperature"], 0)
            return httpx.Response(200, json={"done": True, "response": json.dumps(salida), **envoltura})
        with httpx.Client(base_url="http://ollama", transport=httpx.MockTransport(responder)) as cliente:
            return extraer_campos_factura(str(self.archivo), cliente=cliente)

    def test_conserva_nulos_y_descarta_mediciones_no_verificadas(self):
        salida = {"campos": {"total": {"valor": "447.04", "etiqueta": "TOTAL", "confianza": 99, "bbox": [1, 2, 3, 4]},
                             "impuestos": {"valor": None}}, "texto_completo": "TOTAL 447.04"}
        factura = self.extraer(salida)
        self.assertIsNone(factura.campos["impuestos"].valor)
        self.assertIsNone(factura.campos["total"].confianza)
        self.assertIsNone(factura.campos["total"].bbox)
        self.assertEqual(factura.campos["total"].valor, "447.04")

    def test_descuento_no_es_impuesto_y_subtotal_no_es_total(self):
        factura = self.extraer({"campos": {
            "folio": {"valor": "ABC-12", "etiqueta": "Invoice number"},
            "impuestos": {"valor": "14.51", "etiqueta": "DISCOUNT"},
            "total": {"valor": "569.02", "etiqueta": "SUB_TOTAL"},
        }, "texto_completo": "Invoice number ABC-12\nSUB_TOTAL 569.02\nDISCOUNT 14.51"})
        self.assertEqual(factura.campos["folio"].valor, "ABC-12")
        self.assertIsNone(factura.campos["impuestos"].valor)
        self.assertIsNone(factura.campos["total"].valor)

    def test_rechaza_respuestas_vacias_y_truncadas(self):
        for salida, envoltura in [({"campos": {}}, {}),
                                  ({"campos": {"total": {"valor": "1"}}}, {"done_reason": "length"}),
                                  ({"campos": {"desconocido": {"valor": "1"}}}, {})]:
            with self.subTest(salida=salida), self.assertRaises(ErrorExtraccion):
                self.extraer(salida, **envoltura)

    def test_rechaza_archivo_que_no_es_imagen(self):
        self.archivo.write_text("documento inválido")
        with self.assertRaises(ErrorExtraccion):
            extraer_campos_factura(str(self.archivo))
