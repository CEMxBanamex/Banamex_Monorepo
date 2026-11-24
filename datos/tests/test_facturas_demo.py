"""Las facturas de la demo (evaluacion/facturas_demo.yaml) dan el resultado del guion."""
from pathlib import Path

import pytest
import yaml

from steward_datos.config import CARPETA_SINTETICOS
from steward_datos.reglas.motor import validar_factura
from steward_datos.sinteticos import anotaciones, contexto_para, factura_desde_anotacion

DEMO = yaml.safe_load((Path(__file__).resolve().parent.parent / "evaluacion" / "facturas_demo.yaml").read_text(encoding="utf-8"))
REF = {d["archivo"]: d for d in anotaciones("evaluacion")}
ENTIDADES_DEV_ANA = {"GFD960701AB4", "BDM970315QW2", "CPR180301KJ7"}  # db/semillas/generar_negocio.py


@pytest.mark.parametrize("f", DEMO["facturas"], ids=lambda f: f["escenario"])
def test_factura_de_demo_y_su_respaldo(f):
    for archivo in (f["archivo"], f["respaldo"]):
        assert (CARPETA_SINTETICOS / "facturas" / "evaluacion" / archivo).exists()
        d = REF[archivo]
        r = validar_factura(archivo, factura_desde_anotacion(d), contexto_para(d))
        assert r.resultado_sugerido == f["resultado"], archivo
        assert sorted({h.regla_id for h in r.hallazgos}) == f["reglas"], archivo


@pytest.mark.parametrize("f", DEMO["facturas"], ids=lambda f: f["escenario"])
def test_la_factura_principal_es_de_una_entidad_de_dev_ana(f):
    assert REF[f["archivo"]]["verdad"]["campos"]["receptor_rfc"] in ENTIDADES_DEV_ANA


def test_cubre_los_cuatro_escenarios():
    assert {f["escenario"] for f in DEMO["facturas"]} == {"correcta", "total que no cuadra", "campo faltante", "dato de baja confianza"}
