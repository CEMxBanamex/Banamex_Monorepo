"""Ingesta de políticas al RAG (tarea 2.1.2): metadatos, fragmentos y embeddings en pgvector."""
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import EventoBitacora, FragmentoPolitica, Politica
from .embeddings import embeber, nombre_modelo
from .fragmentar import fragmentar, leer_politica


def ingestar_politica(s: Session, texto_md: str, nombre_archivo: str, *, s3_key: Optional[str] = None,
                      cargada_por: str = "sistema", con_embeddings: bool = True) -> tuple[Politica, str]:
    """Devuelve (politica, accion) con accion en {'nueva', 'actualizada', 'sin_cambios'}."""
    meta, cuerpo = leer_politica(texto_md)
    existente = s.get(Politica, (meta.id, meta.version))
    if existente and existente.sha256 == meta.sha256 and (not con_embeddings or all(f.embedding is not None for f in existente.fragmentos)):
        return existente, "sin_cambios"

    fragmentos = fragmentar(meta, cuerpo)
    vectores = embeber([f.texto for f in fragmentos]) if con_embeddings else [None] * len(fragmentos)
    modelo = nombre_modelo() if con_embeddings else None

    accion = "actualizada" if existente else "nueva"
    p = existente or Politica(id=meta.id, version=meta.version)
    p.nombre, p.tipo, p.historia, p.area_responsable = meta.nombre, meta.tipo, meta.historia, meta.area_responsable
    p.vigente_desde, p.vigente_hasta, p.estado = meta.vigente_desde, meta.vigente_hasta, meta.estado
    p.fuente_nombre, p.fuente_s3_key, p.sha256, p.cargada_por = nombre_archivo, s3_key, meta.sha256, cargada_por
    p.fragmentos.clear()
    s.add(p)
    s.flush()
    for f, v in zip(fragmentos, vectores):
        p.fragmentos.append(FragmentoPolitica(orden=f.orden, seccion=f.seccion, texto=f.texto, reglas=f.reglas,
                                              tokens_aprox=f.tokens_aprox, embedding=v, modelo_embedding=modelo))

    # Una versión vigente nueva cierra la vigencia de las anteriores que seguían abiertas.
    if meta.estado == "vigente":
        anteriores = s.scalars(select(Politica).where(Politica.id == meta.id, Politica.version != meta.version,
                                                      Politica.estado == "vigente")).all()
        for a in anteriores:
            if a.vigente_desde < meta.vigente_desde:
                a.estado = "reemplazada"
                if a.vigente_hasta is None or a.vigente_hasta >= meta.vigente_desde:
                    a.vigente_hasta = meta.vigente_desde - timedelta(days=1)

    s.add(EventoBitacora(actor_tipo="usuario" if cargada_por != "sistema" else "sistema", actor_nombre=cargada_por,
                         accion="politica_cargada", tono="info",
                         detalle=f"Política {meta.id} v{meta.version} {accion}: {len(fragmentos)} fragmentos",
                         datos={"archivo": nombre_archivo, "sha256": meta.sha256, "modelo_embedding": modelo}))
    s.flush()
    return p, accion
