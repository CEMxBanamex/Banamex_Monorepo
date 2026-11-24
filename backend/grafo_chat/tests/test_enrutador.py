
"""Pruebas unitarias del enrutador del grafo de chat."""

import unittest

from backend.grafo_chat.enrutador import clasificar_dominio


class TestEnrutador(unittest.TestCase):
    """Verifica la clasificación de preguntas por dominio."""

    def clasificar(self, pregunta):
        return clasificar_dominio({"pregunta": pregunta})["dominio"]

    def test_gobernanza(self):
        self.assertEqual(
            self.clasificar("politicas existentes"),
            "gobernanza",
        )

    def test_consultas(self):
        self.assertEqual(
            self.clasificar("metricas de ventas"),
            "consultas",
        )

    def test_casos(self):
        self.assertEqual(
            self.clasificar("estado del caso 123"),
            "casos",
        )

    def test_intencion_mixta(self):
        self.assertEqual(
            self.clasificar("metricas y politicas"),
            "mixta",
        )

    def test_calidad_de_datos_es_gobernanza(self):
        self.assertEqual(
            self.clasificar("calidad de datos"),
            "gobernanza",
        )

    def test_general(self):
        self.assertEqual(
            self.clasificar("hola como estas"),
            "general",
        )

    def test_fuera_de_alcance(self):
        self.assertEqual(
            self.clasificar("pronostico del clima"),
            "fuera_de_alcance",
        )

    def test_evitar_coincidencias_parciales(self):
        self.assertEqual(self.clasificar("casoide"), "general")
        self.assertEqual(self.clasificar("datossistema"), "general")

    def test_variantes_plural(self):
        self.assertEqual(self.clasificar("indicadores"), "consultas")
        self.assertEqual(self.clasificar("expedientes"), "casos")
        self.assertEqual(self.clasificar("reglas de calidad"), "gobernanza")

    def test_pregunta_vacia(self):
        with self.assertRaises(ValueError):
            self.clasificar("   ")


    def test_calidad_de_datos_con_intenciones_combinadas(self):
        casos = [
            ("calidad de datos", "gobernanza"),
            ("calidad de datos y metricas", "mixta"),
            ("calidad de datos y facturas", "mixta"),
            ("consulta de datos", "consultas"),
            ("metricas de ventas", "consultas"),
        ]

        for pregunta, dominio_esperado in casos:
            with self.subTest(pregunta=pregunta):
                self.assertEqual(
                    self.clasificar(pregunta),
                    dominio_esperado,
                )


    def test_pregunta_con_acentos(self):
        self.assertEqual(
            self.clasificar("políticas existentes"),
            "gobernanza",
        )

    def test_limite_de_dos_dominios(self):
        resultado = clasificar_dominio({
            "pregunta": "políticas, métricas y casos"
        })

        self.assertEqual(resultado["dominio"], "mixta")
        self.assertEqual(
            resultado["dominios_objetivo"],
            ["gobernanza", "consultas"],
        )



if __name__ == "__main__":
    unittest.main()
