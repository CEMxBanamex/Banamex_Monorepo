"""Ejemplo con una sola factura ficticia y sin llamadas externas."""
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import BaseModel, ConfigDict

from datos.steward_datos.contratos import CampoLeido, ContextoUsuario, FacturaExtraida


class EntradaDemo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documento_id: str


def registrar(servidor: FastMCP, usuario: ContextoUsuario) -> None:
    @servidor.tool()
    async def extraer_campos_factura_demo(entrada: EntradaDemo, ctx: Context) -> FacturaExtraida:
        """Devuelve la extracción fija de DEMO-001 para probar el flujo local."""
        if usuario.rol != "analista":
            raise ToolError("ROL_NO_AUTORIZADO: la herramienta demo requiere rol analista.")
        if entrada.documento_id != "DEMO-001":
            raise ToolError("DOCUMENTO_NO_ENCONTRADO: el único documento demo es DEMO-001.")

        await ctx.report_progress(0, 1, "Extrayendo campos de la factura de prueba…")
        factura = FacturaExtraida(
            campos={
                "folio": CampoLeido(valor="DEMO-001", etiqueta="Folio"),
                "moneda": CampoLeido(valor="MXN", etiqueta="Moneda"),
                "total": CampoLeido(valor="116.00", etiqueta="Total"),
            },
            texto_completo="Folio DEMO-001\nMoneda MXN\nTotal 116.00",
        )
        await ctx.report_progress(1, 1, "Extracción de prueba lista.")
        return factura
