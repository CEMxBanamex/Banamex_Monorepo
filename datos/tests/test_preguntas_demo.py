"""Las preguntas del chat para la demo (evaluacion/preguntas_demo.yaml) coinciden con sus fuentes."""
import re
from pathlib import Path

import pytest
import yaml

from steward_datos.reglas.catalogo import catalogo

EVAL = Path(__file__).resolve().parent.parent / "evaluacion"
DEMO = yaml.safe_load((EVAL / "preguntas_demo.yaml").read_text(encoding="utf-8"))["preguntas"]
GOB = {p["id"]: p for p in yaml.safe_load((EVAL / "preguntas_gobernanza.yaml").read_text(encoding="utf-8"))["preguntas"]}
POLITICAS = {(m.group(1), m.group(2)) for f in (EVAL.parent / "politicas").glob("P-*.md")
             if (m := re.match(r"(P-\d{3})_.+_v(\d+\.\d+)\.md$", f.name))}


def test_ocho_preguntas_cinco_de_gobernanza_y_tres_de_casos():
    assert len(DEMO) == 8
    assert sum(p["tipo"] == "gobernanza" for p in DEMO) == 5
    assert sum(p["tipo"] == "casos" for p in DEMO) == 3


@pytest.mark.parametrize("p", [p for p in DEMO if p["tipo"] == "gobernanza"], ids=lambda p: p["id"])
def test_gobernanza_sale_de_las_preguntas_de_evaluacion(p):
    g = GOB[p["ref"]]
    assert p["pregunta"] == g["pregunta"]
    for c in p["cita"]:
        m = re.match(r"(P-\d{3}) v(\d+\.\d+) §\d$", c)
        if m:
            assert m.groups() in POLITICAS, c


@pytest.mark.parametrize("p", [p for p in DEMO if p["tipo"] == "casos"], ids=lambda p: p["id"])
def test_casos_citan_reglas_del_catalogo(p):
    cat = catalogo().reglas
    assert all(r in cat for r in p["reglas"])



@pytest.mark.bd
@pytest.mark.usefixtures("base_lista")
@pytest.mark.parametrize("p", [p for p in DEMO if p["tipo"] == "casos"], ids=lambda p: p["id"])
def test_casos_coinciden_con_la_semilla_y_los_ve_dev_ana(p):
    from steward_datos.contratos import ContextoUsuario
    from steward_datos.tools.consultas_chat_seguras import consultar_caso
    c = consultar_caso(p["caso"], ContextoUsuario(usuario_id="dev-ana", rol="analista"))
    assert c.resultado_sugerido == p["resultado_sugerido"]
    hallazgos = [h for h in c.hallazgos if h.titulo != "Prueba"]  # test_bd registra uno de prueba en F-1041
    assert sorted(h.regla_id for h in hallazgos) == p["reglas"]
    if "cifras_r014" in p:
        h = next(h for h in hallazgos if h.regla_id == "R-014")
        assert dict(h.cifras) == {"Esperado": p["cifras_r014"]["esperado"], "Encontrado": p["cifras_r014"]["encontrado"],
                                  "Diferencia": p["cifras_r014"]["diferencia"]}


@pytest.mark.bd
@pytest.mark.usefixtures("base_lista")
def test_calidad_coincide_con_la_semilla():
    from steward_datos.tools.consultar_calidad import consultar_calidad
    p = next(p for p in DEMO if p["id"] == "D-4")
    reglas = {r.regla_id: r for r in consultar_calidad("clientes").reglas}
    for rid, esperado in p["calidad"].items():
        r = reglas[rid]
        assert not r.cumple_umbral
        assert (round(r.porcentaje, 2), r.registros_cumplen, r.registros_evaluados) == (
            esperado["porcentaje"], esperado["cumplen"], esperado["evaluados"])
