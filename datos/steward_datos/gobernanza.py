"""Lectura y carga del contenido de gobernanza: catálogo de datos, glosario, reglas de calidad y métricas."""
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from .config import RAIZ_DATOS
from .db.models import CatalogoColumna, CatalogoTabla, Metrica, ReglaCalidad, ResultadoCalidad, TerminoGlosario

CARPETA_GOBERNANZA = RAIZ_DATOS / "gobernanza"
ARCHIVO_METRICAS = RAIZ_DATOS / "semantica" / "metricas.yaml"
MX = ZoneInfo("America/Mexico_City")


def _yaml(ruta: Path) -> dict:
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


@lru_cache
def catalogo_datos() -> dict:
    return _yaml(CARPETA_GOBERNANZA / "catalogo_datos.yaml")


@lru_cache
def glosario() -> dict:
    return _yaml(CARPETA_GOBERNANZA / "glosario.yaml")


@lru_cache
def reglas_calidad() -> list[dict]:
    return _yaml(CARPETA_GOBERNANZA / "calidad.yaml")["reglas"]


@lru_cache
def metricas() -> dict:
    return _yaml(ARCHIVO_METRICAS)


def cargar_catalogo(s: Session) -> int:
    cat = catalogo_datos()
    s.execute(delete(CatalogoColumna))
    s.execute(delete(CatalogoTabla))
    for t in cat["tablas"]:
        dom = cat["dominios"][t["dominio"]]
        tabla = CatalogoTabla(tabla=t["tabla"], nombre_negocio=t["nombre_negocio"], descripcion=t["descripcion"],
                              dominio=t["dominio"], data_owner=dom["data_owner"], data_steward=dom["data_steward"],
                              sensibilidad=t["sensibilidad"], origen=t["origen"], consultable=t.get("consultable", False),
                              relacionadas=t.get("relacionadas", []))
        for i, c in enumerate(t.get("columnas", [])):
            tabla.columnas.append(CatalogoColumna(
                columna=c["columna"], orden=i, tipo=c["tipo"], descripcion=c["descripcion"], sensibilidad=c["sensibilidad"],
                enmascarada=c.get("enmascarada", False), ejemplos=[str(e) for e in c.get("ejemplos", [])] or None,
                termino_glosario=c.get("termino_glosario")))
        s.add(tabla)
    s.flush()
    return len(cat["tablas"])


def cargar_glosario(s: Session) -> int:
    g = glosario()
    s.execute(delete(TerminoGlosario))
    for t in g["terminos"]:
        s.add(TerminoGlosario(termino=t["termino"], definicion=t["definicion"], sinonimos=t.get("sinonimos", []),
                              dominio=t["dominio"], dueno=t["dueno"], relacionados=t.get("relacionados", []),
                              fuente=t.get("fuente"), actualizado_en=g["actualizado_en"]))
    s.flush()
    return len(g["terminos"])


def cargar_metricas(s: Session) -> int:
    m = metricas()
    s.execute(delete(Metrica))
    for nombre, d in m["metricas"].items():
        s.add(Metrica(nombre=nombre, etiqueta=d["etiqueta"], definicion=d["definicion"], unidad=d["unidad"], vista=d["vista"],
                      dimensiones=list(d["dimensiones"]), dueno=m["dueno"], version=str(m["version"])))
    s.flush()
    return len(m["metricas"])


def cargar_calidad(s: Session, *, fecha_corte: date = date(2026, 11, 2), semanas_historial: int = 5) -> int:
    """Registra las reglas y sus resultados: el último se mide sobre los datos actuales; los anteriores se
    simulan alrededor de ese valor (el piloto no tiene historia real de ejecuciones)."""
    s.execute(delete(ResultadoCalidad))
    s.execute(delete(ReglaCalidad))
    rnd = random.Random(2026)
    for r in reglas_calidad():
        regla = ReglaCalidad(id=r["id"], tabla=r["tabla"], columna=r.get("columna"), dimension=r["dimension"],
                             descripcion=r["descripcion"], umbral=Decimal(str(r["umbral"])), sql_medicion=r["sql_medicion"].strip(),
                             politica_id=r.get("politica_id"))
        s.add(regla)
        cumple, total = s.execute(text(r["sql_medicion"])).one()
        actual = Decimal(100) if not total else (Decimal(100) * cumple / total).quantize(Decimal("0.01"))
        for semana in range(semanas_historial, -1, -1):
            cuando = datetime.combine(fecha_corte - timedelta(weeks=semana), datetime.min.time(), MX).replace(hour=6)
            if semana == 0:
                pct, ev, ok = actual, total, cumple
            else:
                pct = max(Decimal(0), min(Decimal(100), actual + Decimal(str(round(rnd.uniform(-1.2, 0.8), 2)))))
                ev = max(1, int(total * (1 - 0.02 * semana)))
                ok = int(ev * pct / 100)
            regla.resultados.append(ResultadoCalidad(ejecutado_en=cuando, registros_evaluados=ev, registros_cumplen=ok,
                                                     porcentaje=pct, cumple_umbral=pct >= regla.umbral))
    s.flush()
    return len(reglas_calidad())
