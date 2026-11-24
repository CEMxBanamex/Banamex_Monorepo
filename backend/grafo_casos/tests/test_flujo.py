import unittest

from pydantic import ValidationError

from backend.grafo_casos.flujo import (
    FlujoCasos,
    redactor,
    validador,
)
from backend.grafo_casos.herramientas_demo import (
    extraer_factura_demo,
    redactar_demo,
    validar_factura_demo,
)
from steward_datos.contratos import CampoLeido


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
            self.flujo.reanudar_caso(
                "caso-1",
                {"resultado": "humana", "motivo": " "},
            )

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

        self.assertEqual(
            self.flujo.reanudar_caso("caso-2", decision)["caso_id"],
            "caso-2",
        )
        self.assertEqual(
            self.flujo.reanudar_caso("caso-1", decision)["caso_id"],
            "caso-1",
        )

    def test_identificador_invalido(self):
        for caso_id in (None, "", "   "):
            with self.subTest(caso_id=caso_id):
                with self.assertRaises(ValueError):
                    self.flujo.procesar_caso(caso_id)

    def test_validador_rechaza_factura_incompleta_o_invalida(self):
        for factura in (None, [], {"campos": {}}):
            with self.subTest(factura=factura):
                with self.assertRaises(ValueError):
                    validador({"factura": factura})

    def test_redactor_rechaza_motivo_invalido(self):
        for motivo in (None, "", "   "):
            with self.subTest(motivo=motivo):
                with self.assertRaises(ValueError):
                    redactor({"motivo": motivo})


class TestHerramientasDemo(unittest.TestCase):
    def setUp(self):
        self.factura = extraer_factura_demo()

    def test_factura_consistente_es_aceptada(self):
        self.factura.campos["total"] = CampoLeido(valor="116.00")

        resultado, motivo = validar_factura_demo(self.factura)

        self.assertEqual(resultado, "aceptado")
        self.assertIn("coincide", motivo)

    def test_factura_con_diferencia_requiere_revision_humana(self):
        resultado, motivo = validar_factura_demo(self.factura)

        self.assertEqual(resultado, "humana")
        self.assertIn("4.00 MXN", motivo)

    def test_campo_obligatorio_faltante(self):
        del self.factura.campos["subtotal"]

        with self.assertRaisesRegex(ValueError, "subtotal"):
            validar_factura_demo(self.factura)

    def test_importe_vacio_o_invalido(self):
        for valor in ("", "abc"):
            with self.subTest(valor=valor):
                factura = extraer_factura_demo()
                factura.campos["total"] = CampoLeido(valor=valor)

                with self.assertRaises(ValueError):
                    validar_factura_demo(factura)

    def test_importe_no_finito(self):
        for valor in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(valor=valor):
                factura = extraer_factura_demo()
                factura.campos["total"] = CampoLeido(valor=valor)

                with self.assertRaisesRegex(ValueError, "finito"):
                    validar_factura_demo(factura)

    def test_redaccion_rechaza_motivo_vacio(self):
        for motivo in ("", "   ", None):
            with self.subTest(motivo=motivo):
                with self.assertRaises(ValueError):
                    redactar_demo(motivo)

    def test_redaccion_con_motivo_valido(self):
        explicacion = redactar_demo("Total inconsistente.")

        self.assertIn("Total inconsistente.", explicacion)
        self.assertIn("decisión final", explicacion)


if __name__ == "__main__":
    unittest.main()
