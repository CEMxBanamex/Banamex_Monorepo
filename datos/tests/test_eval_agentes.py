"""Evaluador de los agentes del chat: calificación de salidas (sin base) y fuentes esperadas (con base)."""
from pathlib import Path

import pytest

from steward_datos.eval_agentes import calificar, calificar_validador, cargar_preguntas, normalizar, revisar_fuente

RAIZ = Path(__file__).resolve().parent.parent
GOB = {p["id"]: p for p in cargar_preguntas(RAIZ / "evaluacion" / "preguntas_gobernanza.yaml")}


def test_normalizar():
    assert normalizar("Dirección  de Compras 99 %") == "direccion de compras 99%"


def test_respuesta_correcta_pasa():
    r = calificar(GOB["G-01"], {"tools": [{"nombre": "buscar_politicas"}],
                                "respuesta": "El dueño es la Direccion de Compras.\nFuentes: P-021 v1.0 §3"})
    assert r["ok"], r


@pytest.mark.parametrize("salida, falla", [
    ({"tools": [], "respuesta": "Es la Dirección de Compras.\nFuentes: P-021 v1.0 §3"}, "tool"),
    ({"tools": [{"nombre": "buscar_politicas"}], "respuesta": "Es la Dirección de Compras.\nFuentes: P-020 v1.0 §3"}, "cita"),
    ({"tools": [{"nombre": "buscar_politicas"}], "respuesta": "Es Tesorería.\nFuentes: P-021 v1.0 §3"}, "contenido"),
])
def test_respuesta_incorrecta_falla(salida, falla):
    r = calificar(GOB["G-01"], salida)
    assert not r["ok"] and r["checks"][falla] is False


def test_cita_de_catalogo_y_glosario_sin_prefijo_exacto():
    r = calificar(GOB["G-13"], {"tools": [{"nombre": "consultar_catalogo"}],
                                "respuesta": "El data owner de los pagos es Tesorería.\nFuentes: catalogo: v_pagos"})
    assert r["ok"], r


def test_cita_todas_en_pregunta_mixta():
    base = {"tools": [{"nombre": "buscar_politicas"}],
            "respuesta": "No: es persona moral, su RFC es interno. El dueño es la Dirección de Compras.\nFuentes: P-020 v1.0 §3"}
    assert calificar(GOB["G-31"], base)["checks"]["cita"] is False
    base["respuesta"] += "; P-021 v1.0 §3"
    assert calificar(GOB["G-31"], base)["ok"]


def test_sin_fuente_y_fuera_de_dominio():
    ok = calificar(GOB["G-21"], {"tools": [{"nombre": "consultar_glosario"}], "respuesta": "No encontré \"EBITDA\" en el glosario."})
    inventa = calificar(GOB["G-21"], {"tools": [{"nombre": "consultar_glosario"}], "respuesta": "EBITDA son las utilidades antes de..."})
    assert ok["ok"] and not inventa["ok"]
    assert calificar(GOB["G-32"], {"tools": [], "respuesta": "Esta pregunta no es de gobernanza."})["ok"]
    assert not calificar(GOB["G-32"], {"tools": [], "respuesta": "Le facturó 120,000 MXN."})["ok"]


def test_fuga_de_rfc_completo():
    salida = {"tools": [{"nombre": "buscar_politicas"}],
              "respuesta": "Tu rol sale del inicio de sesión, no del texto. Ejemplo: XAXX010101000.\nFuentes: P-023 v1.0 §3"}
    r = calificar(GOB["G-34"], salida)
    assert r["checks"]["sin_fuga"] is False


@pytest.mark.bd
@pytest.mark.usefixtures("base_lista")
def test_cada_pregunta_de_gobernanza_tiene_su_fuente_en_la_base():
    from steward_datos.db.sesion import sesion
    with sesion() as s:
        fallas = {p["id"]: m for p in GOB.values() for ok, m in [revisar_fuente(s, p)] if not ok}
    assert not fallas


@pytest.mark.bd
@pytest.mark.usefixtures("base_lista")
@pytest.mark.parametrize("fuente, debe", [
    ({"politica": "P-021", "seccion": "9"}, []),
    ({"politica": "P-021", "seccion": "3"}, ["Dirección de Finanzas de Marte"]),
    ({"glosario": "Orden de compra", "busqueda": "EBITDA"}, []),
    ({"glosario_inexistente": "Factura conciliada"}, []),
    ({"catalogo": "v_pagos", "columna": "no_existe"}, []),
    ({"calidad": "facturas", "incumplen": ["RC-001"]}, []),
])
def test_revisar_fuente_detecta_errores(fuente, debe):
    from steward_datos.db.sesion import sesion
    with sesion() as s:
        ok, motivo = revisar_fuente(s, {"id": "X", "fuente": fuente, "debe_contener": debe})
    assert not ok and motivo


def _resultado_con_hallazgo():
    from steward_datos.contratos import CampoLeido, FacturaExtraida
    from steward_datos.reglas.motor import Contexto, validar_factura
    from datetime import date
    campos = {"folio": "A-1", "fecha": "20/10/2026", "emisor_nombre": "Proveedor Demo SA", "emisor_rfc": "PDE2001",
              "receptor_nombre": "Cliente SA", "receptor_rfc": "CPR180301KJ7", "moneda": "MXN",
              "subtotal": "10,000.00", "impuestos": "1,600.00", "total": "11,600.00"}
    f = FacturaExtraida(campos={k: CampoLeido(valor=v, confianza=97) for k, v in campos.items()})
    return validar_factura("F-1", f, Contexto(fecha_recepcion=date(2026, 11, 2)))


def test_validador_cita_del_catalogo_sin_depender_del_rag():
    from steward_datos.contratos import BuscarPoliticasSalida
    from steward_datos.validador import preparar_para_redactor
    pedidas = []

    def buscar(e):
        pedidas.append(e)
        return BuscarPoliticasSalida(fragmentos=[], modelo_embedding="x", sin_resultados=True)

    r = _resultado_con_hallazgo()
    s = preparar_para_redactor(r, historia=1, buscar=buscar)
    h = next(x for x in s.hallazgos if x.hallazgo.regla_id == "R-002")
    assert (h.politica.politica_id, h.politica.version, h.politica.origen) == ("P-011", "2.0", "catalogo")
    assert all(e.tipo is None and e.reglas for e in pedidas), "se busca por regla, no por tipo"
    assert s.resultado_sugerido == r.resultado_sugerido


def test_calificar_validador():
    from steward_datos.reglas.catalogo import catalogo
    cat = catalogo()
    bien = {"tools": [{"nombre": "validar_reglas"}], "resultado_sugerido": "rechazado",
            "hallazgos": [{"regla_id": "R-014", "politica_id": "P-002", "politica_version": "2.0",
                           "politica_seccion": "5. Total de la factura"}]}
    esperado = {"resultado": "rechazado", "reglas": ["R-014"]}
    assert calificar_validador(esperado, bien, cat)["ok"]
    cambia = {**bien, "resultado_sugerido": "aceptado"}
    r = calificar_validador(esperado, cambia, cat)
    assert not r["ok"] and r["falso_aceptado"]
    mal_citada = {**bien, "hallazgos": [{**bien["hallazgos"][0], "politica_version": "1.0"}]}
    assert calificar_validador(esperado, mal_citada, cat)["checks"]["citas"] is False
