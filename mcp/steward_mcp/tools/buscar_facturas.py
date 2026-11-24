
"""Registro de buscar_facturas con contexto autenticado por petición."""

from functools import partial

from anyio import to_thread
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from sqlalchemy.exc import SQLAlchemyError

from ..identidad import resolver_usuario
from steward_datos.contratos import BuscarFacturasSalida
from steward_datos.tools.consultas_chat_seguras import (
    FiltrosFacturas,
    buscar_facturas as buscar,
)


def registrar(servidor):
    @servidor.tool()
    async def buscar_facturas(
        entrada: FiltrosFacturas,
        ctx: Context,
    ) -> BuscarFacturasSalida:
        """Busca facturas permitidas por proveedor, fechas, importes, estado o regla. Solo lectura."""

        usuario = resolver_usuario(ctx)

        await ctx.report_progress(0, 1, "Buscando facturas")

        try:
            resultado = await to_thread.run_sync(
                partial(buscar, entrada, usuario=usuario)
            )
        except (PermissionError, ValueError) as error:
            raise ToolError(
                "CONTEXTO_INVALIDO: no se puede autorizar la consulta"
            ) from error
        except SQLAlchemyError as error:
            raise ToolError(
                "CONSULTA_NO_DISPONIBLE: no se pudo consultar la base"
            ) from error

        await ctx.report_progress(1, 1, "Búsqueda terminada")
        return resultado
