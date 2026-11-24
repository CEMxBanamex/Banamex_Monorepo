"""Pruebas de integración: usar exclusivamente una base desechable."""

import os
import unittest
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.api.historial_chat import (
    HistorialNoDisponible, crear_conversacion, guardar_turno, leer_mensajes,
)
from contratos.eventos_sse import PasoEvent, RespuestaEvent
from steward_datos.contratos import ContextoUsuario
from steward_datos.db.models import Base, Mensaje


URL = os.getenv("CHAT_DATABASE_URL_PRUEBAS")


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
