
"""Pruebas unitarias de los endpoints del chat agéntico."""

import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.chat import router
from contratos.eventos_sse import EstadoPaso, PasoEvent


app = FastAPI()
app.include_router(router)


class TestChatAPI(unittest.TestCase):
    """Pruebas de autenticación y transmisión SSE del chat."""

    def setUp(self):
        self.client = TestClient(app)
        self.url = "/api/chat/stream"

        self.headers = {
            "X-Usuario": "usuario_demo",
            "X-Rol": "analista",
            "Accept": "text/event-stream",
        }

        self.payload = {
            "pregunta": "Consulta las políticas",
        }

    async def eventos_falsos(self, **kwargs):
        """Genera eventos SSE simulados para las pruebas."""

        yield PasoEvent(
            id="enrutador",
            texto="Clasificando solicitud",
            estado=EstadoPaso.EN_CURSO,
        )

        yield PasoEvent(
            id="respuesta",
            texto="Respuesta de prueba",
            estado=EstadoPaso.COMPLETADO,
        )

    def test_chat_autenticado_transmite_eventos_sse(self):
        """Un usuario autenticado recibe los eventos del chat."""

        with (
            patch.dict(os.environ, {"AUTH_MODE": "dev"}),
            patch("backend.api.chat.flujo_chat") as flujo_mock,
        ):
            flujo_mock.astream_chat.side_effect = self.eventos_falsos

            response = self.client.post(
                self.url,
                json=self.payload,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("Clasificando solicitud", response.text)
        self.assertIn("Respuesta de prueba", response.text)

        flujo_mock.astream_chat.assert_called_once()

    def test_solicitud_sin_autenticacion_devuelve_401(self):
        """Una solicitud sin identidad devuelve 401."""

        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json=self.payload,
                headers={"Accept": "text/event-stream"},
            )

        self.assertEqual(response.status_code, 401)

    def test_rol_invalido_devuelve_403(self):
        """Un rol no permitido devuelve 403 y no ejecuta el grafo."""

        headers = {
            **self.headers,
            "X-Rol": "rol_invalido",
        }

        with (
            patch.dict(os.environ, {"AUTH_MODE": "dev"}),
            patch("backend.api.chat.flujo_chat") as flujo_mock,
        ):
            response = self.client.post(
                self.url,
                json=self.payload,
                headers=headers,
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("rol válido", response.text)
        flujo_mock.astream_chat.assert_not_called()

    def test_auth_mode_no_configurado_devuelve_503(self):
        """La ausencia de AUTH_MODE devuelve 503."""

        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post(
                self.url,
                json=self.payload,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn(
            "AUTH_MODE no está configurado correctamente",
            response.text,
        )

    def test_pregunta_vacia_devuelve_422(self):
        """Una pregunta vacía no es aceptada."""

        payload = {
            "pregunta": "",
        }

        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json=payload,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 422)

    def test_campo_no_permitido_devuelve_422(self):
        """El modelo rechaza campos adicionales."""

        payload = {
            **self.payload,
            "campo_extra": "no permitido",
        }

        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            response = self.client.post(
                self.url,
                json=payload,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 422)

    def test_error_del_grafo_emite_evento_sse(self):
        """Un error del grafo genera un evento SSE de error."""

        async def eventos_con_error(**kwargs):
            yield PasoEvent(
                id="enrutador",
                texto="Clasificando solicitud",
                estado=EstadoPaso.EN_CURSO,
            )

            raise RuntimeError("Error interno de prueba")

        with (
            patch.dict(os.environ, {"AUTH_MODE": "dev"}),
            patch("backend.api.chat.flujo_chat") as flujo_mock,
        ):
            flujo_mock.astream_chat.side_effect = eventos_con_error

            response = self.client.post(
                self.url,
                json=self.payload,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Clasificando solicitud", response.text)
        self.assertIn("event: error", response.text)
        self.assertIn(
            "Ocurrió un error al procesar la solicitud.",
            response.text,
        )


if __name__ == "__main__":
    unittest.main()
