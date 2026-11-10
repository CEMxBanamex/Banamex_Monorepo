"""Tool consultar_calidad (Iris): reglas de calidad de una tabla con su último resultado y el anterior.
En el piloto los resultados están precargados; la tool no ejecuta reglas en vivo."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contratos import ConsultarCalidadSalida, ResultadoReglaCalidad
from ..db.models import ReglaCalidad, ResultadoCalidad
from ..db.sesion import sesion
from ..reglas.normalizar import sin_acentos

DIMENSIONES = {"completitud", "unicidad", "validez", "oportunidad", "consistencia"}


def _tabla(nombre: str, conocidas: list[str]) -> Optional[str]:
    """Acepta 'facturas', 'v_facturas', 'tabla de facturas', 'Facturas'."""
    n = sin_acentos(nombre.lower()).replace("tabla de ", "").replace("tabla ", "").strip()
    n = n[2:] if n.startswith("v_") else n
    n = n.replace(" ", "_")
    if n in conocidas:
        return n
    singular = {t.rstrip("s"): t for t in conocidas}
    return singular.get(n.rstrip("s"))


def consultar_calidad(tabla: Optional[str] = None, dimension: Optional[str] = None,
                      s: Optional[Session] = None) -> ConsultarCalidadSalida:
    if s is None:
        with sesion() as s2:
            return consultar_calidad(tabla, dimension, s2)
    conocidas = sorted(set(s.scalars(select(ReglaCalidad.tabla).where(ReglaCalidad.activa.is_(True)))))
    nombre = _tabla(tabla, conocidas) if tabla else None
    if tabla and nombre is None:
        return ConsultarCalidadSalida(tabla=tabla, reglas=[], tablas_con_reglas=conocidas)
    dim = sin_acentos(dimension.lower()) if dimension else None
    if dim and dim not in DIMENSIONES:
        dim = None
    q = select(ReglaCalidad).where(ReglaCalidad.activa.is_(True)).order_by(ReglaCalidad.id)
    if nombre:
        q = q.where(ReglaCalidad.tabla == nombre)
    if dim:
        q = q.where(ReglaCalidad.dimension == dim)
    out = []
    for r in s.scalars(q):
        ultimos = s.scalars(select(ResultadoCalidad).where(ResultadoCalidad.regla_id == r.id)
                            .order_by(ResultadoCalidad.ejecutado_en.desc()).limit(2)).all()
        if not ultimos:
            continue
        u = ultimos[0]
        out.append(ResultadoReglaCalidad(
            regla_id=r.id, tabla=r.tabla, columna=r.columna, dimension=r.dimension, descripcion=r.descripcion,
            umbral=float(r.umbral), porcentaje=float(u.porcentaje), cumple_umbral=u.cumple_umbral,
            registros_evaluados=u.registros_evaluados, registros_cumplen=u.registros_cumplen, ejecutado_en=u.ejecutado_en,
            porcentaje_anterior=float(ultimos[1].porcentaje) if len(ultimos) > 1 else None, politica_id=r.politica_id))
    paso = f"Revisando reglas de calidad de {nombre}…" if nombre else "Revisando reglas de calidad…"
    return ConsultarCalidadSalida(tabla=nombre, reglas=out, tablas_con_reglas=conocidas, paso=paso)
