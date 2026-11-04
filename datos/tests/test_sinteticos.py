"""Los datos sintéticos y su verdad de referencia son coherentes con el motor de reglas (1.4.2 y 1.4.3)."""
import json
from datetime import date

import pytest

from steward_datos.config import CARPETA_SINTETICOS
from steward_datos.reglas.motor import Contexto, validar_factura, validar_registros
from steward_datos.sinteticos import anotaciones, contexto_para, factura_desde_anotacion, leer_tabla, registros

if not (CARPETA_SINTETICOS / "facturas").exists():
    pytest.skip("Genera los datos con scripts/generar_facturas.py y generar_registros.py", allow_module_level=True)

FACTURAS = list(anotaciones())
REGISTROS = list(registros())


@pytest.mark.parametrize("d", FACTURAS, ids=lambda d: f"{d['grupo']}/{d['archivo']}:{d['escenario']}")
def test_factura_da_el_resultado_esperado(d):
    r = validar_factura(d.get("caso_id") or d["archivo"], factura_desde_anotacion(d), contexto_para(d))
    assert r.resultado_sugerido == d["esperado"]["resultado"]
    assert sorted({h.regla_id for h in r.hallazgos}) == d["esperado"]["reglas"]


@pytest.mark.parametrize("d", REGISTROS, ids=lambda d: d["archivo"])
def test_registros_dan_el_resultado_esperado(d):
    if d["esperado"].get("estado") == "error":
        with pytest.raises(ValueError):
            leer_tabla(d["_ruta_archivo"])
        return
    r = validar_registros(d["archivo"], leer_tabla(d["_ruta_archivo"]), Contexto(fecha_recepcion=date.fromisoformat(d["fecha_recepcion"])))
    assert r.resultado_sugerido == d["esperado"]["resultado"]
    assert sorted({h.regla_id for h in r.hallazgos}) == d["esperado"]["reglas"]
    filas = {}
    for h in r.hallazgos:
        filas.setdefault(h.regla_id, []).extend(h.filas or [])
    for regla, esperadas in d["esperado"]["filas"].items():
        assert sorted(filas[regla]) == esperadas


def test_cobertura_de_escenarios():
    ev = [d for d in FACTURAS if d["grupo"] == "evaluacion"]
    resultados = {d["esperado"]["resultado"] for d in ev}
    assert resultados == {"aceptado", "rechazado", "humana"}
    reglas = {r for d in ev for r in d["esperado"]["reglas"]}
    assert {"R-001", "R-002", "R-003", "R-004", "R-005", "R-010", "R-011", "R-014", "R-015", "R-017", "R-018", "R-021", "R-030", "R-031"} <= reglas
    formatos = {d["formato"] for d in ev}
    assert formatos == {"png", "jpg", "pdf", "pdf_escaneado"}


def test_duplicado_exacto_es_identico_al_original():
    dup = next(d for d in FACTURAS if d["escenario"] == "duplicado_exacto")
    orig = next(d for d in FACTURAS if d.get("caso_id") == dup["copia_de"])
    assert dup["_ruta_archivo"].read_bytes() == orig["_ruta_archivo"].read_bytes()


def test_inyeccion_oculta_esta_en_la_capa_de_texto_del_pdf():
    from pypdf import PdfReader
    d = next(d for d in FACTURAS if d["escenario"] == "inyeccion_oculta")
    texto = PdfReader(d["_ruta_archivo"]).pages[0].extract_text()
    assert "ignore all previous instructions" in texto.lower()


def test_demo_coincide_con_el_mock_del_frontend():
    f1042 = next(d for d in FACTURAS if d.get("caso_id") == "F-1042")
    c = f1042["verdad"]["campos"]
    assert (c["emisor_nombre"], c["subtotal"], c["impuestos"], c["total"]) == ("Proveedor Demo SA", "10,000.00", "1,600.00", "12,000.00")
    assert f1042["confianza_simulada"]["fecha"] == 62 and f1042["lectura_simulada"]["fecha"] == "12/03/2026"
    v0207 = next(d for d in REGISTROS if d.get("caso_id") == "V-0207")
    assert v0207["total_registros"] == 120 and v0207["esperado"]["filas"]["R-101"] == [14, 27, 33, 48, 61, 79, 95, 112]


def test_anotacion_estilo_fatura_tiene_cajas_dentro_de_la_pagina():
    for d in FACTURAS:
        for clase, a in d["anotacion_fatura"].items():
            for x0, y0, x1, y1 in a["bbox"]:
                assert 0 <= x0 < x1 <= 1275 + 40 and 0 <= y0 < y1 <= 1650 + 40, (d["archivo"], clase)


def test_indice_de_referencia():
    idx = json.loads((CARPETA_SINTETICOS / "casos_referencia_facturas.json").read_text(encoding="utf-8"))
    assert len(idx) == len(FACTURAS)
