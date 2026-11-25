"""Pruebas de integración: usar exclusivamente una base desechable."""

import os
import unittest
from uuid import uuid4
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from backend.api.main import app

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.api.historial_chat import (
    HistorialNoDisponible, crear_conversacion, guardar_turno, leer_mensajes,
)
from contratos.eventos_sse import PasoEvent, RespuestaEvent
from steward_datos.contratos import ContextoUsuario
from steward_datos.db.models import Base, Mensaje


URL = os.getenv("CHAT_DATABASE_URL_PRUEBAS")


async def eventos_async(elementos):
    for elemento in elementos:
        yield elemento


@unittest.skipUnless(URL, "Requiere CHAT_DATABASE_URL_PRUEBAS de una base desechable")
class TestHistorialPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.motor = create_engine(URL)
        with cls.motor.begin() as c:
            if c.scalar(text("SELECT current_database()")) != "historial_pruebas":
                raise RuntimeError("Usa una base desechable llamada historial_pruebas")
            c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(cls.motor)

    @classmethod
    def tearDownClass(cls):
        cls.motor.dispose()

    def setUp(self):
        self.ana = ContextoUsuario(usuario_id=str(uuid4()), rol="analista")
        self.otro = ContextoUsuario(usuario_id=str(uuid4()), rol="administrador")
        entorno = patch.dict(os.environ, {"AUTH_MODE": "dev", "CHAT_DEV_USUARIO": self.ana.usuario_id})
        entorno.start()
        self.addCleanup(entorno.stop)

        @contextmanager
        def fabrica():
            with Session(self.motor, expire_on_commit=False) as s, s.begin():
                yield s

        for modulo in ("conversaciones", "chat_stream"):
            sustitucion = patch(f"backend.api.{modulo}.sesion", fabrica)
            sustitucion.start()
            self.addCleanup(sustitucion.stop)
        self.cli = TestClient(app)
        self.addCleanup(self.cli.close)

    def crear_por_api(self):
        r = self.cli.post("/api/chat/conversaciones", json={"titulo": "Mi consulta"})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"]

    def test_api_stream_guarda_y_recupera_historial(self):
        identificador = self.crear_por_api()
        r = self.cli.post("/api/chat/stream", json={"mensaje": "Hola", "conversacion_id": identificador})
        self.assertEqual(r.status_code, 200)
        self.assertIn("event: respuesta", r.text)
        ruta = f"/api/chat/conversaciones/{identificador}/mensajes"
        mensajes = self.cli.get(ruta).json()["mensajes"]
        self.assertEqual([m["rol"] for m in mensajes], ["usuario", "asistente"])
        self.assertEqual(len(mensajes[1]["pasos"]), 4)
        with patch("backend.api.chat_stream.FlujoChat") as flujo:
            flujo.return_value.astream_chat.return_value = eventos_async([
                RespuestaEvent(respuesta="Segundo turno", tipo="informacion_general", simulado=True),
            ])
            r = self.cli.post("/api/chat/stream", json={"mensaje": "Continua", "conversacion_id": identificador})
            self.assertIn("event: respuesta", r.text)
            historial = flujo.return_value.astream_chat.call_args.kwargs["historial"]
            self.assertEqual(historial[0], {"role": "user", "content": "Hola"})
            self.assertEqual(len(historial), 2)
        self.assertEqual(len(self.cli.get(ruta).json()["mensajes"]), 4)
        self.assertEqual(self.cli.get("/api/chat/conversaciones").json()[0]["id"], identificador)

    def test_api_aislamiento_entre_usuarios(self):
        identificador = self.crear_por_api()
        with patch.dict(os.environ, {"CHAT_DEV_USUARIO": self.otro.usuario_id}):
            self.assertEqual(self.cli.get("/api/chat/conversaciones").json(), [])
            r = self.cli.get(f"/api/chat/conversaciones/{identificador}/mensajes")
            self.assertEqual(r.status_code, 404)
            r = self.cli.post("/api/chat/stream", json={"mensaje": "Hola", "conversacion_id": identificador})
            self.assertEqual(r.status_code, 404)

    def test_api_historial_paginado(self):
        identificador = self.crear_por_api()
        self.cli.post("/api/chat/stream", json={"mensaje": "Hola", "conversacion_id": identificador})
        ruta = f"/api/chat/conversaciones/{identificador}/mensajes"
        primera = self.cli.get(ruta, params={"limite": 1}).json()
        self.assertTrue(primera["hay_mas"])
        segunda = self.cli.get(ruta, params={"limite": 1, "despues_de": primera["siguiente_despues_de"]}).json()
        self.assertFalse(segunda["hay_mas"])
        self.assertNotEqual(primera["mensajes"][0]["id"], segunda["mensajes"][0]["id"])

    def test_api_bd_no_disponible(self):
        with patch("backend.api.conversaciones.sesion", side_effect=SQLAlchemyError("DETALLE_PRIVADO")):
            r = self.cli.get("/api/chat/conversaciones")
        self.assertEqual(r.status_code, 503)
        self.assertNotIn("DETALLE_PRIVADO", r.text)

    def test_api_rechaza_identidad_en_cuerpo(self):
        r = self.cli.post("/api/chat/conversaciones", json={"titulo": "Privada", "usuario_id": "otro"})
        self.assertEqual(r.status_code, 422)
        with patch.dict(os.environ, {"AUTH_MODE": "prod"}):
            self.assertEqual(self.cli.get("/api/chat/conversaciones").status_code, 503)

    def test_api_conversacion_inexistente(self):
        for identificador in ("no-existe", str(uuid4())):
            self.assertEqual(self.cli.get(f"/api/chat/conversaciones/{identificador}/mensajes").status_code, 404)

    def test_api_error_de_grafo_no_guarda_exito(self):
        identificador = self.crear_por_api()
        with patch("backend.api.chat_stream.FlujoChat") as flujo:
            flujo.return_value.astream_chat.side_effect = RuntimeError("fallo simulado")
            r = self.cli.post("/api/chat/stream", json={"mensaje": "Hola", "conversacion_id": identificador})
        self.assertNotIn("event: respuesta", r.text)
        self.assertEqual(self.cli.get(f"/api/chat/conversaciones/{identificador}/mensajes").json()["mensajes"], [])

    def test_persiste_tras_cerrar_sesion(self):
        with Session(self.motor) as s, s.begin():
            c = crear_conversacion(s, self.ana, "Consulta general")
            identificador = c.id
            guardar_turno(
                s, self.ana, identificador, "Hola",
                [PasoEvent(id="uno", texto="Preparando", estado="completado")],
                RespuestaEvent(respuesta="Ejemplo", tipo="informacion_general",
                               simulado=True, fuentes=["demo"], duracion_ms=5),
            )
        with Session(self.motor) as s:
            mensajes = leer_mensajes(s, self.ana, identificador)
            self.assertEqual([m.rol for m in mensajes], ["usuario", "asistente"])
            self.assertEqual(mensajes[1].contenido, "Ejemplo")
            self.assertEqual(mensajes[1].pasos[0]["estado"], "completado")
            self.assertEqual(mensajes[1].citas, [{"fuente": "demo"}])

    def test_otro_usuario_no_lee_ni_escribe(self):
        with Session(self.motor) as s, s.begin():
            identificador = crear_conversacion(s, self.ana, "Privada").id
        with Session(self.motor) as s:
            with self.assertRaises(HistorialNoDisponible):
                leer_mensajes(s, self.otro, identificador)
            with self.assertRaises(HistorialNoDisponible):
                guardar_turno(s, self.otro, identificador, "Hola", [],
                             RespuestaEvent(respuesta="No", tipo="informacion_general"))

    def test_rollback_no_deja_mensajes(self):
        with Session(self.motor) as s, s.begin():
            identificador = crear_conversacion(s, self.ana, "Atómica").id
        with Session(self.motor) as s:
            guardar_turno(s, self.ana, identificador, "Hola", [],
                         RespuestaEvent(respuesta="Ejemplo", tipo="informacion_general"))
            s.rollback()
        with Session(self.motor) as s:
            self.assertEqual(leer_mensajes(s, self.ana, identificador), [])

    def test_rechaza_respuesta_de_otro_caso(self):
        with Session(self.motor) as s, s.begin():
            identificador = crear_conversacion(s, self.ana, "General").id
            with self.assertRaises(ValueError):
                guardar_turno(s, self.ana, identificador, "Hola", [],
                             RespuestaEvent(respuesta="Ejemplo", tipo="datos", caso_id="F-1042"))
            self.assertEqual(list(s.scalars(select(Mensaje).where(
                Mensaje.conversacion_id == identificador,
            ))), [])

    def test_rechaza_paso_de_error_como_exito(self):
        with Session(self.motor) as s, s.begin():
            identificador = crear_conversacion(s, self.ana, "Errores").id
            with self.assertRaises(ValueError):
                guardar_turno(s, self.ana, identificador, "Hola",
                             [PasoEvent(id="uno", texto="Fallo", estado="error")],
                             RespuestaEvent(respuesta="Ejemplo", tipo="informacion_general"))


if __name__ == "__main__":
    unittest.main()
