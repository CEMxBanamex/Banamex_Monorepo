import unittest
from unittest.mock import patch

from steward_datos.contratos import ResultadoValidacion
from backend.grafo_casos.reproducir_reglas import clasificar


class TestReproduccionReglas(unittest.TestCase):
    def test_separa_resultado_de_reglas_de_revision_y_no_completa_errores(self):
        documentos = [{"archivo": "a.png", "esperado": {"resultado": "rechazado", "reglas": ["R-001"]}},
                      {"archivo": "b.pdf", "esperado": {"resultado": "humana", "reglas": ["R-021"]}}]
        registros = {"a.png": {"estado": "ok", "sin_filtro": {"campos": {
            "folio": {"valor": "AAA010101AAA", "etiqueta": "R.F.C."}}, "texto_completo": "R.F.C. AAA010101AAA"}},
                     "b.pdf": {"estado": "error", "error": "HTTP 500"}}
        resultado = ResultadoValidacion(caso_id="F-9600", reglas_evaluadas=[], hallazgos=[],
                                         resultado_sugerido="aceptado", motivo="fixture")
        with patch("backend.grafo_casos.reproducir_reglas.motor.validar_factura", return_value=resultado) as validar:
            r = clasificar(documentos, registros, "sin_filtro", lambda _: None)
        self.assertEqual(validar.call_count, 1)
        self.assertEqual(r["sugerencias_aceptado_no_esperadas"], ["a.png"])
        self.assertEqual(r["casos"][0]["predicho_reglas"], "aceptado")
        self.assertEqual(r["casos"][0]["sugerencia_modo_revision"], "humana")
        self.assertEqual(r["casos"][0]["reglas_esperadas_no_detectadas"], ["R-001"])
        self.assertEqual(r["casos"][1]["predicho_reglas"], "sin_salida")
        self.assertIsNone(r["casos"][1]["resultado_reglas"])
