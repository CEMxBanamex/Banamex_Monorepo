"""Tool consultar_bitacora (2.2.4): consulta eventos de auditoría con filtros.

Usada por el Agente de Casos y la pantalla de Bitácora.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contratos import ConsultarBitacoraEntrada, ConsultarBitacoraSalida, EventoBitacoraDetalle
from ..db.models import EventoBitacora
from ..db.sesion import sesion


def consultar_bitacora(entrada: ConsultarBitacoraEntrada, s: Optional[Session] = None) -> ConsultarBitacoraSalida:
    if s is None:
        with sesion() as s2:
            return consultar_bitacora(entrada, s2)

    query = select(EventoBitacora)

    if entrada.caso_id:
        query = query.where(EventoBitacora.caso_id == entrada.caso_id.strip().upper())
    if entrada.actor_nombre:
        patron = f"%{entrada.actor_nombre.strip()}%"
        query = query.where(EventoBitacora.actor_nombre.ilike(patron))
    if entrada.accion:
        query = query.where(EventoBitacora.accion == entrada.accion.strip())
    if entrada.fecha_desde:
        query = query.where(EventoBitacora.fecha >= entrada.fecha_desde)
    if entrada.fecha_hasta:
        query = query.where(EventoBitacora.fecha <= entrada.fecha_hasta)

    query = query.order_by(EventoBitacora.fecha.desc(), EventoBitacora.id.desc()).limit(entrada.limite)
    filas = s.scalars(query).all()

    eventos = [
        EventoBitacoraDetalle(
            id=f"EV-{e.id}",
            fecha=e.fecha,
            caso_id=e.caso_id,
            actor_tipo=e.actor_tipo,
            actor_nombre=e.actor_nombre,
            accion=e.accion,
            tono=e.tono,
            detalle=e.detalle,
            regla=f"{e.regla_id} · v{e.regla_version}" if e.regla_id else None,
            datos=e.datos,
        )
        for e in filas
    ]
    return ConsultarBitacoraSalida(eventos=eventos, total=len(eventos))
