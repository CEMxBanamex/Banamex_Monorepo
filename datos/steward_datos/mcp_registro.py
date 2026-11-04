"""Registro de las tools de Datos en el servidor MCP de Agentes (1.6.1).

    from mcp.server.mcpserver import MCPServer          # mcp 2.x (en 1.x: from mcp.server.fastmcp import FastMCP)
    from steward_datos.mcp_registro import registrar_tools_datos
    mcp = MCPServer("data-steward")
    registrar_tools_datos(mcp)

Las descripciones son las que lee el LLM para decidir cuándo llamar cada tool.
"""
from .contratos import (
    BuscarFacturasEntrada, BuscarFacturasSalida, BuscarPoliticasEntrada, BuscarPoliticasSalida, CasoOut,
    RegistrarHallazgoEntrada, RegistrarHallazgoSalida, ResultadoValidacion, ValidarReglasEntrada,
)
from .tools import buscar_politicas as _bp
from .tools import consultas_chat as _cc
from .tools import registrar_hallazgo as _rh
from .tools import validar_reglas as _vr


def registrar_tools_datos(mcp) -> None:
    @mcp.tool(name="validar_reglas")
    def validar_reglas(entrada: ValidarReglasEntrada) -> ResultadoValidacion:
        """Aplica en código las reglas exactas del catálogo (sumas, impuestos, campos obligatorios, formatos, duplicados)
        a una factura extraída (historia 1) o a una tabla de registros (historia 2). Devuelve hallazgos y el resultado
        sugerido. Usa siempre esta tool para cualquier cálculo; no calcules montos tú."""
        return _vr.validar_reglas(entrada)

    @mcp.tool(name="buscar_politicas")
    def buscar_politicas(entrada: BuscarPoliticasEntrada) -> BuscarPoliticasSalida:
        """Busca fragmentos de políticas vigentes relacionados con la consulta. Cita la política, versión y sección
        de cada fragmento que uses. Si sin_resultados es verdadero, no hay política aplicable: pide revisión humana."""
        return _bp.buscar_politicas(entrada)

    @mcp.tool(name="registrar_hallazgo")
    def registrar_hallazgo(entrada: RegistrarHallazgoEntrada) -> RegistrarHallazgoSalida:
        """Guarda un hallazgo del caso y su evento en la bitácora de auditoría."""
        return _rh.registrar_hallazgo(entrada)

    @mcp.tool(name="consultar_caso")
    def consultar_caso(caso_id: str) -> CasoOut:
        """Devuelve el estado, los datos extraídos, los hallazgos y la bitácora de un caso (p. ej. F-1042 o V-0207)."""
        return _cc.consultar_caso(caso_id)

    @mcp.tool(name="buscar_facturas")
    def buscar_facturas(entrada: BuscarFacturasEntrada) -> BuscarFacturasSalida:
        """Busca facturas registradas con filtros (proveedor, folio, fechas, montos, moneda, resultado, regla incumplida).
        Solo lectura."""
        return _cc.buscar_facturas(entrada)
