"""Contexto del usuario para las vistas consultables (seguridad por fila).

El rol y el usuario vienen del JWT (o de X-Usuario / X-Rol en AUTH_MODE=dev), nunca del texto de la pregunta.
El servidor MCP fija el contexto de cada petición con `usuario_actual.set(...)`; las tools lo leen de aquí.
"""
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


def fijar_en_bd(s: Session, usuario: ContextoUsuario) -> None:
    """SET LOCAL de app.rol y app.usuario: dura solo la transacción actual, así que no se filtra a otra petición del pool."""
    s.execute(text("SELECT set_config('app.rol', :rol, true), set_config('app.usuario', :usuario, true)"),
              {"rol": usuario.rol, "usuario": usuario.usuario_id})
