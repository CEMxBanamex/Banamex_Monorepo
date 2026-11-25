"""Registro MCP de la métrica oficial de la capa semántica."""

from functools import partial

from anyio import to_thread
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from sqlalchemy.exc import SQLAlchemyError
from steward_datos.contratos import (
    MetricaNoDisponible,
    ObtenerMetricaEntrada,
    ObtenerMetricaSalida,
)
from steward_datos.tools.obtener_metrica import (
    obtener_metrica as obtener,
)

from ..identidad import resolver_usuario


def registrar(servidor):
    """Registra obtener_metrica con identidad resuelta por petición."""

    @servidor.tool()
    async def obtener_metrica(
        entrada: ObtenerMetricaEntrada,
        ctx: Context,
    ) -> ObtenerMetricaSalida | MetricaNoDisponible:
        """Calcula una métrica oficial y devuelve su definición, resultados y SQL generado."""

        usuario = resolver_usuario(ctx)

        await ctx.report_progress(
            0,
            1,
            f"Calculando métrica: {entrada.metrica}",
        )

        try:
            resultado = await to_thread.run_sync(
                partial(obtener, entrada, usuario=usuario)
            )
        except (PermissionError, ValueError) as error:
            raise ToolError(
                "CONTEXTO_INVALIDO: no se puede autorizar la consulta"
            ) from error
        except SQLAlchemyError as error:
            raise ToolError(
                "CONSULTA_NO_DISPONIBLE: no se pudo calcular la métrica"
            ) from error

        await ctx.report_progress(1, 1, "Cálculo de métrica terminado")
        return resultado
