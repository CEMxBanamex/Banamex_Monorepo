import base64
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

import httpx
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pdfencrypt import StandardEncryption

from backend.grafo_casos.extraccion import ErrorExtraccion, extraer_campos_factura, _rasterizar_pdf


class TestPDF(unittest.TestCase):
    def pdf(self, paginas=1, tamano=(144, 144), cifrado=None):
        salida = BytesIO()
        c = canvas.Canvas(salida, pagesize=tamano, encrypt=cifrado)
        for i in range(paginas):
            c.setFillColorRGB(1 if i == 0 else 0, 0, 0)
            c.rect(0, 0, *tamano, fill=1, stroke=0)
            c.showPage()
        c.save()
        return salida.getvalue()

    def test_pdf_completo_llega_a_ollama_y_conserva_original(self):
        datos = self.pdf(2)
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'documento.bin'  # Identificación por contenido.
            ruta.write_bytes(datos)
            def responder(request):
                entrada = json.loads(request.content)
                imagen = Image.open(BytesIO(base64.b64decode(entrada['images'][0])))
                with imagen:
                    self.assertEqual(imagen.format, 'PNG')
                    self.assertEqual(imagen.size, (300, 600))
                    self.assertEqual(imagen.getpixel((150, 150))[:3], (255, 0, 0))
                    self.assertEqual(imagen.getpixel((150, 450))[:3], (0, 0, 0))
                return httpx.Response(200, json={'done': True, 'response': json.dumps({
                    'campos': {'folio': {'valor': 'X-1', 'etiqueta': 'Folio'}},
                    'texto_completo': 'Folio X-1'})})
            with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(responder)) as cliente:
                factura = extraer_campos_factura(str(ruta), cliente=cliente)
            self.assertEqual(factura.paginas, 2)
            self.assertIsNone(factura.campos['folio'].pagina)
            self.assertEqual(factura.campos['folio'].valor, 'X-1')
            self.assertEqual(ruta.read_bytes(), datos)

    def test_pdf_invalido_cifrado_y_fuera_de_limites_no_llaman_modelo(self):
        muestras = [b'%PDF-invalido', self.pdf(cifrado=StandardEncryption('secreto')),
                    self.pdf(5), self.pdf(tamano=(10000, 10000))]
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'factura.pdf'
            for datos in muestras:
                with self.subTest(bytes=len(datos)):
                    ruta.write_bytes(datos)
                    with httpx.Client(base_url='http://ollama', transport=httpx.MockTransport(
                            lambda r: self.fail('No debe llamarse Ollama'))) as cliente:
                        with self.assertRaises(ErrorExtraccion):
                            extraer_campos_factura(str(ruta), cliente=cliente)

    def test_rasteriza_todos_los_pdf_del_piloto(self):
        corpus = Path(__file__).resolve().parents[3] / 'db/semillas/sinteticos/facturas/evaluacion'
        archivos = sorted(corpus.glob('piloto_*.pdf'))
        self.assertEqual(len(archivos), 20)
        for archivo in archivos:
            with self.subTest(archivo=archivo.name):
                datos, paginas = _rasterizar_pdf(archivo.read_bytes())
                referencia = json.loads(archivo.with_suffix('.json').read_text(encoding='utf-8'))
                self.assertEqual(paginas, referencia['paginas'])
                with Image.open(BytesIO(datos)) as imagen:
                    self.assertEqual(imagen.format, 'PNG')
                    self.assertGreater(imagen.height, 0)
