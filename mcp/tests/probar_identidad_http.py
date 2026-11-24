
import asyncio
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from steward_datos.contratos import ContextoUsuario
from steward_datos.credencial_interna import crear_credencial


URL = "http://127.0.0.1:8001/mcp"
CLAVE = os.environ["CLAVE_IDENTIDAD_MCP"]


async def probar(nombre, token):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(headers=headers) as cliente_http:
        async with streamable_http_client(URL, http_client=cliente_http) as (lectura, escritura, _):
            async with ClientSession(lectura, escritura) as sesion:
                await sesion.initialize()
                resultado = await sesion.call_tool(
                    "extraer_campos_factura_demo",
                    {"entrada": {"documento_id": "DEMO-001"}},
                )

                print(f"\n{nombre}")
                print("Error:", resultado.isError)
                if resultado.content:
                    print("Respuesta:", resultado.content[0].text)


async def main():

    usuario_analista = ContextoUsuario(
        usuario_id="analista-prueba",
        rol="analista",
    )
    token_valido = crear_credencial(usuario_analista)

    await probar("TOKEN VÁLIDO", token_valido)
    await probar("SIN TOKEN", None)
    await probar("TOKEN INVÁLIDO", "token.falso.invalido")


if __name__ == "__main__":
    asyncio.run(main())
