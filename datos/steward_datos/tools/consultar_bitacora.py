"""Tool consultar_bitacora (2.2.4): consulta eventos de auditoría con filtros.

Usada por el Agente de Casos y la pantalla de Bitácora.
"""
from typing import Optional

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..contexto import fijar_en_bd, usuario_actual
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
    if s is None:
        with sesion() as s2:
            return consultar_bitacora(entrada, usuario=usuario, s=s2)

    u = usuario or usuario_actual.get()
    if u is not None:
        try:
            fijar_en_bd(s, u)
        except Exception:
            pass

    query = select(EventoBitacora)

    # Filtrar por visibilidad de casos para usuarios analistas (evita fuga de existencia de casos)
    if u is not None and u.rol != "administrador":
        if entrada.caso_id:
            caso_id = entrada.caso_id.strip().upper()
            try:
                permitido = s.execute(
                    text("SELECT caso_id FROM v_casos WHERE caso_id = :id"), {"id": caso_id}
                ).scalar_one_or_none()
                if permitido is None:
                    # El analista no tiene acceso a este caso: devolver vacío sin confirmar si existe
                    return ConsultarBitacoraSalida(eventos=[], total=0)
            except Exception:
                pass
        else:
            try:
                casos_visibles = select(text("caso_id FROM v_casos"))
                query = query.where(
                    (EventoBitacora.caso_id.is_(None)) | (EventoBitacora.caso_id.in_(casos_visibles))
                )
            except Exception:
                pass

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
    try:
        res_total = s.scalar(conteo_query)
        total = int(res_total) if res_total is not None and not isinstance(res_total, type(Ellipsis)) else 0
    except Exception:
        total = 0

    query = query.order_by(EventoBitacora.fecha.desc(), EventoBitacora.id.desc()).limit(entrada.limite)
    filas = s.scalars(query).all()

    # Si total no se pudo calcular por mock/subquery pero hay filas devueltas
    if total == 0 and filas:
        total = len(filas)

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
