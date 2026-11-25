
"""Pruebas HTTP del endpoint de chat y su transmisión SSE."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app
from contratos.eventos_sse import (
    EstadoPaso,
    PasoEvent,
    RespuestaEvent,
    TipoRespuesta,
)


class TestChatAPI(unittest.TestCase):
    """Prueba autenticación, validación y transmisión de eventos."""

    def setUp(self):
        self.client = TestClient(app)
        self.url = "/api/chat/stream"
        self.headers = {
            "X-Usuario": "usuario_demo",
            "X-Rol": "analista",
            "Accept": "text/event-stream",
        }
        self.payload = {"mensaje": "Consulta las políticas"}

    @staticmethod
    async def eventos_falsos(**kwargs):
        yield PasoEvent(
            id="enrutador",
            texto="Clasificando solicitud",
            estado=EstadoPaso.EN_CURSO,
        )
        yield RespuestaEvent(
            respuesta="Respuesta de prueba",
            simulado=False,
            duracion_ms=10,
            tipo=TipoRespuesta.POLITICAS,
            fuentes=["buscar_politicas"],
        )

    def test_chat_autenticado_transmite_eventos_sse(self):
        with (
            patch.dict(os.environ, {"AUTH_MODE": "dev"}),
            patch("backend.api.chat_stream.FlujoChat") as flujo_cls,
        ):
            flujo_cls.return_value.astream_chat.side_effect = (
                self.eventos_falsos
            )

            response = self.client.post(
                self.url,
                json=self.payload,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "text/event-stream",
            response.headers["content-type"],
        )
        self.assertIn("data:", response.text)
        self.assertIn("Clasificando solicitud", response.text)
        self.assertIn("Respuesta de prueba", response.text)
        self.assertIn("buscar_politicas", response.text)

        flujo_cls.assert_called_once()
        flujo_cls.return_value.astream_chat.assert_called_once()

        kwargs = flujo_cls.return_value.astream_chat.call_args.kwargs
        self.assertEqual(kwargs["usuario_id"], "dev-ana")
        self.assertEqual(kwargs["rol"], "analista")
        self.assertEqual(kwargs["pregunta"], self.payload["mensaje"])

    def test_auth_no_configurada_devuelve_503(self):
        with patch.dict(os.environ, {"AUTH_MODE": ""}):
            response = self.client.post(
                self.url,
                json=self.payload,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("autenticación configurada", response.text.lower())

    def test_encabezado_de_rol_no_sobrescribe_rol_de_desarrollo(self):
        async def eventos_falsos(**kwargs):
            yield RespuestaEvent(
                respuesta="Respuesta de prueba",
                simulado=False,
                duracion_ms=10,
                tipo=TipoRespuesta.POLITICAS,
                fuentes=["buscar_politicas"],
            )

        headers = {
            "X-Usuario": "usuario_demo",
            "X-Rol": "invitado",
            "Accept": "text/event-stream",
        }

        with (
            patch.dict(os.environ, {"AUTH_MODE": "dev"}),
            patch("backend.api.chat_stream.FlujoChat") as flujo_cls,
        ):
            flujo_cls.return_value.astream_chat.side_effect = eventos_falsos

            response = self.client.post(
                self.url,
                json=self.payload,
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)

        kwargs = flujo_cls.return_value.astream_chat.call_args.kwargs
        self.assertEqual(kwargs["usuario_id"], "dev-ana")
        self.assertEqual(kwargs["rol"], "analista")

    def test_mensaje_vacio_devuelve_422(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json={"mensaje": ""},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 422)

    def test_campo_no_permitido_devuelve_422(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json={
                    "mensaje": "Consulta las políticas",
                    "campo_invalido": "valor",
                },
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 422)

    def test_error_del_grafo_emite_paso_de_error_sse(self):
        async def eventos_con_error(**kwargs):
            yield PasoEvent(
                id="enrutador",
                texto="Clasificando solicitud",
                estado=EstadoPaso.EN_CURSO,
            )
            raise RuntimeError("Error interno de prueba")

        with (
            patch.dict(os.environ, {"AUTH_MODE": "dev"}),
            patch("backend.api.chat_stream.FlujoChat") as flujo_cls,
        ):
            flujo_cls.return_value.astream_chat.side_effect = (
                eventos_con_error
            )

            response = self.client.post(
                self.url,
                json=self.payload,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: paso", response.text)
        self.assertIn("No se pudo completar la consulta", response.text)
        self.assertIn('"estado":"error"', response.text)
        self.assertNotIn("Error interno de prueba", response.text)


if __name__ == "__main__":
    unittest.main()
