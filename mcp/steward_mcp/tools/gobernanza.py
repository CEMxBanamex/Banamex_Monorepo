
"""Herramientas MCP de gobernanza con identidad resuelta por llamada."""

from functools import partial

from anyio import to_thread
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from sqlalchemy.exc import SQLAlchemyError
from steward_datos.contratos import (
    BuscarPoliticasEntrada,
    BuscarPoliticasSalida,
    ConsultarCalidadSalida,
    ConsultarGlosarioSalida,
)
from steward_datos.tools.buscar_politicas import (
    buscar_politicas as buscar,
)
from steward_datos.tools.consultar_calidad import (
    consultar_calidad as consultar_resultados,
)
from steward_datos.tools.consultar_glosario import (
    consultar_glosario as consultar_termino,
)

from ..identidad import resolver_usuario


def registrar(servidor):
    """Registra las herramientas de gobernanza en el servidor MCP."""

    @servidor.tool()
    async def buscar_politicas(
        entrada: BuscarPoliticasEntrada,
        ctx: Context,
    ) -> BuscarPoliticasSalida:
        """Busca políticas vigentes y fragmentos relevantes para una consulta.
        Devuelve versión, sección y similitud de cada fragmento."""

        resolver_usuario(ctx)

        await ctx.report_progress(0, 1, "Buscando políticas")

        try:
            resultado = await to_thread.run_sync(
                partial(buscar, entrada)
            )
        except SQLAlchemyError as error:
            raise ToolError(
                "CONSULTA_NO_DISPONIBLE: no se pudieron consultar las políticas."
            ) from error

        await ctx.report_progress(1, 1, "Búsqueda de políticas terminada")
        return resultado

    @servidor.tool()
    async def consultar_glosario(
        termino: str,
        ctx: Context,
    ) -> ConsultarGlosarioSalida:
        """Consulta la definición oficial de un término de negocio."""

        resolver_usuario(ctx)

        await ctx.report_progress(0, 1, "Consultando glosario")

        try:
            resultado = await to_thread.run_sync(
                partial(consultar_termino, termino)
            )
        except SQLAlchemyError as error:
            raise ToolError(
                "CONSULTA_NO_DISPONIBLE: no se pudo consultar el glosario."
            ) from error

        await ctx.report_progress(1, 1, "Consulta del glosario terminada")
        return resultado

    @servidor.tool()
    async def consultar_calidad(
        ctx: Context,
        tabla: str | None = None,
        dimension: str | None = None,
    ) -> ConsultarCalidadSalida:
        """Consulta reglas y resultados de calidad de datos.
        Permite filtrar por tabla y dimensión."""

        resolver_usuario(ctx)

        await ctx.report_progress(0, 1, "Consultando calidad de datos")

        try:
            resultado = await to_thread.run_sync(
                partial(consultar_resultados, tabla, dimension)
            )
        except SQLAlchemyError as error:
            raise ToolError(
                "CONSULTA_NO_DISPONIBLE: no se pudo consultar la calidad."
            ) from error

        await ctx.report_progress(1, 1, "Consulta de calidad terminada")
        return resultado
