"""Pruebas de S1-40 contra la base desechable y el protocolo MCP real."""
import asyncio
import os
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from steward_datos.contratos import ContextoUsuario
from steward_datos.db.sesion import sesion
from steward_datos.tools.consultas_chat_seguras import (
    CasoNoDisponible, FiltrosFacturas, buscar_facturas, consultar_caso, sesion_autorizada,
)

pytestmark = [pytest.mark.bd, pytest.mark.usefixtures("base_lista")]
ANA = ContextoUsuario(usuario_id="dev-ana", rol="analista")
NADIE = ContextoUsuario(usuario_id="sin-entidades", rol="analista")
ADMIN = ContextoUsuario(usuario_id="admin-pruebas", rol="administrador")


def ids_permitidos(usuario):
    with sesion_autorizada(usuario) as s:
        return set(s.execute(text("SELECT caso_id FROM v_facturas")).scalars())


def test_busqueda_limita_resultados_y_total_por_usuario():
    permitidos = ids_permitidos(ANA)
    assert permitidos
    salida = buscar_facturas(FiltrosFacturas(limite=3), ANA)
    assert salida.total_coincidencias == len(permitidos)
    assert len(salida.facturas) == min(3, len(permitidos))
    assert {f.caso_id for f in salida.facturas} <= permitidos
    assert buscar_facturas(FiltrosFacturas(), NADIE).total_coincidencias == 0


def test_caso_autorizado_y_denegado():
    permitido = sorted(ids_permitidos(ANA))[0]
    assert consultar_caso(permitido.lower(), ANA).id == permitido
    prohibido = sorted(ids_permitidos(ADMIN) - ids_permitidos(ANA))[0]
    mensajes = []
    for identificador in (prohibido, "NO-EXISTE"):
        with pytest.raises(CasoNoDisponible) as error:
            consultar_caso(identificador, ANA)
        mensajes.append(str(error.value))
    assert mensajes[0] == mensajes[1]
    assert consultar_caso(prohibido, ADMIN).id == prohibido


def test_consultas_exigen_contexto():
    with pytest.raises(PermissionError):
        consultar_caso("F-1042")
    with pytest.raises(PermissionError):
        buscar_facturas(FiltrosFacturas())


def test_filtros_y_orden():
    entrada = FiltrosFacturas(total_min=100, total_max=10000, moneda="mxn", orden="total_desc", limite=100)
    salida = buscar_facturas(entrada, ANA)
    assert salida.facturas
    importes = [f.total for f in salida.facturas]
    assert all(100 <= valor <= 10000 for valor in importes)
    assert importes == sorted(importes, reverse=True)
    assert all(f.moneda == "MXN" for f in salida.facturas)
    assert buscar_facturas(FiltrosFacturas(emisor="'; DROP TABLE casos; --"), ANA).total_coincidencias == 0
    assert buscar_facturas(FiltrosFacturas(emisor="%"), ANA).total_coincidencias == 0
    for f in buscar_facturas(FiltrosFacturas(con_regla="R-014"), ADMIN).facturas:
        assert "R-014" in f.reglas_con_hallazgo


@pytest.mark.parametrize("datos", [
    {"limite": 0}, {"limite": 101}, {"total_min": 10, "total_max": 1},
    {"fecha_desde": "2026-12-01", "fecha_hasta": "2026-01-01"},
    {"rol": "administrador"}, {"usuario_id": "dev-ana"}, {"total_min": float("nan")},
])
def test_entradas_invalidas(datos):
    with pytest.raises(ValidationError):
        FiltrosFacturas(**datos)


def test_sesion_solo_lectura():
    from sqlalchemy.exc import DBAPIError
    with pytest.raises(DBAPIError):
        with sesion_autorizada(ANA) as s:
            s.execute(text("UPDATE casos SET estado=estado WHERE false"))
    with sesion() as s:
        rol = s.execute(text("SELECT current_setting('app.rol', true)")).scalar()
        assert rol in (None, "")


async def llamada_mcp():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    raiz = Path(__file__).resolve().parents[2]
    entorno = {**os.environ, "AUTH_MODE": "dev", "MCP_DEV_ROL": "analista",
               "MCP_DEV_USUARIO": "dev-ana", "MCP_TRANSPORT": "stdio",
               "PYTHONPATH": os.pathsep.join([str(raiz / "mcp"), str(raiz / "datos")])}
    params = StdioServerParameters(command=sys.executable, args=["-m", "steward_mcp.servidor"], env=entorno, cwd=raiz)
    async with stdio_client(params) as (lector, escritor):
        async with ClientSession(lector, escritor) as cliente:
            await cliente.initialize()
            nombres = {t.name for t in (await cliente.list_tools()).tools}
            assert {"buscar_facturas", "consultar_caso"} <= nombres
            pasos = []

            async def progreso(valor, total, mensaje):
                pasos.append(valor)

            resultado = await cliente.call_tool("buscar_facturas", {"entrada": {"limite": 2}}, progress_callback=progreso)
            assert not resultado.isError, resultado.content
            assert pasos == [0, 1]
            salida = resultado.structuredContent
            assert salida["total_coincidencias"] > 0 and len(salida["facturas"]) == 2
            caso = salida["facturas"][0]["caso_id"]
            detalle = await cliente.call_tool("consultar_caso", {"entrada": {"caso_id": caso}})
            assert not detalle.isError and detalle.structuredContent["id"] == caso
            for nombre, entrada in (("consultar_caso", {"caso_id": caso, "rol": "administrador"}),
                                    ("buscar_facturas", {"usuario_id": "dev-ana"})):
                assert (await cliente.call_tool(nombre, {"entrada": entrada})).isError
            denegado = await cliente.call_tool("consultar_caso", {"entrada": {"caso_id": "NO-EXISTE"}})
            assert denegado.isError and "CASO_NO_DISPONIBLE" in denegado.content[0].text


def test_mcp_real_con_base_local():
    asyncio.run(llamada_mcp())
