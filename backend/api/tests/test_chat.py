"""Pruebas HTTP aisladas del adaptador de chat anterior (contrato pregunta)."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from fastapi import FastAPI
from backend.api.chat import router

app = FastAPI()
app.include_router(router)
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

    def test_chat_autenticado_transmite_eventos_sse(self):
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

        with patch.dict(os.environ, {"AUTH_MODE": "dev"}), patch(
            "backend.api.chat.flujo_chat.astream_chat",
            side_effect=eventos_falsos,
        ):
            response = self.client.post(
                self.url,
                json={"pregunta": "Consulta las políticas"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("data:", response.text)
        self.assertIn("Clasificando solicitud", response.text)
        self.assertIn("Respuesta de prueba", response.text)
        self.assertIn("buscar_politicas", response.text)

    def test_solicitud_sin_autenticacion_devuelve_401(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json={"pregunta": "Consulta las políticas"},
            )

        self.assertEqual(response.status_code, 401)

    def test_rol_invalido_devuelve_403(self):
        headers = {
            "X-Usuario": "usuario_demo",
            "X-Rol": "invitado",
        }

        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json={"pregunta": "Consulta las políticas"},
                headers=headers,
            )

        self.assertEqual(response.status_code, 403)

    def test_pregunta_vacia_devuelve_422(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json={"pregunta": ""},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 422)

    def test_campo_no_permitido_devuelve_422(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json={
                    "pregunta": "Consulta las políticas",
                    "campo_invalido": "valor",
                },
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 422)

    def test_error_del_grafo_emite_evento_sse(self):
        async def eventos_con_error(**kwargs):
            yield PasoEvent(
                id="enrutador",
                texto="Clasificando solicitud",
                estado=EstadoPaso.EN_CURSO,
            )
            raise RuntimeError("Error interno de prueba")

        with patch.dict(os.environ, {"AUTH_MODE": "dev"}), patch(
            "backend.api.chat.flujo_chat.astream_chat",
            side_effect=eventos_con_error,
        ):
            response = self.client.post(
                self.url,
                json={"pregunta": "Consulta las políticas"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: error", response.text)
        self.assertIn("Ocurrió un error al procesar la solicitud.", response.text)
        self.assertNotIn("Error interno de prueba", response.text)


if __name__ == "__main__":
    unittest.main()
