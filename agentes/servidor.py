"""Servidor MCP de desarrollo. Ejecutar desde la raíz: python -m agentes.servidor."""
import os

from mcp.server.fastmcp import FastMCP

from datos.steward_datos.contratos import ContextoUsuario
from .tools.extraer_campos_factura_demo import registrar


def crear_servidor(usuario: ContextoUsuario) -> FastMCP:
    servidor = FastMCP("data-steward-dev")
    registrar(servidor, usuario)
    return servidor


def main() -> None:
    if os.getenv("AUTH_MODE") != "dev":
        raise SystemExit("Este servidor local requiere AUTH_MODE=dev.")
    rol = os.getenv("MCP_DEV_ROL")
    if rol not in ("analista", "administrador"):
        raise SystemExit("Configurar MCP_DEV_ROL como analista o administrador.")
    usuario = ContextoUsuario(usuario_id="dev-local", rol=rol)
    crear_servidor(usuario).run(transport="stdio")


if __name__ == "__main__":
    main()
