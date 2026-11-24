import json
from pathlib import Path
import tempfile
import unittest

import httpx
from PIL import Image

from backend.grafo_casos.extraccion import ErrorExtraccion, extraer_campos_factura
from steward_datos.contratos import CAMPOS_FACTURA


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
            esquema = entrada["format"]
            esquema_visible = json.loads(entrada["prompt"].split("ESQUEMA_JSON:\n", 1)[1])
            self.assertEqual(esquema_visible, esquema)
            for campo in CAMPOS_FACTURA:
                self.assertTrue(esquema_visible["properties"]["campos"]["properties"][campo]["description"])
            self.assertIn("campos", esquema["required"])
            self.assertIn("texto_completo", esquema["required"])
            self.assertEqual(set(esquema["properties"]["campos"]["required"]), set(CAMPOS_FACTURA))
            self.assertEqual(set(esquema["$defs"]["CampoLeido"]["required"]), {"valor", "etiqueta"})
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
        for salida, envoltura in [({"campos": {}, "texto_completo": "Folio 23175403 Total 134,494.76"}, {}),
                                  ({"campos": {"total": {"valor": "1"}}}, {"done_reason": "length"}),
                                  ({"campos": {"desconocido": {"valor": "1"}}}, {})]:
            with self.subTest(salida=salida), self.assertRaises(ErrorExtraccion):
                self.extraer(salida, **envoltura)

    def test_rechaza_archivo_que_no_es_imagen(self):
        self.archivo.write_text("documento inválido")
        with self.assertRaises(ErrorExtraccion):
            extraer_campos_factura(str(self.archivo))

    def test_etiquetas_literales_y_encabezado_sin_etiqueta(self):
        factura = self.extraer({"campos": {
            "emisor_nombre": {"valor": "Empresa Ejemplo SA", "etiqueta": None},
            "emisor_direccion": {"valor": "Calle Prueba 10", "etiqueta": None},
            "receptor_nombre": {"valor": "Cliente Ejemplo SA", "etiqueta": "Receptor"},
            "emisor_rfc": {"valor": "AAA010101AAA", "etiqueta": "RFC"},
            "impuestos": {"valor": "16.00", "etiqueta": "IVA 16 %"},
            "total": {"valor": "116.00", "etiqueta": "Total"},
        }, "texto_completo": "Empresa Ejemplo SA\nRFC AAA010101AAA\nCalle Prueba 10\n"
           "Receptor\nCliente Ejemplo SA\nIVA 16 % 16.00\nTotal 116.00"})
        self.assertTrue(all(c.valor is not None for c in factura.campos.values()))
        self.assertIsNone(factura.campos["emisor_nombre"].etiqueta)

    def test_excepcion_sin_etiqueta_no_admite_importes_ni_textos_parciales(self):
        factura = self.extraer({"campos": {
            "folio": {"valor": "X-10", "etiqueta": "Folio"},
            "emisor_nombre": {"valor": "Empresa", "etiqueta": None},
            "receptor_nombre": {"valor": "Cliente", "etiqueta": "Receptor Nombre"},
            "total": {"valor": "116.00", "etiqueta": None},
            "emisor_rfc": {"valor": "AAA010101AAA", "etiqueta": None},
        }, "texto_completo": "Folio X-10\nEmpresa Ejemplo\nCliente Ejemplo\nRFC AAA010101AAA\nTotal 116.00"})
        self.assertEqual(factura.campos["folio"].valor, "X-10")
        for nombre in ("emisor_nombre", "receptor_nombre", "total", "emisor_rfc"):
            self.assertIsNone(factura.campos[nombre].valor)

    def test_conserva_encabezado_completo_sin_inventar_etiqueta(self):
        factura = self.extraer({"campos": {
            "emisor_nombre": {"valor": "Proveedor Ejemplo SA", "etiqueta": "Emisor"},
            "emisor_direccion": {"valor": "Calle Ejemplo 15", "etiqueta": "Dirección"},
        }, "texto_completo": "Proveedor Ejemplo SA\nCalle Ejemplo 15"})
        self.assertEqual(factura.campos["emisor_nombre"].valor, "Proveedor Ejemplo SA")
        self.assertEqual(factura.campos["emisor_direccion"].valor, "Calle Ejemplo 15")
        self.assertTrue(all(c.etiqueta is None for c in factura.campos.values()))

    def test_separa_prefijo_rfc_solo_si_esta_transcrito(self):
        factura = self.extraer({"campos": {
            "folio": {"valor": "F-5", "etiqueta": "Folio"},
            "emisor_rfc": {"valor": "RFC AAA010101AAA", "etiqueta": "Emisor RFC"},
            "receptor_rfc": {"valor": "RFC BBB020202BBB", "etiqueta": "RFC"},
        }, "texto_completo": "Folio F-5\nRFC AAA010101AAA"})
        self.assertEqual(factura.campos["emisor_rfc"].valor, "AAA010101AAA")
        self.assertEqual(factura.campos["emisor_rfc"].etiqueta, "RFC")
        self.assertIsNone(factura.campos["receptor_rfc"].valor)

    def test_rfc_sin_etiqueta_en_bloque_receptor(self):
        factura = self.extraer({"campos": {
            "receptor_nombre": {"valor": "Cliente Ejemplo SA", "etiqueta": "RECEPTOR"},
            "receptor_rfc": {"valor": "BBB020202BBB", "etiqueta": None},
        }, "texto_completo": "RECEPTOR\nCliente Ejemplo SA\nBBB020202BBB"})
        self.assertEqual(factura.campos["receptor_rfc"].valor, "BBB020202BBB")
        self.assertIsNone(factura.campos["receptor_rfc"].etiqueta)
        self.assertIsNone(factura.campos["receptor_rfc"].confianza)

    def test_rfc_sin_etiqueta_rechaza_bloques_ambiguos_y_valores_sin_respaldo(self):
        for texto in (
            "EMISOR\nCliente Ejemplo SA\nBBB020202BBB",  # Otro rol.
            "RECEPTOR\nOtro Cliente SA\nBBB020202BBB",  # Otro nombre.
            "RECEPTOR\nCliente Ejemplo SA\nRFC BBB020202BBB",  # No es línea completa.
            "RECEPTOR\nCliente Ejemplo SA\nBBB020202BBB9",  # Coincidencia parcial.
            "RECEPTOR\nCliente Ejemplo SA\nMoneda MXN\nBBB020202BBB",  # Otro bloque.
            "RECEPTOR\nCliente Ejemplo SA\nBBB020202BBB\nBBB020202BBB",  # Ambiguo.
            "RECEPTOR\nCliente Ejemplo SA",  # Ausente.
        ):
            with self.subTest(texto=texto):
                factura = self.extraer({"campos": {
                    "folio": {"valor": "F-1", "etiqueta": "Folio"},
                    "receptor_nombre": {"valor": "Cliente Ejemplo SA", "etiqueta": "RECEPTOR"},
                    "receptor_rfc": {"valor": "BBB020202BBB", "etiqueta": None},
                }, "texto_completo": "Folio F-1\n" + texto})
                self.assertIsNone(factura.campos["receptor_rfc"].valor)

    def test_no_conserva_folio_y_fecha_omitidos_en_transcripcion(self):
        factura = self.extraer({"campos": {
            "folio": {"valor": "23175403", "etiqueta": "Folio"},
            "fecha": {"valor": "27/09/2026", "etiqueta": "Fecha"},
            "total": {"valor": "116.00", "etiqueta": "Total"},
        }, "texto_completo": "Total 116.00"})
        self.assertIsNone(factura.campos["folio"].valor)
        self.assertIsNone(factura.campos["fecha"].valor)
