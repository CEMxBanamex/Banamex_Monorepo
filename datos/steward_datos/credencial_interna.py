
"""Credenciales internas para transmitir identidad autenticada del backend al MCP."""

import os
import time

import jwt
from jwt import PyJWTError

from .contratos import ContextoUsuario

EMISOR = "data-steward-backend"
AUDIENCIA = "data-steward-mcp"
DURACION_SEGUNDOS = 60
ALGORITMO = "HS256"
ROLES_VALIDOS = {"analista", "administrador"}


class CredencialInternaInvalida(Exception):
    """La credencial interna no es válida o no está configurada."""


def _obtener_secreto() -> str:
    secreto = os.getenv("CLAVE_IDENTIDAD_MCP", "").strip()

    if len(secreto) < 32:
        raise CredencialInternaInvalida(
            "CLAVE_IDENTIDAD_MCP debe contener al menos 32 caracteres."
        )

    return secreto


def crear_credencial(usuario: ContextoUsuario) -> str:
    """Genera una credencial interna de corta duración para una solicitud MCP."""

    if usuario.rol not in ROLES_VALIDOS:
        raise CredencialInternaInvalida("Rol no autorizado.")

    if not usuario.usuario_id or len(usuario.usuario_id) > 128:
        raise CredencialInternaInvalida("Identificador de usuario inválido.")

    ahora = int(time.time())

    claims = {
        "iss": EMISOR,
        "aud": AUDIENCIA,
        "sub": usuario.usuario_id,
        "role": usuario.rol,
        "iat": ahora,
        "exp": ahora + DURACION_SEGUNDOS,
    }

    return jwt.encode(
        claims,
        _obtener_secreto(),
        algorithm=ALGORITMO,
    )


def verificar_credencial(token: str) -> ContextoUsuario:
    """Verifica una credencial interna y recupera la identidad autenticada."""

    if not isinstance(token, str) or not token.strip():
        raise CredencialInternaInvalida("Credencial ausente.")

    try:
        claims = jwt.decode(
            token,
            _obtener_secreto(),
            algorithms=[ALGORITMO],
            issuer=EMISOR,
            audience=AUDIENCIA,
            leeway=5,
            options={
                "require": ["exp", "iat", "iss", "aud", "sub", "role"],
            },
        )
    except (PyJWTError, CredencialInternaInvalida) as error:
        raise CredencialInternaInvalida(
            "No fue posible validar la credencial interna."
        ) from error

    usuario_id = claims.get("sub")
    rol = claims.get("role")

    if (
        not isinstance(usuario_id, str)
        or not usuario_id
        or len(usuario_id) > 128
        or rol not in ROLES_VALIDOS
    ):
        raise CredencialInternaInvalida("Identidad o rol inválido.")

    try:
        return ContextoUsuario(
            usuario_id=usuario_id,
            rol=rol,
        )
    except Exception as error:
        raise CredencialInternaInvalida(
            "No fue posible construir el contexto de usuario."
        ) from error
