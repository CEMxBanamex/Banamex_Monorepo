"""Pruebas unitarias para las tools de Yael (registrar_hallazgo y consultar_bitacora)."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from steward_datos.contratos import (
    ConsultarBitacoraEntrada,
    ContextoUsuario,
    HallazgoOut,
    RegistrarHallazgoEntrada,
)
from steward_datos.db.models import EventoBitacora
from steward_datos.tools.consultar_bitacora import consultar_bitacora
from steward_datos.tools.registrar_hallazgo import registrar_hallazgo


def test_consultar_bitacora_filtrado():
    mock_session = MagicMock()
    evento1 = EventoBitacora(
        id=3108,
        fecha=datetime(2026, 10, 26, 11, 42),
        caso_id="F-1042",
        actor_tipo="usuario",
        actor_nombre="Ana López",
        accion="correccion",
        tono="adv",
        detalle="Campo fecha corregido",
        regla_id="R-003",
        regla_version="1.0",
        datos={"antes": "12/03/2026", "despues": "12/08/2026"},
    )
    mock_session.scalars.return_value.all.return_value = [evento1]
    mock_session.execute.return_value.scalar_one.return_value = 3

    entrada = ConsultarBitacoraEntrada(caso_id="F-1042", actor_nombre="Ana%_!", limite=1)
    admin = ContextoUsuario(rol="administrador", usuario_id="admin-prueba")
    resultado = consultar_bitacora(entrada, usuario=admin, s=mock_session)

    assert resultado.total == 3
    assert "%Ana!%!_!!%" in mock_session.scalars.call_args.args[0].compile().params.values()
    assert resultado.eventos[0].id == "EV-3108"
    assert resultado.eventos[0].caso_id == "F-1042"
    assert resultado.eventos[0].actor_nombre == "Ana López"
    assert resultado.eventos[0].regla == "R-003 · v1.0"
    assert resultado.paso == "Revisando la bitácora…"


def test_consultar_bitacora_permisos_analista():
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar_one.return_value = 0
    mock_session.scalars.return_value.all.return_value = []

    usuario_analista = ContextoUsuario(rol="analista", usuario_id="analista-1")
    entrada = ConsultarBitacoraEntrada(caso_id="F-PROHIBIDO", limite=10)

    resultado = consultar_bitacora(entrada, usuario=usuario_analista, s=mock_session)
    assert resultado.total == 0
    assert resultado.eventos == []
    assert "FROM v_casos" in str(mock_session.execute.call_args.args[0])
    assert "FROM v_casos" in str(mock_session.scalars.call_args.args[0])


def test_consultar_bitacora_requiere_usuario():
    with pytest.raises(PermissionError, match="Falta el contexto"):
        consultar_bitacora(ConsultarBitacoraEntrada())


def test_registrar_hallazgo_validaciones():
    mock_session = MagicMock()
    # Simular que el caso no existe
    mock_session.get.side_effect = lambda modelo, id_: None

    h = HallazgoOut(
        regla_id="R-014",
        regla_version="2.1",
        politica_id="P-002",
        efecto="rechazo",
        severidad="error",
        titulo="Total incorrecto",
        texto="Diferencia de 400 MXN",
    )
    entrada = RegistrarHallazgoEntrada(caso_id="F-9999", hallazgo=h)

    with pytest.raises(ValueError, match="El caso F-9999 no existe"):
        registrar_hallazgo(entrada, s=mock_session)
