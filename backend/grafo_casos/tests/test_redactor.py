import unittest

from backend.grafo_casos.redactor import ejecutar_redactor, redactar_explicacion_caso


class TestRedactorHallazgos(unittest.TestCase):
    def test_redactor_sin_hallazgos_aceptado(self):
        explicacion, detalles = redactar_explicacion_caso(
            caso_id="F-1041",
            resultado_sugerido="aceptado",
            motivo="El total coincide con subtotal más impuestos.",
        )
        self.assertIn("F-1041", explicacion)
        self.assertIn("Aceptado", explicacion)
        self.assertEqual(len(detalles), 0)

    def test_redactor_con_hallazgos_estructurados(self):
        hallazgos = [
            {
                "regla_id": "R-014",
                "regla_version": "2.1",
                "politica_id": "P-002",
                "politica_seccion": "sección 5",
                "titulo": "Discrepancia aritmética en total",
                "cifras": [["Esperado", "11,600.00 MXN"], ["Encontrado", "12,000.00 MXN"], ["Diferencia", "400.00 MXN"]],
                "evidencia": "página 1, campo total",
                "severidad": "error",
            },
            {
                "regla_id": "R-003",
                "regla_version": "1.0",
                "politica_id": "P-002",
                "politica_seccion": "sección 2",
                "titulo": "Fecha leída con baja confianza",
                "evidencia": "página 1, campo fecha",
                "severidad": "adv",
            },
        ]
        res = ejecutar_redactor(
            caso_id="F-1042",
            resultado_sugerido="humana",
            motivo="Discrepancias encontradas",
            hallazgos=hallazgos,
        )
        exp = res["explicacion"]
        self.assertIn("HUMANA", exp)
        self.assertIn("R-014 v2.1", exp)
        self.assertIn("P-002 (sección 5)", exp)
        self.assertIn("página 1, campo total", exp)
        self.assertIn("Esperado: 11,600.00 MXN", exp)
        self.assertIn("Diferencia: 400.00 MXN", exp)
        self.assertEqual(len(res["hallazgos_redactados"]), 2)
        self.assertIn("analista de cuentas por pagar", exp)


if __name__ == "__main__":
    unittest.main()
