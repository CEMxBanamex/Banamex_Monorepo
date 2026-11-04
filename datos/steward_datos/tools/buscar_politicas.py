"""Tool buscar_politicas (2.2.2): fragmentos vigentes más parecidos a la consulta, con su versión."""
import os
from datetime import date
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..contratos import BuscarPoliticasEntrada, BuscarPoliticasSalida, FragmentoOut
from ..db.models import FragmentoPolitica, Politica
from .. import config
from ..db.sesion import sesion
from ..rag.embeddings import embeber, nombre_modelo


def umbral_similitud() -> float:
    """Depende del modelo: calibrarlo con scripts/evaluar_rag.py al fijar el modelo de embeddings (0.5.5)."""
    return float(os.getenv("RAG_UMBRAL_SIMILITUD", "0.10" if config.EMBEDDING_PROVEEDOR == "falso" else "0.30"))


def buscar_politicas(entrada: BuscarPoliticasEntrada, s: Optional[Session] = None) -> BuscarPoliticasSalida:
    if s is None:
        with sesion() as s2:
            return buscar_politicas(entrada, s2)
    fecha = entrada.fecha or date.today()
    vector = embeber([entrada.consulta])[0]
    distancia = FragmentoPolitica.embedding.cosine_distance(vector).label("distancia")
    q = (
        select(FragmentoPolitica, Politica, distancia)
        .join(Politica, and_(Politica.id == FragmentoPolitica.politica_id, Politica.version == FragmentoPolitica.politica_version))
        .where(
            FragmentoPolitica.embedding.is_not(None),
            FragmentoPolitica.modelo_embedding == nombre_modelo(),  # mismo modelo al indexar y al consultar
            Politica.estado != "borrador",
            Politica.vigente_desde <= fecha,
            or_(Politica.vigente_hasta.is_(None), Politica.vigente_hasta >= fecha),
        )
        .order_by(distancia)
        .limit(entrada.k)
    )
    if entrada.historia:
        q = q.where(or_(Politica.historia.is_(None), Politica.historia == entrada.historia))
    if entrada.reglas:
        q = q.where(FragmentoPolitica.reglas.overlap(entrada.reglas))
    fragmentos = [
        FragmentoOut(fragmento_id=f.id, politica_id=p.id, politica_nombre=p.nombre, version=p.version,
                     vigente_desde=p.vigente_desde, vigente_hasta=p.vigente_hasta, seccion=f.seccion, texto=f.texto,
                     reglas=f.reglas, similitud=round(1 - float(d), 4))
        for f, p, d in s.execute(q).all()
    ]
    fragmentos = [f for f in fragmentos if f.similitud >= umbral_similitud()]
    return BuscarPoliticasSalida(fragmentos=fragmentos, modelo_embedding=nombre_modelo(), sin_resultados=not fragmentos)
