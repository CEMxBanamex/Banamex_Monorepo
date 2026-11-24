import json
import unittest

from fastapi.testclient import TestClient

from backend.api.main import app
from contratos.eventos_sse import PasoEvent, RespuestaEvent


class TestChatProvisional(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_consulta_con_caso(self):
        respuesta = self.client.post(
            "/api/chat/consulta",
            json={
                "mensaje": "¿Qué información tiene este caso?",
                "caso_id": "F-1042",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        RespuestaEvent.model_validate(datos)
        self.assertEqual(datos['tipo'], 'informacion_general')
        self.assertEqual(datos['fuentes'], [])
        self.assertEqual(datos["caso_id"], "F-1042")
        self.assertIs(datos["simulado"], True)
        self.assertTrue(datos["respuesta"].strip())

    def test_consulta_sin_caso(self):
        respuesta = self.client.post(
            "/api/chat/consulta",
            json={"mensaje": "Hola"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.json()["caso_id"])

    def test_entradas_invalidas_en_ambas_rutas(self):
        entradas = [
            {},
            {"mensaje": ""},
            {"mensaje": "   "},
            {"mensaje": "a" * 2001},
            {"mensaje": "Hola", "caso_id": ""},
            {"mensaje": "Hola", "campo_desconocido": True},
        ]

        rutas = [
            "/api/chat/consulta",
            "/api/chat/stream",
        ]

        for ruta in rutas:
            for entrada in entradas:
                with self.subTest(ruta=ruta, entrada=entrada):
                    respuesta = self.client.post(
                        ruta,
                        json=entrada,
                    )
                    self.assertEqual(respuesta.status_code, 422)

    def test_eventos_sse(self):
        respuesta = self.client.post(
            "/api/chat/stream",
            json={
                "mensaje": "Mostrar un ejemplo",
                "caso_id": "F-1042",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(
            respuesta.headers["content-type"].startswith(
                "text/event-stream"
            )
        )
        self.assertEqual(
            respuesta.headers["cache-control"],
            "no-cache",
        )
        self.assertTrue(respuesta.text.endswith("\n\n"))

        eventos = []

        for bloque in respuesta.text.strip().split("\n\n"):
            campos = {}

            for linea in bloque.splitlines():
                clave, valor = linea.split(":", 1)
                campos[clave] = valor.strip()

            eventos.append(
                (campos["event"], json.loads(campos["data"]))
            )

        self.assertEqual(
            [nombre for nombre, _ in eventos],
            ["paso", "paso", "respuesta"],
        )

        primero = eventos[0][1]
        segundo = eventos[1][1]
        final = eventos[2][1]
        PasoEvent.model_validate(primero)
        PasoEvent.model_validate(segundo)
        RespuestaEvent.model_validate(final)
        self.assertEqual(final['tipo'], 'informacion_general')
        self.assertEqual(final['fuentes'], [])

        self.assertEqual(primero["id"], segundo["id"])
        self.assertEqual(primero["estado"], "en_curso")
        self.assertEqual(segundo["estado"], "completado")
        self.assertEqual(final["caso_id"], "F-1042")
        self.assertIs(final["simulado"], True)
        self.assertTrue(final["respuesta"].strip())

    def test_listar_conversaciones(self):
        respuesta = self.client.get(
            "/api/chat/conversaciones"
        )

        self.assertEqual(respuesta.status_code, 200)
        conversaciones = respuesta.json()
        self.assertEqual(len(conversaciones), 1)
        self.assertEqual(
            conversaciones[0]["id"],
            "demo-conversacion-1",
        )
        self.assertIs(
            conversaciones[0]["simulado"],
            True,
        )

    def test_historial_de_conversacion(self):
        respuesta = self.client.get(
            "/api/chat/conversaciones/"
            "demo-conversacion-1/mensajes"
        )

        self.assertEqual(respuesta.status_code, 200)
        historial = respuesta.json()
        self.assertEqual(
            historial["conversacion_id"],
            "demo-conversacion-1",
        )
        self.assertEqual(
            [
                mensaje["rol"]
                for mensaje in historial["mensajes"]
            ],
            ["usuario", "asistente"],
        )
        self.assertIs(historial["simulado"], True)

    def test_historial_inexistente(self):
        respuesta = self.client.get(
            "/api/chat/conversaciones/no-existe/mensajes"
        )

        self.assertEqual(respuesta.status_code, 404)