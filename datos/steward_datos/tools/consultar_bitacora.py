"""Tool consultar_bitacora (2.2.4): consulta eventos de auditoría con filtros.

Usada por el Agente de Casos y la pantalla de Bitácora.
"""
from typing import Optional

from sqlalchemy import column, func, select, table
from sqlalchemy.orm import Session

from ..contexto import fijar_en_bd, requerir_usuario
from ..contratos import ConsultarBitacoraEntrada, ConsultarBitacoraSalida, ContextoUsuario, EventoBitacoraDetalle
from ..db.models import EventoBitacora
from ..db.sesion import sesion


def _patron(valor: str) -> str:
    """Escapa caracteres especiales de SQL LIKE/ILIKE usando ! como escape."""
    escapado = valor.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escapado}%"


def consultar_bitacora(
    entrada: ConsultarBitacoraEntrada,
    usuario: Optional[ContextoUsuario] = None,
    s: Optional[Session] = None,
) -> ConsultarBitacoraSalida:
    """Consulta eventos de bitácora respetando visibilidad de casos por usuario y conteo total."""
    u = requerir_usuario(usuario)
    if s is None:
        with sesion() as s2:
            return consultar_bitacora(entrada, usuario=u, s=s2)

    fijar_en_bd(s, u)
    query = select(EventoBitacora)
    if u.rol != "administrador":
        casos_visibles = table("v_casos", column("caso_id"))
        query = query.where(EventoBitacora.caso_id.in_(select(casos_visibles.c.caso_id)))

    if entrada.caso_id:
        query = query.where(EventoBitacora.caso_id == entrada.caso_id.strip().upper())
    if entrada.actor_nombre:
        patron = _patron(entrada.actor_nombre.strip())
        query = query.where(EventoBitacora.actor_nombre.ilike(patron, escape="!"))
    if entrada.accion:
        query = query.where(EventoBitacora.accion == entrada.accion.strip())
    if entrada.fecha_desde:
        query = query.where(EventoBitacora.fecha >= entrada.fecha_desde)
    if entrada.fecha_hasta:
        query = query.where(EventoBitacora.fecha <= entrada.fecha_hasta)

    # Conteo total real sin el recorte de límite
    conteo_query = select(func.count()).select_from(query.subquery())
    total = s.execute(conteo_query).scalar_one()
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
    return ConsultarBitacoraSalida(eventos=eventos, total=total)
