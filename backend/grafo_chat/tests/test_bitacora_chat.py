import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from backend.grafo_chat.flujo import FlujoChat
from contratos.eventos_sse import RespuestaEvent


class TestBitacoraChat(unittest.IsolatedAsyncioTestCase):
    async def test_rechazo_consulta_caso_y_bitacora_con_misma_identidad(self):
        cliente = SimpleNamespace(ejecutar=AsyncMock(side_effect=[
            SimpleNamespace(structuredContent={
                "id": "F-1042", "estado": "revision", "resultado_sugerido": "humana",
                "resultado_final": None, "hallazgos": [{"regla_id": "R-014", "evidencia": "página 1, total"}],
            }),
            SimpleNamespace(structuredContent={"total": 1, "eventos": [{
                "actor_nombre": "Agente", "detalle": "Regla aplicada", "regla": "R-014",
            }]}),
        ]))
        eventos = [e async for e in FlujoChat(cliente).astream_chat(
            pregunta="¿Por qué se rechazó la factura F-1042?",
            usuario_id="dev-ana", rol="analista", caso_id="F-1042",
        )]
        final = next(e for e in eventos if isinstance(e, RespuestaEvent))
        self.assertEqual(final.fuentes, ["consultar_caso", "consultar_bitacora"])
        self.assertIn("Decisión final: Pendiente", final.respuesta)
        self.assertIn("R-014", final.respuesta)
        self.assertIn("página 1, total", final.respuesta)
        self.assertIn("Bitácora consultada", final.respuesta)
        llamadas = cliente.ejecutar.call_args_list
        self.assertEqual(llamadas[0].args[2], llamadas[1].args[2])
        self.assertEqual(llamadas[1].args[1]["entrada"]["caso_id"], "F-1042")

    async def test_error_bitacora_no_produce_respuesta_exitosa(self):
        cliente = SimpleNamespace(ejecutar=AsyncMock(side_effect=[
            SimpleNamespace(structuredContent={"id": "F-1042"}), RuntimeError("Fallo de bitácora"),
        ]))
        eventos = []
        with self.assertRaises(RuntimeError):
            async for evento in FlujoChat(cliente).astream_chat(
                pregunta="¿Por qué se rechazó la factura?", usuario_id="dev-ana",
                rol="analista", caso_id="F-1042",
            ):
                eventos.append(evento)
        self.assertFalse(any(isinstance(e, RespuestaEvent) for e in eventos))
        self.assertEqual(eventos[-1].estado, "error")
