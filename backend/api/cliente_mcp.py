
"""Cliente asíncrono para ejecutar herramientas del servidor MCP."""

import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from steward_datos.contratos import ContextoUsuario
from steward_datos.credencial_interna import crear_credencial


class ErrorMCP(Exception):
    """Error al ejecutar una herramienta MCP."""


class ClienteMCP:
    """Centraliza la conexión autenticada con el servidor MCP."""

    def __init__(self, url: str | None = None):
        self.url = url or os.getenv(
            "MCP_URL",
            "http://127.0.0.1:8001/mcp",
        )

    async def ejecutar(
        self,
        herramienta: str,
        argumentos: dict,
        usuario: ContextoUsuario,
    ):
        """Ejecuta una herramienta MCP usando la identidad del usuario."""

        token = crear_credencial(usuario)
        headers = {
            "Authorization": f"Bearer {token}",
        }

        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
            ) as cliente_http:

                async with streamable_http_client(
                    self.url,
                    http_client=cliente_http,
                ) as (lectura, escritura, _):

                    async with ClientSession(
                        lectura,
                        escritura,
                    ) as sesion:

                        await sesion.initialize()

                        resultado = await sesion.call_tool(
                            herramienta,
                            argumentos,
                        )

                        if resultado.isError:
                            mensajes = [
                                contenido.text
                                for contenido in (resultado.content or [])
                                if hasattr(contenido, "text")
                            ]
                            raise ErrorMCP(
                                f"Error en herramienta {herramienta}: "
                                + " | ".join(mensajes)
                            )

                        return resultado

        except ErrorMCP:
            raise
        except Exception as error:
            raise ErrorMCP(
                f"No se pudo conectar o ejecutar {herramienta}: {error}"
            ) from error
