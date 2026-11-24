"""ResoluciÃ³n de identidad por llamada para las herramientas MCP."""

import os

from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from steward_datos.contratos import ContextoUsuario
from steward_datos.credencial_interna import (
    CredencialInternaInvalida,
    verificar_credencial,
)

ROLES_VALIDOS = {"analista", "administrador"}


def _usuario_stdio() -> ContextoUsuario:
    """Identidad local exclusiva para ejecuciÃ³n STDIO en modo desarrollo."""
    if os.getenv("AUTH_MODE", "").strip().lower() != "dev":
        raise ToolError("IDENTIDAD_NO_DISPONIBLE: STDIO solo estÃ¡ permitido en desarrollo.")

    usuario_id = os.getenv("MCP_DEV_USUARIO", "dev-local").strip()
    rol = os.getenv("MCP_DEV_ROL", "").strip()

    if not usuario_id or rol not in ROLES_VALIDOS:
        raise ToolError("IDENTIDAD_NO_DISPONIBLE: configura MCP_DEV_USUARIO y MCP_DEV_ROL.")

    return ContextoUsuario(usuario_id=usuario_id, rol=rol)


def resolver_usuario(ctx: Context) -> ContextoUsuario:
    """Obtiene la identidad autenticada correspondiente a esta llamada MCP."""
    request_context = ctx.request_context
    request = getattr(request_context, "request", None)

    # STDIO no tiene encabezados HTTP. Solo se permite el fallback en desarrollo.
    if request is None:
        return _usuario_stdio()

    # En HTTP nunca se acepta la identidad de desarrollo como fallback.
    authorization = request.headers.get("authorization", "")
    esquema, separador, token = authorization.partition(" ")

    if not separador or esquema.lower() != "bearer" or not token.strip():
        raise ToolError("IDENTIDAD_NO_VALIDA: se requiere una credencial Bearer.")

    try:
        return verificar_credencial(token.strip())
    except CredencialInternaInvalida as error:
        raise ToolError("IDENTIDAD_NO_VALIDA: la credencial interna no es vÃ¡lida.") from error
