"""Servidor MCP de desarrollo. Ejecutar desde la raíz, con mcp/ en PYTHONPATH y steward_datos instalado (pip install -e datos): python -m steward_mcp.servidor."""
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from steward_datos.contratos import ContextoUsuario
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
    servidor = crear_servidor(usuario)
    # Por omisión stdio (pruebas y cliente como subproceso). En contenedor, MCP_TRANSPORT=streamable-http
    # expone http://<host>:MCP_PORT/mcp solo dentro de la red de Docker; MCP_ALLOWED_HOSTS evita el DNS rebinding.
    transporte = os.getenv("MCP_TRANSPORT", "stdio")
    if transporte == "streamable-http":
        servidor.settings.host = os.getenv("MCP_HOST", "0.0.0.0")
        servidor.settings.port = int(os.getenv("MCP_PORT", "8001"))
        servidor.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=os.getenv("MCP_ALLOWED_HOSTS", "mcp:*,localhost:*,127.0.0.1:*").split(","),
        )
    servidor.run(transport=transporte)


if __name__ == "__main__":
    main()
