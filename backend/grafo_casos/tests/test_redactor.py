import unittest
from unittest.mock import patch

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

    def test_redactor_sin_politica_marca_revision_humana(self):
        hallazgos = [
            {
                "regla_id": "R-999",
                "titulo": "Regla sin política vinculada",
                "evidencia": "página 2",
            }
        ]
        explicacion, detalles = redactar_explicacion_caso(
            caso_id="F-1099",
            resultado_sugerido="aceptado",
            motivo="Prueba",
            hallazgos=hallazgos,
        )
        self.assertNotIn("P-XXX", explicacion)
        self.assertIn("requiere revisión humana", explicacion)
        self.assertIn("HUMANA", explicacion)


    @patch("steward_datos.tools.registrar_hallazgo.registrar_hallazgo")
    def test_redactor_registra_revision_sin_inventar_politica(self, registrar):
        registrar.return_value.evento_id = 32
        resultado = ejecutar_redactor(
            caso_id="F-1099",
            resultado_sugerido="aceptado",
            motivo="Prueba",
            hallazgos=[{"regla_id": "R-014", "regla_version": "2.1", "politica_id": " "}],
            registrar_en_bd=True,
            sesion_bd=object(),
        )
        hallazgo = registrar.call_args.args[0].hallazgo
        self.assertEqual(hallazgo.politica_id, "")
        self.assertEqual(hallazgo.efecto, "revision")
        self.assertEqual(resultado["eventos_bitacora"], [32])
        self.assertIn("requiere revisión humana", resultado["explicacion"])


    @patch("steward_datos.tools.registrar_hallazgo.registrar_hallazgo", side_effect=RuntimeError("BD no disponible"))
    def test_redactor_registra_y_propaga_fallo_de_auditoria(self, registrar):
        with self.assertLogs("backend.grafo_casos.redactor", level="ERROR") as eventos:
            with self.assertRaisesRegex(RuntimeError, "BD no disponible"):
                ejecutar_redactor("F-1099", "humana", "Prueba", [
                    {"regla_id": "R-014", "regla_version": "2.1"},
                ], registrar_en_bd=True, sesion_bd=object())
        registrar.assert_called_once()
        self.assertIn("F-1099", eventos.output[0])


if __name__ == "__main__":
    unittest.main()
