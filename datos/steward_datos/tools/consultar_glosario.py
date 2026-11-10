"""Tool consultar_glosario (Mario): definición oficial de un término. Primero coincidencia exacta, luego sinónimos y
al final aproximada. Si no hay un término suficientemente parecido, lo dice en lugar de devolver uno cualquiera."""
import difflib
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contratos import ConsultarGlosarioSalida, TerminoOut
from ..db.models import TerminoGlosario
from ..db.sesion import sesion
from ..reglas.normalizar import sin_acentos

UMBRAL_APROXIMADA = 0.78
_PALABRAS_VACIAS = {"que", "es", "significa", "el", "la", "los", "las", "un", "una", "de", "del", "termino", "definicion", "qué"}


def _norm(s: str) -> str:
    palabras = [w for w in sin_acentos(s.lower()).replace("?", " ").replace("¿", " ").replace("«", " ").replace("»", " ").split()
                if w not in _PALABRAS_VACIAS]
    return " ".join(palabras)


def _out(t: TerminoGlosario) -> TerminoOut:
    return TerminoOut(termino=t.termino, definicion=t.definicion, sinonimos=list(t.sinonimos), dominio=t.dominio, dueno=t.dueno,
                      relacionados=list(t.relacionados), fuente=t.fuente)


def consultar_glosario(termino: str, s: Optional[Session] = None) -> ConsultarGlosarioSalida:
    if s is None:
        with sesion() as s2:
            return consultar_glosario(termino, s2)
    buscado = _norm(termino)
    terminos = s.scalars(select(TerminoGlosario)).all()
    if not buscado:
        return ConsultarGlosarioSalida(encontrado=False, alternativas=[])

    for t in terminos:
        if _norm(t.termino) == buscado:
            return ConsultarGlosarioSalida(encontrado=True, coincidencia="exacta", termino=_out(t), alternativas=list(t.relacionados))
    for t in terminos:
        if any(_norm(x) == buscado for x in t.sinonimos):
            return ConsultarGlosarioSalida(encontrado=True, coincidencia="sinonimo", termino=_out(t), alternativas=list(t.relacionados))

    puntajes = []
    for t in terminos:
        candidatos = [t.termino, *t.sinonimos]
        mejor = max(difflib.SequenceMatcher(None, buscado, _norm(c)).ratio() for c in candidatos)
        if any(_norm(c) in buscado.split() or (len(_norm(c)) > 3 and _norm(c) in buscado) for c in candidatos):
            mejor = max(mejor, 0.85)  # el término aparece dentro de la pregunta
        puntajes.append((mejor, t))
    puntajes.sort(key=lambda x: -x[0])
    mejor, t = puntajes[0]
    alternativas = [x.termino for p, x in puntajes[1:4] if p >= 0.5]
    if mejor >= UMBRAL_APROXIMADA:
        return ConsultarGlosarioSalida(encontrado=True, coincidencia="aproximada", termino=_out(t), alternativas=alternativas)
    return ConsultarGlosarioSalida(encontrado=False, alternativas=[x.termino for p, x in puntajes[:3] if p >= 0.45])
