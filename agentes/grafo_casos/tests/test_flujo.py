import unittest

from pydantic import ValidationError

from agentes.grafo_casos.flujo import FlujoCasos


class TestFlujoCasos(unittest.TestCase):
    def setUp(self):
        self.flujo = FlujoCasos()

    def test_recorrido_y_pausa_antes_de_decidir(self):
        estado = self.flujo.procesar_caso("caso-1")
        self.assertEqual(estado["factura"]["campos"]["total"]["valor"], "120.00")
        self.assertEqual(estado["resultado_sugerido"], "humana")
        self.assertIn("116.00 MXN", estado["explicacion"])
        self.assertIn("4.00 MXN", estado["explicacion"])
        self.assertNotIn("decision_analista", estado)
        self.assertEqual(estado["__interrupt__"][0].value["caso_id"], "caso-1")

    def test_decision_invalida_no_consume_la_pausa(self):
        self.flujo.procesar_caso("caso-1")
        with self.assertRaises(ValidationError):
            self.flujo.reanudar_caso("caso-1", {"resultado": "humana", "motivo": " "})
        decision = {"resultado": "rechazado", "motivo": "El total no coincide."}
        final = self.flujo.reanudar_caso("caso-1", decision)
        self.assertEqual(final["decision_analista"], decision)
        self.assertEqual(final["resultado_sugerido"], "humana")
        self.assertNotIn("__interrupt__", final)
        with self.assertRaises(ValueError):
            self.flujo.reanudar_caso("caso-1", decision)

    def test_casos_aislados(self):
        self.flujo.procesar_caso("caso-1")
        self.flujo.procesar_caso("caso-2")
        with self.assertRaises(ValueError):
            self.flujo.procesar_caso("caso-2")
        decision = {"resultado": "rechazado", "motivo": "Total inconsistente."}
        with self.assertRaises(ValueError):
            self.flujo.reanudar_caso("desconocido", decision)
        self.assertEqual(self.flujo.reanudar_caso("caso-2", decision)["caso_id"], "caso-2")
        self.assertEqual(self.flujo.reanudar_caso("caso-1", decision)["caso_id"], "caso-1")
