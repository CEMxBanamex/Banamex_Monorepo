"""Pruebas del grafo de chat."""
from unittest.mock import Mock, patch

from backend.grafo_chat import flujo as modulo_flujo

import unittest

from backend.grafo_chat.flujo import FlujoChat, ejecutar_dominios

from contratos.eventos_sse import (
    EstadoPaso,
    PasoEvent,
    RespuestaEvent,
    TipoRespuesta,
)


class TestFlujoChat(unittest.TestCase):
    """Pruebas de enrutamiento, ejecución y eventos del chat."""

    def setUp(self):
        self.flujo = FlujoChat()

    def ejecutar_chat(self, pregunta):
        return list(
            self.flujo.stream_chat(
                pregunta=pregunta,
                usuario_id="usuario_demo",
                rol="analista",
            )
        )

    def test_gobernanza(self):
        eventos = self.ejecutar_chat("politicas existentes")
        respuesta = eventos[-1]

        self.assertIsInstance(respuesta, RespuestaEvent)
        self.assertEqual(respuesta.tipo, TipoRespuesta.POLITICAS)
        self.assertEqual(respuesta.fuentes, ["politicas_demo"])

    def test_consultas(self):
        eventos = self.ejecutar_chat("consulta las metricas")
        respuesta = eventos[-1]

        self.assertEqual(respuesta.tipo, TipoRespuesta.DATOS)
        self.assertEqual(respuesta.fuentes, ["datos_demo"])

    def test_casos(self):
        eventos = self.ejecutar_chat("estado del caso 123")
        respuesta = eventos[-1]

        self.assertEqual(respuesta.tipo, TipoRespuesta.DATOS)
        self.assertEqual(respuesta.fuentes, ["casos_demo"])

    def test_intencion_mixta(self):
        eventos = self.ejecutar_chat("metricas y politicas")
        respuesta = eventos[-1]

        self.assertEqual(respuesta.tipo, TipoRespuesta.MIXTA)
        self.assertEqual(
            respuesta.fuentes,
            ["politicas_demo", "datos_demo"],
        )

    def test_general(self):
        eventos = self.ejecutar_chat("hola como estas")
        respuesta = eventos[-1]

        self.assertEqual(
            respuesta.tipo,
            TipoRespuesta.INFORMACION_GENERAL,
        )
        self.assertEqual(respuesta.fuentes, [])

    def test_fuera_de_alcance(self):
        eventos = self.ejecutar_chat("pronostico del clima")
        respuesta = eventos[-1]

        self.assertEqual(
            respuesta.tipo,
            TipoRespuesta.INFORMACION_GENERAL,
        )
        self.assertEqual(respuesta.fuentes, [])

    def test_eventos_de_progreso(self):
        eventos = self.ejecutar_chat("politicas existentes")

        pasos = [
            evento for evento in eventos
            if isinstance(evento, PasoEvent)
        ]

        self.assertEqual(len(pasos), 4)

        self.assertEqual(
            [paso.estado for paso in pasos],
            [
                EstadoPaso.EN_CURSO,
                EstadoPaso.COMPLETADO,
                EstadoPaso.EN_CURSO,
                EstadoPaso.COMPLETADO,
            ],
        )

        self.assertEqual(
            [paso.id for paso in pasos],
            ["enrutador", "enrutador", "ejecutor", "ejecutor"],
        )

    def test_respuesta_final(self):
        eventos = self.ejecutar_chat("consulta las metricas")

        self.assertIsInstance(eventos[-1], RespuestaEvent)
        self.assertTrue(eventos[-1].simulado)
        self.assertIsNotNone(eventos[-1].duracion_ms)
        self.assertGreaterEqual(eventos[-1].duracion_ms, 0)

    def test_pregunta_vacia(self):
        with self.assertRaises(ValueError):
            self.ejecutar_chat(" ")

    def test_usuario_vacio(self):
        with self.assertRaises(ValueError):
            list(
                self.flujo.stream_chat(
                    pregunta="hola",
                    usuario_id=" ",
                    rol="analista",
                )
            )

    def test_rol_invalido(self):
        with self.assertRaises(ValueError):
            list(
                self.flujo.stream_chat(
                    pregunta="hola",
                    usuario_id="usuario_demo",
                    rol="invitado",
                )
            )
    def test_dominios_objetivo_vacios(self):
        with self.assertRaisesRegex(
            ValueError,
            "Debe haber uno o dos dominios objetivo",
        ):
            ejecutar_dominios({
                "dominio": "mixta",
                "pregunta": "prueba",
                "dominios_objetivo": [],
            })

    def test_mas_de_dos_dominios(self):
        with self.assertRaisesRegex(
            ValueError,
            "Debe haber uno o dos dominios objetivo",
        ):
            ejecutar_dominios({
                "dominio": "mixta",
                "pregunta": "prueba",
                "dominios_objetivo": [
                    "gobernanza",
                    "consultas",
                    "casos",
                ],
            })

    def test_secuencia_eventos_intencion_mixta(self):
        eventos = self.ejecutar_chat("metricas y politicas")

        # Todos los eventos deben respetar los contratos.
        self.assertTrue(
            all(
                isinstance(evento, (PasoEvent, RespuestaEvent))
                for evento in eventos
            )
        )

        # Debe existir exactamente una respuesta final.
        respuestas = [
            evento
            for evento in eventos
            if isinstance(evento, RespuestaEvent)
        ]

        self.assertEqual(len(respuestas), 1)

        # La respuesta debe ser el último evento.
        self.assertIsInstance(eventos[-1], RespuestaEvent)

        # La respuesta debe conservar el tipo de intención mixta.
        self.assertEqual(
            eventos[-1].tipo,
            TipoRespuesta.MIXTA,
        )

        # Todos los eventos anteriores deben ser pasos de progreso.
        self.assertTrue(
            all(
                isinstance(evento, PasoEvent)
                for evento in eventos[:-1]
            )
        )

    def test_error_en_herramienta_emite_evento(self):
        herramienta_fallida = Mock(
            side_effect=RuntimeError("Error simulado")
        )

        eventos = []

        with patch.dict(
            modulo_flujo.HERRAMIENTAS,
            {"gobernanza": herramienta_fallida},
        ):
            generador = self.flujo.stream_chat(
                pregunta="politicas existentes",
                usuario_id="usuario_demo",
                rol="analista",
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "Error simulado",
            ):
                while True:
                    eventos.append(next(generador))

        paso_error = [
            evento
            for evento in eventos
            if isinstance(evento, PasoEvent)
            and evento.estado == EstadoPaso.ERROR
        ]

        self.assertEqual(len(paso_error), 1)
        self.assertEqual(paso_error[0].id, "ejecutor")
        herramienta_fallida.assert_called_once()

    def test_dominio_no_soportado(self):
        with self.assertRaisesRegex(
            ValueError,
            "Dominios no soportados",
        ):
            ejecutar_dominios({
                "dominio": "mixta",
                "pregunta": "prueba",
                "dominios_objetivo": ["finanzas"],
            })

    def test_dominio_individual_incoherente(self):
        estado = {
            "dominio": "gobernanza",
            "dominios_objetivo": ["casos"],
            "pregunta": "consulta de prueba",
        }

        with self.assertRaisesRegex(
            ValueError,
            "debe coincidir",
        ):
            ejecutar_dominios(estado)

    def test_intencion_mixta_con_dominios_duplicados(self):
        estado = {
            "dominio": "mixta",
            "dominios_objetivo": ["gobernanza", "gobernanza"],
            "pregunta": "consulta de prueba",
        }

        with self.assertRaisesRegex(
            ValueError,
            "dos dominios objetivo diferentes",
        ):
            ejecutar_dominios(estado)

    def test_general_con_dominios_objetivo(self):
        estado = {
            "dominio": "general",
            "dominios_objetivo": ["consultas"],
            "pregunta": "hola",
        }

        with self.assertRaisesRegex(
            ValueError,
            "no debe tener dominios objetivo",
        ):
            ejecutar_dominios(estado)

    def test_fuera_de_alcance_con_dominios_objetivo(self):
        estado = {
            "dominio": "fuera_de_alcance",
            "dominios_objetivo": ["casos"],
            "pregunta": "pronostico del clima",
        }

        with self.assertRaisesRegex(
            ValueError,
            "no debe tener dominios objetivo",
        ):
            ejecutar_dominios(estado)


    def test_caso_id_se_conserva_en_respuesta(self):
        eventos = list(
            self.flujo.stream_chat(
                pregunta="estado del caso 123",
                usuario_id="usuario_demo",
                rol="analista",
                caso_id="CASO-123",
            )
        )

        respuesta = eventos[-1]

        self.assertIsInstance(respuesta, RespuestaEvent)
        self.assertEqual(respuesta.caso_id, "CASO-123")


    def test_orden_secuencial_herramientas_mixtas(self):
        orden = []

        def herramienta_gobernanza(pregunta):
            orden.append("gobernanza")
            return {
                "dominio": "gobernanza",
                "respuesta": "Resultado de gobernanza",
                "fuentes": ["politicas_demo"],
            }

        def herramienta_consultas(pregunta):
            orden.append("consultas")
            return {
                "dominio": "consultas",
                "respuesta": "Resultado de consultas",
                "fuentes": ["datos_demo"],
            }

        with patch.dict(
            modulo_flujo.HERRAMIENTAS,
            {
                "gobernanza": herramienta_gobernanza,
                "consultas": herramienta_consultas,
            },
        ):
            estado = {
                "dominio": "mixta",
                "dominios_objetivo": [
                    "gobernanza",
                    "consultas",
                ],
                "pregunta": "politicas y metricas",
            }

            resultado = ejecutar_dominios(estado)

        self.assertEqual(
            orden,
            ["gobernanza", "consultas"],
        )
        self.assertEqual(
            resultado["dominios_ejecutados"],
            ["gobernanza", "consultas"],
        )





if __name__ == "__main__":
    unittest.main()
