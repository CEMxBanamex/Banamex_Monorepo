"""Contexto del usuario para las vistas consultables (seguridad por fila).

El rol y el usuario vienen del JWT (o de X-Usuario / X-Rol en AUTH_MODE=dev), nunca del texto de la pregunta.
El servidor MCP fija el contexto de cada petición con `usuario_actual.set(...)`; las tools lo leen de aquí.
"""
import re
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from .contratos import ContextoUsuario

usuario_actual: ContextVar[Optional[ContextoUsuario]] = ContextVar("usuario_actual", default=None)


def requerir_usuario(usuario: Optional[ContextoUsuario] = None) -> ContextoUsuario:
    u = usuario or usuario_actual.get()
    if u is None:
        raise PermissionError("Falta el contexto del usuario (rol y usuario). El servidor MCP debe fijarlo en cada petición.")
    return u


ROLES_VALIDOS = {"analista", "administrador"}
# sub de Cognito (UUID), correo o los usuarios de desarrollo (dev-ana); sin comillas ni dos puntos.
_USUARIO_VALIDO = re.compile(r"[A-Za-z0-9._@+-]{1,128}")


def fijar_en_bd(s: Session, usuario: ContextoUsuario) -> None:
    """SET LOCAL de app.rol y app.usuario: dura solo la transacción actual, así que no se filtra a otra petición del pool.

    Se usa SET LOCAL y no set_config porque el usuario de consultas no tiene permiso de ejecutar set_config
    (migración 0003). SET no acepta parámetros, así que los valores se validan antes de armarlo.
    """
    if usuario.rol not in ROLES_VALIDOS:
        raise ValueError(f"Rol no admitido: {usuario.rol!r}")
    if not _USUARIO_VALIDO.fullmatch(usuario.usuario_id):
        raise ValueError("Identificador de usuario no admitido")
    s.execute(text(f"SET LOCAL app.rol = '{usuario.rol}'"))
    s.execute(text(f"SET LOCAL app.usuario = '{usuario.usuario_id}'"))
