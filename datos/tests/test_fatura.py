"""Conversión de FATURA: la verdad guarda el valor sin la etiqueta impresa."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fatura_piloto as fp  # noqa: E402

from steward_datos.reglas import normalizar as n


@pytest.mark.parametrize("campo, impreso, valor", [
    ("folio", "Invoice number 2514-256", "2514-256"),
    ("folio", "INVOICE ID INV/86-20/955", "INV/86-20/955"),
    ("folio", "INVOICE # INV4523", "INV4523"),
    ("fecha", "Invoice Date: 26-Jul-2009", "26-Jul-2009"),
    ("fecha_vencimiento", "Due Date : 30-Aug-2013", "30-Aug-2013"),
    ("total", "TOTAL : 1,319.73 $", "1,319.73"),
    ("impuestos", "TAX:VAT (4.17%):  12.21 EUR", "12.21"),
    ("descuento", "DISCOUNT(2.75%): (-)  12.05", "12.05"),
    ("receptor_nombre", "Bill to:Jay Pierce\n8985 Harris Plain", "Jay Pierce"),
    ("receptor_nombre", "BILL_TO: Dr. Erica Parker PhD\nCalle 1", "Dr. Erica Parker PhD"),
    ("emisor_nombre", "Mclean-Cochran", "Mclean-Cochran"),
    ("total", "", None),
])
def test_limpiar_quita_la_etiqueta(campo, impreso, valor):
    assert fp.limpiar(campo, impreso) == valor


def test_moneda_solo_con_codigo_explicito():
    assert fp.moneda("TOTAL : 447.04 USD") == "USD"
    assert fp.moneda("TOTAL : 107.54 $") is None


@pytest.mark.parametrize("texto, esperado", [
    ("26-Jul-2009", date(2009, 7, 26)),
    ("Feb 14, 2021", date(2021, 2, 14)),
    ("12 de marzo de 2026", date(2026, 3, 12)),
    ("31-Feb-2020", None),
])
def test_fecha_en_ingles_y_espanol(texto, esperado):
    assert n.fecha(texto) == esperado


def test_convertir_guarda_valor_limpio_y_texto_impreso(tmp_path):
    ann = tmp_path / "Template1_Instance1.json"
    ann.write_text('{"DATE": {"text": "Invoice Date: 26-Jul-2009", "bbox": [1, 2, 3, 4]}, '
                   '"TOTAL": {"text": "TOTAL : 447.04 USD", "bbox": [1, 2, 3, 4]}}', encoding="utf-8")
    d = fp.convertir(tmp_path / "Template1_Instance1.jpg", ann)
    assert d["verdad"]["campos"] == {"fecha": "26-Jul-2009", "total": "447.04", "moneda": "USD"}
    assert d["verdad"]["texto_impreso"]["fecha"] == "Invoice Date: 26-Jul-2009"
