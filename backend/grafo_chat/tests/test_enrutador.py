"""Pruebas unitarias del enrutador S3-15."""

import unittest

from backend.grafo_chat.enrutador import clasificar_dominio


class TestEnrutador(unittest.TestCase):

    def clasificar(self, pregunta):
        return clasificar_dominio({"pregunta": pregunta})["dominio"]

    def test_gobernanza(self):
        self.assertEqual(self.clasificar("políticas existentes"), "gobernanza")

    def test_glosario(self):
        self.assertEqual(self.clasificar("qué significa data owner"), "gobernanza")

    def test_calidad_de_datos(self):
        self.assertEqual(self.clasificar("calidad de datos"), "gobernanza")

    def test_casos(self):
        self.assertEqual(self.clasificar("estado del caso 123"), "casos")

    def test_facturas_se_clasifican_como_casos(self):
        self.assertEqual(self.clasificar("consulta las facturas"), "casos")

    def test_general(self):
        self.assertEqual(self.clasificar("hola cómo estás"), "general")

    def test_metricas_fuera_de_los_dos_dominios_ejecutables(self):
        self.assertEqual(self.clasificar("métricas de ventas"), "general")

    def test_fuera_de_alcance(self):
        self.assertEqual(self.clasificar("pronóstico del clima"), "fuera_de_alcance")

    def test_fuera_de_alcance_tiene_prioridad(self):
        self.assertEqual(
            self.clasificar("dame una receta de cocina para un caso"),
            "fuera_de_alcance",
        )

    def test_gobernanza_tiene_prioridad_sobre_casos(self):
        self.assertEqual(
            self.clasificar("políticas relacionadas con facturas"),
            "gobernanza",
        )

    def test_evitar_coincidencias_parciales(self):
        self.assertEqual(self.clasificar("casoide"), "general")
        self.assertEqual(self.clasificar("datossistema"), "general")

    def test_variantes_plural(self):
        self.assertEqual(self.clasificar("expedientes"), "casos")
        self.assertEqual(self.clasificar("reglas de calidad"), "gobernanza")

    def test_pregunta_vacia(self):
        with self.assertRaises(ValueError):
            self.clasificar("   ")

    def test_no_genera_intencion_mixta(self):
        resultado = clasificar_dominio({
            "pregunta": "políticas, facturas y casos"
        })

        self.assertNotEqual(resultado["dominio"], "mixta")
        self.assertEqual(resultado["dominio"], "gobernanza")
        self.assertEqual(resultado["dominios_objetivo"], ["gobernanza"])


if __name__ == "__main__":
    unittest.main()