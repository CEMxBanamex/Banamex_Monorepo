import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from steward_datos.contratos import CampoLeido, FacturaExtraida
from backend.grafo_casos.evaluacion import (
    CORPUS, calificar, cargar_corpus, extraer_documento, generar_reportes, huellas_codigo, normalizado, resumir, sha,
)


class TestEvaluacion(unittest.TestCase):
    def test_huellas_incluyen_catalogo_configurado_existente(self):
        from steward_datos.config import CATALOGO_REGLAS
        huellas = huellas_codigo()
        self.assertEqual(huellas['catalogo_reglas_sha256'], sha(CATALOGO_REGLAS))
        self.assertTrue(all(len(v) == 64 for v in huellas.values()))

    def test_corpus_completo_y_huellas(self):
        docs = cargar_corpus()
        self.assertEqual(len(docs), 39)
        self.assertEqual(sum(d['archivo'].endswith('.pdf') for d in docs), 20)
        self.assertEqual(sum(d['paginas'] == 2 for d in docs), 4)

    def test_no_inflar_precision_con_nulos_o_excluir_errores(self):
        docs = cargar_corpus()[:2]
        campos = {n: {'valor': v} for n, v in docs[0]['verdad']['campos'].items()}
        campos['emisor_rfc']['valor'] = 'GSS070101186W'  # Error real observado: no se corrige al calificar.
        campos['retenciones']['valor'] = '0.00'  # Ausente no equivale a cero impreso.
        registros = {docs[0]['archivo']: {'estado': 'pausa', 'salida': {'factura': {'campos': campos},
                     'resultado': {'resultado_sugerido': 'rechazado', 'hallazgos': []}}},
                     docs[1]['archivo']: {'estado': 'error', 'error': 'Ollama desconectado'}}
        resumen = resumir(docs, registros)
        self.assertEqual(resumen['total_corpus'], 2)
        self.assertEqual(resumen['errores'], 1)
        self.assertEqual(resumen['clasificacion']['exactitud_sobre_corpus'], 0)
        self.assertEqual(resumen['clasificacion']['matriz']['aceptado']['sin_salida'], 1)
        self.assertEqual(resumen['extraccion']['valores_correctos'], 12)
        self.assertEqual(resumen['extraccion']['valores_emitidos'], 14)
        self.assertEqual(resumen['extraccion']['valores_esperados'], 26)
        self.assertEqual(resumen['extraccion']['por_campo']['emisor_rfc']['correctos'], 0)

    def test_pendientes_y_falso_aceptado_se_conservan_en_denominador(self):
        docs = [d for d in cargar_corpus() if d['esperado']['resultado'] != 'aceptado'][:2]
        resumen = resumir(docs, {docs[0]['archivo']: {'estado': 'pausa', 'salida': {
            'resultado': {'resultado_sugerido': 'aceptado', 'hallazgos': []}}}})
        self.assertEqual(resumen['pendientes'], 1)
        self.assertEqual(resumen['clasificacion']['falsos_aceptados'], 1)
        self.assertEqual(resumen['clasificacion']['exactitud_sobre_corpus'], 0)

    def test_normalizacion_no_oculta_diferencias_reales(self):
        self.assertEqual(normalizado('total', '$ 1,234.50'), normalizado('total', '1234.50'))
        self.assertNotEqual(normalizado('total', None), normalizado('total', '0'))
        self.assertNotEqual(normalizado('total', 'null'), normalizado('total', None))
        self.assertEqual(normalizado('tasa_iva', 'IVA 16 %'), normalizado('tasa_iva', '16'))
        self.assertEqual(normalizado('fecha', '27/09/2026'), normalizado('fecha', '2026-09-27'))
        self.assertNotEqual(normalizado('emisor_rfc', 'GSS07010186W'), normalizado('emisor_rfc', 'GSS070101186W'))

    def test_pdf_incluye_segunda_pagina_sin_entregar_verdad_al_extractor(self):
        import pymupdf
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'dos.pdf'
            doc = pymupdf.open()
            doc.new_page(width=100, height=100)
            doc.new_page(width=100, height=100)
            doc[1].draw_rect(doc[1].rect, fill=(0, 0, 0))
            doc.save(ruta); doc.close()
            def leer_solo_imagen(archivo):
                with Image.open(archivo) as imagen:
                    self.assertEqual(imagen.format, 'PNG')
                    self.assertGreater(imagen.height, imagen.width)
                    self.assertLess(sum(imagen.getpixel((20, imagen.height - 20))), 10)
                return FacturaExtraida(campos={'folio': CampoLeido(valor='X')})
            factura = extraer_documento(ruta, extraer=leer_solo_imagen)
            self.assertEqual(factura.paginas, 2)

    def test_todos_los_pdf_pueden_renderizarse(self):
        for d in cargar_corpus():
            if d['archivo'].endswith('.pdf'):
                with self.subTest(archivo=d['archivo']):
                    factura = extraer_documento(CORPUS / d['archivo'], extraer=lambda _: FacturaExtraida())
                    self.assertEqual(factura.paginas, d['paginas'])

    def test_informe_parcial_se_identifica_y_conserva_39_documentos(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            generar_reportes(carpeta, cargar_corpus(), {})
            resumen = json.loads((carpeta / 'resumen.json').read_text())
            self.assertEqual(resumen['pendientes'], 39)
            self.assertIsNone(resumen['extraccion']['precision_valores'])
            self.assertIn('pendientes: 39', (carpeta / 'informe.md').read_text())
            self.assertEqual(len(resumen['casos']), 39)


if __name__ == '__main__':
    unittest.main()
