"""Pruebas de extremo a extremo con un cliente MCP y el servidor por stdio."""
import asyncio
import os
import sys
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from datos.steward_datos.contratos import FacturaExtraida

RAIZ = Path(__file__).resolve().parents[2]
TOOL = "extraer_campos_factura_demo"


async def probar_analista():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agentes.servidor"],
        cwd=RAIZ,
        env={**os.environ, "AUTH_MODE": "dev", "MCP_DEV_ROL": "analista"},
    )
    async with stdio_client(params) as (lector, escritor):
        async with ClientSession(lector, escritor) as cliente:
            await cliente.initialize()
            tools = await cliente.list_tools()
            assert [tool.name for tool in tools.tools] == [TOOL]
            pasos = []

            async def registrar_paso(progreso, total, mensaje):
                pasos.append((progreso, total, mensaje))

            ok = await cliente.call_tool(
                TOOL, {"entrada": {"documento_id": "DEMO-001"}}, progress_callback=registrar_paso
            )
            assert not ok.isError, ok.content
            salida = FacturaExtraida.model_validate(ok.structuredContent)
            assert salida.campos["total"].valor == "116.00"
            assert salida.campos["total"].confianza is None
            assert [p[0] for p in pasos] == [0, 1]
            assert all(p[2] for p in pasos)
            error = await cliente.call_tool(TOOL, {"entrada": {"documento_id": "NO-EXISTE"}})
            assert error.isError
            assert "DOCUMENTO_NO_ENCONTRADO" in error.content[0].text


async def probar_rol():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agentes.servidor"],
        cwd=RAIZ,
        env={**os.environ, "AUTH_MODE": "dev", "MCP_DEV_ROL": "administrador"},
    )
    async with stdio_client(params) as (lector, escritor):
        async with ClientSession(lector, escritor) as cliente:
            await cliente.initialize()
            error = await cliente.call_tool(TOOL, {"entrada": {"documento_id": "DEMO-001"}})
            assert error.isError
            assert "ROL_NO_AUTORIZADO" in error.content[0].text
            suplantado = await cliente.call_tool(
                TOOL, {"entrada": {"documento_id": "DEMO-001", "rol": "analista"}}
            )
            assert suplantado.isError
            assert "extra_forbidden" in suplantado.content[0].text


class PruebasMCP(unittest.TestCase):
    def test_herramienta_entrega_contrato_y_pasos(self):
        asyncio.run(probar_analista())

    def test_rol_no_viene_de_la_herramienta(self):
        asyncio.run(probar_rol())
