"""Registro de las tools de Datos en el servidor MCP de Agentes (1.6.1).

    from mcp.server.mcpserver import MCPServer          # mcp 2.x (en 1.x: from mcp.server.fastmcp import FastMCP)
    from steward_datos.mcp_registro import registrar_tools_datos
    mcp = MCPServer("data-steward")
    registrar_tools_datos(mcp)

Las descripciones son las que lee el LLM para decidir cuándo llamar cada tool.

Reparto vigente (vault, decisión del 4 nov.): validar_reglas y consultar_calidad son de Iris; obtener_metrica y
consultar_glosario, de Mario. buscar_politicas, registrar_hallazgo, consultar_caso y buscar_facturas son implementaciones
de referencia que se entregan a sus responsables (Carlos D./R., Yael y Mauricio); usar `solo_propias=True` para registrar
únicamente las de Datos.

obtener_metrica necesita el contexto del usuario: el servidor lo fija con `steward_datos.contexto.usuario_actual.set(...)`
a partir del JWT (o de X-Usuario / X-Rol en AUTH_MODE=dev) antes de atender cada petición.
"""
from typing import Optional, Union
from .contratos import (
    ConsultarCalidadSalida, ConsultarGlosarioSalida, MetricaNoDisponible, ObtenerMetricaEntrada, ObtenerMetricaSalida,
    BuscarFacturasEntrada, BuscarFacturasSalida, BuscarPoliticasEntrada, BuscarPoliticasSalida, CasoOut,
    RegistrarHallazgoEntrada, RegistrarHallazgoSalida, ResultadoValidacion, ValidarReglasEntrada,
)
from .tools import buscar_politicas as _bp
from .tools import consultar_calidad as _cq
from .tools import consultar_glosario as _cg
from .tools import obtener_metrica as _om
from .tools import consultas_chat as _cc
from .tools import registrar_hallazgo as _rh
from .tools import validar_reglas as _vr


def registrar_tools_datos(mcp, solo_propias: bool = False) -> None:
    @mcp.tool(name="obtener_metrica")
    def obtener_metrica(entrada: ObtenerMetricaEntrada) -> Union[ObtenerMetricaSalida, MetricaNoDisponible]:
        """Calcula una métrica oficial (monto facturado, facturas rechazadas, tasa de rechazo, tiempo de revisión, monto
        pagado, etc.) agrupada por hasta 2 dimensiones y con filtros. Es la primera opción para preguntas con cifras.
        Cita la definición que devuelve. Si responde con metricas_disponibles, la pregunta no encaja: usa buscar_facturas
        o la consulta libre."""
        return _om.obtener_metrica(entrada)

    @mcp.tool(name="consultar_glosario")
    def consultar_glosario(termino: str) -> ConsultarGlosarioSalida:
        """Busca la definición oficial de un término de negocio (p. ej. "factura conciliada", "data owner"). Si
        encontrado es falso, di que el término no está en el glosario; no inventes una definición."""
        return _cg.consultar_glosario(termino)

    @mcp.tool(name="consultar_calidad")
    def consultar_calidad(tabla: Optional[str] = None, dimension: Optional[str] = None) -> ConsultarCalidadSalida:
        """Devuelve las reglas de calidad de una tabla (facturas, proveedores, clientes, ordenes_compra, pagos) con su
        umbral, su último porcentaje de cumplimiento y el anterior. Dimensiones: completitud, unicidad, validez,
        oportunidad, consistencia."""
        return _cq.consultar_calidad(tabla, dimension)

    @mcp.tool(name="validar_reglas")
    def validar_reglas(entrada: ValidarReglasEntrada) -> ResultadoValidacion:
        """Aplica en código las reglas exactas del catálogo (sumas, impuestos, campos obligatorios, formatos, duplicados)
        a una factura extraída (historia 1) o a una tabla de registros (historia 2). Devuelve hallazgos y el resultado
        sugerido. Usa siempre esta tool para cualquier cálculo; no calcules montos tú."""
        return _vr.validar_reglas(entrada)

    if solo_propias:
        return

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
