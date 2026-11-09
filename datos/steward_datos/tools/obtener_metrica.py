"""Tool obtener_metrica (Mario): calcula una métrica de la capa semántica. El SQL lo arma el código, no el modelo.

Las piezas de SQL (vista, expresión, dimensiones, columnas de filtro) vienen solo de semantica/metricas.yaml;
los valores que da el usuario siempre van como parámetros. Lee de vistas consultables con el rol del usuario,
así que la seguridad por fila aplica también a las métricas.
"""
import difflib
from datetime import date
from decimal import Decimal
from typing import Optional, Union

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..contexto import fijar_en_bd, requerir_usuario
from ..contratos import ContextoUsuario, MetricaNoDisponible, ObtenerMetricaEntrada, ObtenerMetricaSalida
from ..db.sesion import sesion
from ..gobernanza import metricas


def catalogo_metricas() -> dict[str, dict]:
    """Resumen para el prompt del analista de datos: nombre -> definición, dimensiones y filtros."""
    return {n: {"etiqueta": d["etiqueta"], "definicion": d["definicion"], "unidad": d["unidad"],
                "dimensiones": list(d["dimensiones"]), "filtros": list(d.get("filtros", {}))}
            for n, d in metricas()["metricas"].items()}


def _no_disponible(motivo: str, nombre: Optional[str] = None) -> MetricaNoDisponible:
    defs = metricas()["metricas"]
    parecida = difflib.get_close_matches(nombre or "", list(defs), n=1, cutoff=0.5) if nombre else []
    return MetricaNoDisponible(motivo=motivo, metricas_disponibles={n: d["definicion"] for n, d in defs.items()},
                               sugerencia=parecida[0] if parecida else None)


def construir_sql(entrada: ObtenerMetricaEntrada) -> Union[tuple[str, dict, dict], MetricaNoDisponible]:
    defs = metricas()["metricas"]
    m = defs.get(entrada.metrica)
    if m is None:
        return _no_disponible(f"No existe la métrica «{entrada.metrica}».", entrada.metrica)
    dims = m["dimensiones"]
    malas = [d for d in entrada.dimensiones if d not in dims]
    if malas:
        return _no_disponible(f"La métrica {entrada.metrica} no se agrupa por {', '.join(malas)}. Dimensiones: {', '.join(dims)}.")
    filtros_def = m.get("filtros", {})
    malos = [f for f in entrada.filtros if f not in filtros_def]
    if malos:
        return _no_disponible(f"La métrica {entrada.metrica} no admite el filtro {', '.join(malos)}. Filtros: {', '.join(filtros_def) or 'ninguno'}.")

    where, params = [], {}
    if m.get("filtro_base"):
        where.append(f"({m['filtro_base']})")
    for i, (nombre, valor) in enumerate(entrada.filtros.items()):
        f = filtros_def[nombre]
        p = f"f{i}"
        if f["operador"] == "igual":
            where.append(" OR ".join(f"{c} = :{p}" for c in f["columna"]).join("()"))
            params[p] = valor
        else:
            where.append(" OR ".join(f"{c} ILIKE :{p}" for c in f["columna"]).join("()"))
            params[p] = f"%{valor.strip()}%"
    if entrada.fecha_desde:
        where.append(f"{m['columna_fecha']} >= :fecha_desde")
        params["fecha_desde"] = entrada.fecha_desde
    if entrada.fecha_hasta:
        where.append(f"{m['columna_fecha']} < :fecha_hasta_excl")
        params["fecha_hasta_excl"] = date.fromordinal(entrada.fecha_hasta.toordinal() + 1)

    select = [f"{dims[d]} AS {d}" for d in entrada.dimensiones] + [f"{m['expresion']} AS valor"]
    sql = f"SELECT {', '.join(select)}\nFROM {m['vista']}"
    if where:
        sql += "\nWHERE " + "\n  AND ".join(where)
    if entrada.dimensiones:
        sql += "\nGROUP BY " + ", ".join(str(i + 1) for i in range(len(entrada.dimensiones)))
        orden = {"valor_desc": "valor DESC NULLS LAST", "valor_asc": "valor ASC NULLS LAST",
                 "dimension": ", ".join(str(i + 1) for i in range(len(entrada.dimensiones)))}[entrada.orden]
        sql += f"\nORDER BY {orden}\nLIMIT :limite"
        params["limite"] = entrada.limite + 1  # uno más para saber si se truncó
    return sql, params, m


def _paso(m: dict, entrada: ObtenerMetricaEntrada) -> str:
    texto = m.get("paso", f"Calculando {m['etiqueta'].lower()}")
    if entrada.dimensiones:
        texto += " por " + " y ".join(d.replace("_", " ") for d in entrada.dimensiones)
    return texto + "…"


def _valor(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, date):
        return v.isoformat()
    return v


def obtener_metrica(entrada: ObtenerMetricaEntrada, usuario: Optional[ContextoUsuario] = None,
                    s: Optional[Session] = None) -> Union[ObtenerMetricaSalida, MetricaNoDisponible]:
    usuario = requerir_usuario(usuario)
    armado = construir_sql(entrada)
    if isinstance(armado, MetricaNoDisponible):
        return armado
    sql, params, m = armado
    if s is None:
        with sesion() as s2:
            return obtener_metrica(entrada, usuario, s2)
    fijar_en_bd(s, usuario)
    filas = [{k: _valor(v) for k, v in fila.items()} for fila in s.execute(text(sql), params).mappings()]
    truncado = len(filas) > entrada.limite
    params_vista = {k: _valor(v) for k, v in params.items() if k != "limite"}
    return ObtenerMetricaSalida(metrica=entrada.metrica, etiqueta=m["etiqueta"], definicion=m["definicion"], unidad=m["unidad"],
                                dimensiones=entrada.dimensiones, filas=filas[:entrada.limite], truncado=truncado,
                                sql=sql.replace(":limite", str(entrada.limite)), parametros=params_vista, paso=_paso(m, entrada))
