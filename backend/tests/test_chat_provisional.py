import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app
from contratos.eventos_sse import PasoEvent, RespuestaEvent


def leer_eventos(texto):
    eventos = []

    for bloque in texto.strip().split("\n\n"):
        campos = {}

        for linea in bloque.splitlines():
            clave, valor = linea.split(":", 1)
            campos[clave] = valor.strip()

        eventos.append(
            (campos["event"], json.loads(campos["data"]))
        )

    return eventos


async def eventos_async(elementos):
    for elemento in elementos:
        yield elemento


class TestChatProvisional(unittest.TestCase):
    def setUp(self):
        entorno = patch.dict(
            os.environ,
            {
                "AUTH_MODE": "dev",
                "CHAT_DEV_USUARIO": "dev-ana",
            },
        )
        entorno.start()
        self.addCleanup(entorno.stop)

        self.client = TestClient(app, headers={"X-Usuario": "dev-ana", "X-Rol": "analista"})
        self.addCleanup(self.client.close)

    def test_consulta_provisional_con_caso(self):
        respuesta = self.client.post(
            "/api/chat/consulta",
            json={"mensaje": "Hola", "caso_id": "F-1042"},
        )

        self.assertEqual(respuesta.status_code, 200)
        modelo = RespuestaEvent.model_validate(respuesta.json())
        self.assertEqual(modelo.caso_id, "F-1042")
        self.assertTrue(modelo.simulado)

    def test_consulta_provisional_sin_caso(self):
        respuesta = self.client.post(
            "/api/chat/consulta",
            json={"mensaje": "Hola"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.json()["caso_id"])

    def test_entradas_invalidas(self):
        entradas = [
            {},
            {"mensaje": ""},
            {"mensaje": "   "},
            {"mensaje": "a" * 2001},
            {"mensaje": "Hola", "caso_id": ""},
            {"mensaje": "Hola", "usuario_id": "otra-persona"},
            {"mensaje": "Hola", "rol": "administrador"},
        ]

        for ruta in ("/api/chat/consulta", "/api/chat/stream"):
            for entrada in entradas:
                with self.subTest(ruta=ruta, entrada=entrada):
                    respuesta = self.client.post(ruta, json=entrada)
                    self.assertEqual(respuesta.status_code, 422)

    def test_stream_ejecuta_el_grafo_y_respeta_el_contrato(self):
        respuesta = self.client.post(
            "/api/chat/stream",
            json={"mensaje": "Hola", "caso_id": "F-1042"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            "text/event-stream",
            respuesta.headers["content-type"],
        )
        self.assertEqual(
            respuesta.headers["cache-control"],
            "no-cache",
        )
        self.assertTrue(respuesta.text.endswith("\n\n"))

        eventos = leer_eventos(respuesta.text)

        self.assertEqual(
            [nombre for nombre, _ in eventos],
            ["paso", "paso", "paso", "paso", "respuesta"],
        )

        pasos = [
            PasoEvent.model_validate(datos)
            for nombre, datos in eventos
            if nombre == "paso"
        ]

        self.assertEqual(
            [paso.id for paso in pasos],
            ["enrutador", "enrutador", "ejecutor", "ejecutor"],
        )
        self.assertEqual(
            [paso.estado for paso in pasos],
            ["en_curso", "completado", "en_curso", "completado"],
        )

        final = RespuestaEvent.model_validate(eventos[-1][1])
        self.assertEqual(final.caso_id, "F-1042")
        self.assertTrue(final.simulado)
        self.assertTrue(final.respuesta.strip())

    def test_identidad_procede_del_servidor(self):
        final = RespuestaEvent(
            respuesta="Respuesta de prueba",
            tipo="informacion_general",
            fuentes=[],
            simulado=True,
            caso_id="F-1042",
        )

        with patch(
            "backend.api.chat_stream.FlujoChat"
        ) as clase:
            clase.return_value.astream_chat.return_value = eventos_async([final])

            respuesta = self.client.post(
                "/api/chat/stream",
                json={"mensaje": "Hola", "caso_id": "F-1042"},
                headers={
                    "X-Usuario": "usuario-inyectado",
                    "X-Rol": "administrador",
                },
            )

            self.assertEqual(respuesta.status_code, 200)
            clase.return_value.astream_chat.assert_called_once_with(
                pregunta="Hola",
                usuario_id="usuario-inyectado",
                rol="administrador",
                historial=[],
                caso_id="F-1042",
            )

    def test_fuera_de_dev_no_utiliza_identidad_ficticia(self):
        with patch.dict(os.environ, {"AUTH_MODE": "prod"}):
            respuesta = self.client.post(
                "/api/chat/stream",
                json={"mensaje": "Hola"},
            )

        self.assertEqual(respuesta.status_code, 503)

    def test_error_interno_no_expone_detalles(self):
        with patch(
            "backend.api.chat_stream.FlujoChat"
        ) as clase:
            clase.return_value.astream_chat.side_effect = RuntimeError(
                "DETALLE_INTERNO_PRIVADO"
            )

            respuesta = self.client.post(
                "/api/chat/stream",
                json={"mensaje": "Hola"},
            )

        eventos = leer_eventos(respuesta.text)
        self.assertEqual(eventos[-1][0], "paso")
        self.assertEqual(eventos[-1][1]["estado"], "error")
        self.assertNotIn("DETALLE_INTERNO_PRIVADO", respuesta.text)
        self.assertNotIn("respuesta", [nombre for nombre, _ in eventos])

    def test_error_del_grafo_no_se_duplica(self):
        error = PasoEvent(
            id="ejecutor",
            texto="Error al procesar solicitud",
            estado="error",
        )

        with patch(
            "backend.api.chat_stream.FlujoChat"
        ) as clase:
            clase.return_value.astream_chat.return_value = eventos_async([error])

            respuesta = self.client.post(
                "/api/chat/stream",
                json={"mensaje": "Hola"},
            )

        eventos = leer_eventos(respuesta.text)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0][1]["estado"], "error")

    def test_grafo_sin_respuesta_final_emite_error(self):
        with patch(
            "backend.api.chat_stream.FlujoChat"
        ) as clase:
            clase.return_value.astream_chat.return_value = eventos_async([])

            respuesta = self.client.post(
                "/api/chat/stream",
                json={"mensaje": "Hola"},
            )

        eventos = leer_eventos(respuesta.text)
        self.assertEqual(eventos[-1][1]["estado"], "error")

    def test_no_hay_rutas_stream_duplicadas(self):
        rutas = []

        for ruta in app.routes:
            recorrer = getattr(ruta, "effective_route_contexts", None)

            if callable(recorrer):
                for contexto in recorrer():
                    if (
                        contexto.path_format == "/api/chat/stream"
                        and "POST"
                        in getattr(contexto.original_route, "methods", set())
                    ):
                        rutas.append(contexto)

            elif (
                getattr(ruta, "path", None) == "/api/chat/stream"
                and "POST" in getattr(ruta, "methods", set())
            ):
                rutas.append(ruta)

        self.assertEqual(len(rutas), 1)
