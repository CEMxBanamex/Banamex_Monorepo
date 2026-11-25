
"""Servidor MCP para desarrollo local y transporte HTTP."""

import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .tools.buscar_facturas import registrar as registrar_facturas
from .tools.consultar_bitacora import registrar as registrar_bitacora
from .tools.consultar_caso import registrar as registrar_casos
from .tools.extraer_campos_factura_demo import registrar
from .tools.gobernanza import registrar as registrar_gobernanza
from .tools.obtener_metrica import registrar as registrar_metrica


def crear_servidor() -> FastMCP:
    """Registra herramientas sin capturar una identidad global."""
    servidor = FastMCP("data-steward")

    registrar(servidor)
    registrar_casos(servidor)
    registrar_bitacora(servidor)
    registrar_facturas(servidor)
    registrar_gobernanza(servidor)
    registrar_metrica(servidor)

    return servidor


def main() -> None:
    transporte = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    auth_mode = os.getenv("AUTH_MODE", "dev").strip().lower()

    if auth_mode not in ("dev", "cognito"):
        raise SystemExit("AUTH_MODE debe ser dev o cognito.")

    if transporte == "stdio":
        if auth_mode != "dev":
            raise SystemExit("El transporte STDIO solo está permitido en desarrollo.")

        rol = os.getenv("MCP_DEV_ROL", "").strip()
        if rol not in ("analista", "administrador"):
            raise SystemExit("Configurar MCP_DEV_ROL como analista o administrador.")

    elif transporte == "streamable-http":
        servidor = crear_servidor()
        servidor.settings.host = os.getenv("MCP_HOST", "0.0.0.0")
        servidor.settings.port = int(os.getenv("MCP_PORT", "8001"))
        servidor.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=os.getenv(
                "MCP_ALLOWED_HOSTS",
                "mcp:*,localhost:*,127.0.0.1:*",
            ).split(","),
        )
        servidor.run(transport=transporte)
        return

    else:
        raise SystemExit(f"Transporte MCP no soportado: {transporte}")

    servidor = crear_servidor()
    servidor.run(transport=transporte)


if __name__ == "__main__":
    main()
