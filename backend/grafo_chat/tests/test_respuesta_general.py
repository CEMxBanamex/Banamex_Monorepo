import unittest

from backend.grafo_chat.herramientas_demo import (
    NO_ENTENDIDA,
    PRESENTACION,
    responder_general,
)


class TestRespuestaGeneral(unittest.TestCase):
    def respuesta(self, pregunta: str) -> str:
        return responder_general(pregunta)["respuesta"]

    def test_saludos_y_preguntas_sobre_el_asistente(self):
        for pregunta in (
            "Hola",
            "hola, ¿quién eres?",
            "Buenos días",
            "¿Qué puedes hacer?",
            "¿En qué me puedes ayudar?",
            "ayuda",
            "¿Cómo te llamas?",
        ):
            with self.subTest(pregunta=pregunta):
                self.assertEqual(self.respuesta(pregunta), PRESENTACION)

    def test_agradecimiento(self):
        self.assertTrue(self.respuesta("¡Gracias!").startswith("De nada"))

    def test_pregunta_no_entendida(self):
        self.assertEqual(self.respuesta("que es el interes compuesto"), NO_ENTENDIDA)

    def test_palabra_que_contiene_hola_no_es_saludo(self):
        self.assertEqual(self.respuesta("Holanda es un país"), NO_ENTENDIDA)

    def test_sin_fuentes(self):
        self.assertEqual(responder_general("Hola")["fuentes"], [])


if __name__ == "__main__":
    unittest.main()
