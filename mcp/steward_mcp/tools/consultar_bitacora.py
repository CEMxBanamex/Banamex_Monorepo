"""Registro MCP de la bitácora con identidad resuelta por petición."""
from functools import partial

from anyio import to_thread
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from sqlalchemy.exc import SQLAlchemyError
from steward_datos.contratos import ConsultarBitacoraEntrada, ConsultarBitacoraSalida
from steward_datos.tools.consultar_bitacora import consultar_bitacora as consultar

from ..identidad import resolver_usuario


def registrar(servidor):
    @servidor.tool()
    async def consultar_bitacora(entrada: ConsultarBitacoraEntrada, ctx: Context) -> ConsultarBitacoraSalida:
        """Consulta eventos de auditoría de los casos disponibles para el usuario."""
        usuario = resolver_usuario(ctx)
        try:
            return await to_thread.run_sync(partial(consultar, entrada, usuario=usuario))
        except (PermissionError, ValueError) as error:
            raise ToolError("CONTEXTO_INVALIDO: no se puede autorizar la consulta") from error
        except SQLAlchemyError as error:
            raise ToolError("CONSULTA_NO_DISPONIBLE: no se pudo consultar la bitácora") from error
