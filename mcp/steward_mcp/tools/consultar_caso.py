"""Registro de consultar_caso con contexto fijado por el servidor."""
from functools import partial

from anyio import to_thread
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from steward_datos.contratos import CasoOut
from steward_datos.tools.consultas_chat_seguras import CasoNoDisponible, consultar_caso as consultar


class EntradaCaso(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    caso_id: str = Field(min_length=1, max_length=100)


def registrar(servidor, usuario):
    @servidor.tool()
    async def consultar_caso(entrada: EntradaCaso, ctx: Context) -> CasoOut:
        """Consulta datos y evidencias de un caso permitido. Solo lectura; no cambia decisiones."""
        await ctx.report_progress(0, 1, "Consultando caso")
        try:
            resultado = await to_thread.run_sync(partial(consultar, entrada.caso_id, usuario=usuario))
        except CasoNoDisponible as error:
            raise ToolError(str(error)) from error
        except (PermissionError, ValueError) as error:
            raise ToolError("CONTEXTO_INVALIDO: no se puede autorizar la consulta") from error
        except SQLAlchemyError as error:
            raise ToolError("CONSULTA_NO_DISPONIBLE: no se pudo consultar la base") from error
        await ctx.report_progress(1, 1, "Caso consultado")
        return resultado
