from datetime import date
from decimal import Decimal

import pytest

from steward_datos.reglas import normalizar as n


@pytest.mark.parametrize("texto,esperado", [
    ("12,000.00", "12000.00"), ("$ 1,600.00", "1600.00"), ("10 800,00", "10800.00"), ("1.234.567,89", "1234567.89"),
    ("MXN 1600", "1600.00"), ("-1,250.5", "-1250.50"), ("384,14", "384.14"),
])
def test_monto(texto, esperado):
    assert n.monto(texto) == Decimal(esperado)


@pytest.mark.parametrize("texto", [None, "", "  ", "N/A", "sin total"])
def test_monto_invalido(texto):
    assert n.monto(texto) is None


@pytest.mark.parametrize("texto,esperado", [
    ("12/03/2026", date(2026, 3, 12)), ("2026-08-12", date(2026, 8, 12)), ("12 de agosto de 2026", date(2026, 8, 12)),
    ("3 sept 2026", date(2026, 9, 3)), ("31/02/2026", None), ("ayer", None),
])
def test_fecha(texto, esperado):
    assert n.fecha(texto) == esperado


@pytest.mark.parametrize("rfc,valido", [
    ("PDE200115AB3", True), ("GOMA850315HX1", True), ("xaxx010101000", True), ("ÑAB200229XY1", True),
    ("PDE-200115-AB3", True), ("PDE230231AB3", False), ("PDE20011AB3", False), ("12345678901", False), ("RFC-PENDIENTE", False),
])
def test_rfc(rfc, valido):
    assert n.rfc_valido(rfc) is valido


def test_tasa():
    assert n.tasa("IVA 16 %") == Decimal("0.16")
    assert n.tasa("0.08") == Decimal("0.08")
    assert n.tasa("IVA 0 %") == Decimal("0")
