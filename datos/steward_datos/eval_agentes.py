"""Evaluación de los agentes del chat contra conjuntos de preguntas con fuente esperada.

Dos niveles:
- revisar_fuente: sin LLM. Comprueba que la fuente esperada exista en la base y diga lo que la respuesta debe contener.
  Si falla, el problema está en los datos o en la pregunta, no en el agente.
- calificar: califica una salida del agente ({"id", "tools": [{"nombre", "argumentos"}], "respuesta"}).
"""
import re
import unicodedata
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

from .gobernanza import catalogo_datos
from .tools.consultar_calidad import consultar_calidad
from .tools.consultar_glosario import consultar_glosario

MARCA_SIN_FUENTE = "no encontre"
MARCA_FUERA_DE_DOMINIO = "esta pregunta no es de gobernanza"


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"\s+%", "%", t).strip()


def cargar_preguntas(ruta: Path) -> list[dict]:
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))["preguntas"]


def _fuentes(p: dict) -> list[dict]:
    f = p.get("fuente")
    return [] if f is None else (f if isinstance(f, list) else [f])


def _texto_politica(s: Session, politica: str, seccion: str) -> Optional[str]:
    filas = s.execute(text("""
        SELECT f.texto FROM politica_fragmentos f
        JOIN politicas p ON p.id = f.politica_id AND p.version = f.politica_version
        WHERE f.politica_id = :pid AND p.estado = 'vigente' AND f.seccion LIKE :sec
        ORDER BY f.orden"""), {"pid": politica, "sec": f"{seccion}.%"}).scalars().all()
    return "\n".join(filas) or None


def _texto_catalogo(tabla: str, columna: Optional[str]) -> Optional[str]:
    cat = catalogo_datos()
    t = next((x for x in cat["tablas"] if x["tabla"] == tabla), None)
    if t is None:
        return None
    dom = cat["dominios"][t["dominio"]]
    partes = [t["nombre_negocio"], t["descripcion"], t["sensibilidad"], dom["data_owner"], dom["data_steward"], t["origen"]]
    for c in t.get("columnas", []):
        if columna and c["columna"] != columna:
            continue
        partes += [c["columna"], c["descripcion"], c["sensibilidad"], "enmascarada" if c.get("enmascarada") else ""]
    if columna and len(partes) == 6:
        return None
    return "\n".join(partes)


def revisar_fuente(s: Session, p: dict) -> tuple[bool, str]:
    """(ok, motivo). Sin fuente declarada (fuera de dominio) siempre es ok."""
    textos = []
    for f in _fuentes(p):
        if "politica" in f:
            t = _texto_politica(s, f["politica"], f["seccion"])
            if t is None:
                return False, f"No hay fragmentos vigentes de {f['politica']} §{f['seccion']}"
            textos.append(t)
        elif "glosario" in f:
            r = consultar_glosario(f.get("busqueda", f["glosario"]))
            if not r.encontrado or r.termino.termino != f["glosario"]:
                return False, f"El glosario no resuelve '{f.get('busqueda', f['glosario'])}' a '{f['glosario']}'"
            t = r.termino
            textos.append("\n".join([t.definicion, t.dueno, *t.sinonimos]))
        elif "glosario_inexistente" in f:
            if consultar_glosario(f["glosario_inexistente"]).encontrado:
                return False, f"'{f['glosario_inexistente']}' sí está en el glosario"
        elif "catalogo" in f:
            t = _texto_catalogo(f["catalogo"], f.get("columna"))
            if t is None:
                return False, f"No está {f['catalogo']}{'.' + f['columna'] if f.get('columna') else ''} en el catálogo"
            textos.append(t)
        elif "calidad" in f:
            r = consultar_calidad(f["calidad"])
            incumplen = sorted(x.regla_id for x in r.reglas if not x.cumple_umbral)
            if incumplen != sorted(f["incumplen"]):
                return False, f"En {f['calidad']} incumplen {incumplen}, se esperaba {sorted(f['incumplen'])}"
            textos.append("\n".join(f"{x.regla_id} {x.descripcion} {x.porcentaje}% {x.umbral}%" for x in r.reglas))
        else:
            return False, f"Fuente desconocida: {f}"
    junto = normalizar("\n".join(textos))
    faltan = [d for d in p.get("debe_contener", []) if normalizar(str(d)) not in junto]
    if faltan:
        return False, f"La fuente no contiene: {faltan}"
    return True, ""


def _linea_fuentes(respuesta: str) -> Optional[str]:
    for linea in reversed(respuesta.strip().splitlines()):
        if normalizar(linea).startswith("fuentes:"):
            return normalizar(linea)
    return None


def _citado(cita: str, respuesta_n: str, fuentes_n: Optional[str]) -> bool:
    ident = normalizar(cita.split(":", 1)[1] if ":" in cita else cita)
    return ident in (fuentes_n if fuentes_n is not None else respuesta_n)


def calificar(p: dict, salida: dict) -> dict:
    """Devuelve las comprobaciones que aplican a la pregunta (True/False) y si pasó todas."""
    resp = salida.get("respuesta", "")
    resp_n = normalizar(resp)
    llamadas = {t["nombre"] for t in salida.get("tools", [])}
    c: dict[str, bool] = {}
    comp = p.get("comportamiento")
    if comp == "fuera_de_dominio":
        c["comportamiento"] = resp_n.startswith(MARCA_FUERA_DE_DOMINIO)
    elif comp == "sin_fuente":
        c["comportamiento"] = resp_n.startswith(MARCA_SIN_FUENTE)
    if p.get("tools"):
        c["tool"] = bool(llamadas & set(p["tools"]))
    if p.get("cita"):
        fuentes_n = _linea_fuentes(resp)
        citas = [_citado(x, resp_n, fuentes_n) for x in p["cita"]]
        c["cita"] = all(citas) if p.get("cita_todas") else any(citas)
    if p.get("debe_contener"):
        c["contenido"] = all(normalizar(str(d)) in resp_n for d in p["debe_contener"])
    if p.get("no_debe_regex"):
        c["sin_fuga"] = re.search(p["no_debe_regex"], resp) is None
    return {"id": p["id"], "categoria": p["categoria"], "checks": c, "ok": all(c.values())}


def resumen(resultados: list[dict]) -> dict:
    por_cat: dict[str, list[int]] = {}
    for r in resultados:
        a = por_cat.setdefault(r["categoria"], [0, 0])
        a[0] += r["ok"]
        a[1] += 1
    total = sum(r["ok"] for r in resultados)
    return {"aciertos": total, "total": len(resultados), "por_categoria": por_cat}


def calificar_validador(esperado: dict, salida: dict, cat) -> dict:
    """esperado: {"resultado", "reglas"} de la verdad de referencia. cat: catálogo de reglas."""
    llamadas = [t["nombre"] for t in salida.get("tools", [])]
    hallazgos = salida.get("hallazgos", [])
    citas_ok = all(
        h.get("regla_id") in cat.reglas
        and (h.get("politica_id"), h.get("politica_version"), h.get("politica_seccion"))
        == (cat[h["regla_id"]].politica_id, cat[h["regla_id"]].politica_version, cat[h["regla_id"]].seccion)
        for h in hallazgos)
    c = {
        "tool": llamadas.count("validar_reglas") == 1,
        "resultado": salida.get("resultado_sugerido") == esperado["resultado"],
        "reglas": sorted({h.get("regla_id") for h in hallazgos}) == sorted(esperado["reglas"]),
        "citas": citas_ok,
    }
    falso_aceptado = salida.get("resultado_sugerido") == "aceptado" and esperado["resultado"] != "aceptado"
    return {"checks": c, "ok": all(c.values()), "falso_aceptado": falso_aceptado}
