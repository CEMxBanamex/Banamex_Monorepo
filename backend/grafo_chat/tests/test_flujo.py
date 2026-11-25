"""Pruebas unitarias del grafo asíncrono de chat."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from steward_datos.contratos import ContextoUsuario

from backend.grafo_chat.flujo import FlujoChat
from contratos.eventos_sse import (
    EstadoPaso,
    PasoEvent,
    RespuestaEvent,
    TipoRespuesta,
)


class TestFlujoChat(unittest.IsolatedAsyncioTestCase):
    """Prueba el flujo asíncrono sin depender de un servidor MCP real."""

    def setUp(self):
        self.cliente_mcp = SimpleNamespace(
            ejecutar=AsyncMock(
                return_value=SimpleNamespace(
                    structuredContent={"resultado": "Resultado de prueba"}
                )
            )
        )
        self.flujo = FlujoChat(cliente_mcp=self.cliente_mcp)

    async def ejecutar_chat(self, pregunta, **kwargs):
        return [
            evento
            async for evento in self.flujo.astream_chat(
                pregunta=pregunta,
                usuario_id="usuario_demo",
                rol="analista",
                **kwargs,
            )
        ]

    async def test_gobernanza_ejecuta_busqueda_politicas(self):
        pregunta = "políticas existentes"
        eventos = await self.ejecutar_chat(pregunta)

        respuesta = eventos[-1]

        self.assertIsInstance(respuesta, RespuestaEvent)
        self.assertEqual(respuesta.tipo, TipoRespuesta.POLITICAS)
        self.assertEqual(respuesta.fuentes, ["buscar_politicas"])
        self.assertFalse(respuesta.simulado)

        self.cliente_mcp.ejecutar.assert_awaited_once_with(
            "buscar_politicas",
            {"entrada": {"consulta": pregunta}},
            ContextoUsuario(
                usuario_id="usuario_demo",
                rol="analista",
            ),
        )

    async def test_pregunta_con_dos_intenciones_ejecuta_un_solo_dominio(self):
        eventos = await self.ejecutar_chat(
            "Busca políticas relacionadas con facturas"
        )

        respuesta = eventos[-1]

        self.assertEqual(respuesta.tipo, TipoRespuesta.POLITICAS)
        self.assertEqual(respuesta.fuentes, ["buscar_politicas"])
        self.assertFalse(respuesta.simulado)

        self.cliente_mcp.ejecutar.assert_awaited_once_with(
            "buscar_politicas",
            {"entrada": {"consulta": "Busca políticas relacionadas con facturas"}},
            unittest.mock.ANY,
        )


    async def test_calidad_de_datos_ejecuta_consultar_calidad(self):
        pregunta = "\u00bfQu\u00e9 significa calidad de datos?"

        self.cliente_mcp.ejecutar.return_value = SimpleNamespace(
            structuredContent={
                "reglas": [
                    {
                        "regla_id": "RC-001",
                        "tabla": "facturas",
                        "dimension": "completitud",
                        "descripcion": "Toda factura tiene RFC.",
                        "porcentaje": 100.0,
                        "umbral": 99.0,
                        "cumple_umbral": True,
                    },
                    {
                        "regla_id": "RC-002",
                        "tabla": "facturas",
                        "dimension": "unicidad",
                        "descripcion": "No hay folios duplicados.",
                        "porcentaje": 98.0,
                        "umbral": 99.5,
                        "cumple_umbral": False,
                    },
                ],
                "tablas_con_reglas": ["facturas"],
            }
        )

        eventos = await self.ejecutar_chat(pregunta)
        respuesta = eventos[-1]

        self.assertEqual(respuesta.fuentes, ["consultar_calidad"])
        self.assertIn("Reglas evaluadas: 2", respuesta.respuesta)
        self.assertIn("Reglas que no cumplen su umbral: 1", respuesta.respuesta)
        self.assertIn("RC-002", respuesta.respuesta)
        self.assertIn("98.0%", respuesta.respuesta)
        self.assertNotIn('"reglas":', respuesta.respuesta)

        self.cliente_mcp.ejecutar.assert_awaited_once_with(
            "consultar_calidad",
            {},
            unittest.mock.ANY,
        )

    async def test_concepto_especifico_se_consulta_en_glosario(self):
        pregunta = "\u00bfQu\u00e9 significa completitud?"

        eventos = await self.ejecutar_chat(pregunta)
        respuesta = eventos[-1]

        self.assertEqual(respuesta.fuentes, ["consultar_glosario"])

        self.cliente_mcp.ejecutar.assert_awaited_once_with(
            "consultar_glosario",
            {"termino": "completitud"},
            unittest.mock.ANY,
        )

    async def test_consulta_de_facturas(self):
        eventos = await self.ejecutar_chat("consulta las facturas")

        respuesta = eventos[-1]

        self.assertEqual(respuesta.tipo, TipoRespuesta.DATOS)
        self.assertEqual(respuesta.fuentes, ["buscar_facturas"])

        self.cliente_mcp.ejecutar.assert_awaited_once_with(
            "buscar_facturas",
            {"entrada": {"limite": 20}},
            unittest.mock.ANY,
        )

    async def test_consulta_de_caso_con_identificador(self):
        eventos = await self.ejecutar_chat(
            "estado del caso",
            caso_id="CASO-123",
        )

        respuesta = eventos[-1]

        self.assertEqual(respuesta.tipo, TipoRespuesta.DATOS)
        self.assertEqual(respuesta.caso_id, "CASO-123")
        self.assertEqual(respuesta.fuentes, ["consultar_caso"])

        self.cliente_mcp.ejecutar.assert_awaited_once_with(
            "consultar_caso",
            {"entrada": {"caso_id": "CASO-123"}},
            unittest.mock.ANY,
        )

    async def test_caso_sin_identificador_no_ejecuta_herramienta(self):
        eventos = await self.ejecutar_chat("estado del caso")

        respuesta = eventos[-1]

        self.assertEqual(respuesta.tipo, TipoRespuesta.DATOS)
        self.assertEqual(respuesta.fuentes, [])
        self.assertIn("identificador", respuesta.respuesta.lower())

        self.cliente_mcp.ejecutar.assert_not_awaited()

    async def test_metricas_no_invoca_herramientas_mcp(self):
        eventos = await self.ejecutar_chat("consulta las métricas de ventas")

        respuesta = eventos[-1]

        self.assertEqual(
            respuesta.tipo,
            TipoRespuesta.INFORMACION_GENERAL,
        )
        self.assertFalse(respuesta.simulado)
        self.assertEqual(respuesta.fuentes, [])

        self.cliente_mcp.ejecutar.assert_not_awaited()

    async def test_respuesta_general(self):
        eventos = await self.ejecutar_chat("hola, ¿cómo estás?")

        respuesta = eventos[-1]

        self.assertEqual(
            respuesta.tipo,
            TipoRespuesta.INFORMACION_GENERAL,
        )
        self.assertFalse(respuesta.simulado)
        self.assertEqual(respuesta.fuentes, [])

        self.cliente_mcp.ejecutar.assert_not_awaited()

    async def test_fuera_de_alcance(self):
        eventos = await self.ejecutar_chat("pronóstico del clima")

        respuesta = eventos[-1]

        self.assertEqual(
            respuesta.tipo,
            TipoRespuesta.INFORMACION_GENERAL,
        )
        self.assertFalse(respuesta.simulado)
        self.assertEqual(respuesta.fuentes, [])

        self.cliente_mcp.ejecutar.assert_not_awaited()

    async def test_eventos_de_progreso(self):
        eventos = await self.ejecutar_chat("políticas existentes")

        pasos = [
            evento
            for evento in eventos
            if isinstance(evento, PasoEvent)
        ]

        self.assertEqual(len(pasos), 4)

        self.assertEqual(
            [paso.id for paso in pasos],
            ["enrutador", "enrutador", "ejecutor", "ejecutor"],
        )

        self.assertEqual(
            [paso.estado for paso in pasos],
            [
                EstadoPaso.EN_CURSO,
                EstadoPaso.COMPLETADO,
                EstadoPaso.EN_CURSO,
                EstadoPaso.COMPLETADO,
            ],
        )

    async def test_una_sola_respuesta_final(self):
        eventos = await self.ejecutar_chat("políticas existentes")

        respuestas = [
            evento
            for evento in eventos
            if isinstance(evento, RespuestaEvent)
        ]

        self.assertEqual(len(respuestas), 1)
        self.assertIsInstance(eventos[-1], RespuestaEvent)

    async def test_duracion_no_negativa(self):
        eventos = await self.ejecutar_chat("políticas existentes")

        respuesta = eventos[-1]

        self.assertIsNotNone(respuesta.duracion_ms)
        self.assertGreaterEqual(respuesta.duracion_ms, 0)

    async def test_pregunta_vacia(self):
        with self.assertRaisesRegex(ValueError, "pregunta"):
            await self.ejecutar_chat(" ")

    async def test_usuario_vacio(self):
        with self.assertRaisesRegex(ValueError, "usuario"):
            [
                evento
                async for evento in self.flujo.astream_chat(
                    pregunta="hola",
                    usuario_id=" ",
                    rol="analista",
                )
            ]

    async def test_rol_invalido(self):
        with self.assertRaisesRegex(ValueError, "rol"):
            [
                evento
                async for evento in self.flujo.astream_chat(
                    pregunta="hola",
                    usuario_id="usuario_demo",
                    rol="invitado",
                )
            ]

    async def test_error_mcp_emite_evento_y_propaga_error(self):
        self.cliente_mcp.ejecutar.side_effect = RuntimeError(
            "Error de conexión MCP"
        )

        eventos = []

        with self.assertRaisesRegex(RuntimeError, "Error de conexión MCP"):
            async for evento in self.flujo.astream_chat(
                pregunta="políticas existentes",
                usuario_id="usuario_demo",
                rol="analista",
            ):
                eventos.append(evento)

        errores = [
            evento
            for evento in eventos
            if isinstance(evento, PasoEvent)
            and evento.estado == EstadoPaso.ERROR
        ]

        self.assertEqual(len(errores), 1)
        self.assertEqual(errores[0].id, "ejecutor")


if __name__ == "__main__":
    unittest.main()
