"""Tools de datos del chat (3.1.1 consultar_caso y 3.1.2 buscar_facturas). Solo lectura, sin SQL escrito por el LLM."""
from typing import Optional

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from ..contratos import (
    BuscarFacturasEntrada, BuscarFacturasSalida, CampoCaso, CasoOut, EventoOut, FacturaResumen, HallazgoOut,
)
from ..db.models import CampoExtraido, Caso, Documento, EventoBitacora, Factura, Hallazgo
from ..db.sesion import sesion


def consultar_caso(caso_id: str, s: Optional[Session] = None, max_eventos: int = 50) -> CasoOut:
    if s is None:
        with sesion() as s2:
            return consultar_caso(caso_id, s2, max_eventos)
    c = s.get(Caso, caso_id.strip().upper())
    if c is None:
        raise ValueError(f"No existe el caso {caso_id}.")
    doc = s.scalars(select(Documento).where(Documento.caso_id == c.id, Documento.principal)).first()
    campos = s.scalars(select(CampoExtraido).where(CampoExtraido.caso_id == c.id).order_by(CampoExtraido.id)).all()
    hallazgos = s.scalars(select(Hallazgo).where(Hallazgo.caso_id == c.id).order_by(Hallazgo.id)).all()
    eventos = s.scalars(select(EventoBitacora).where(EventoBitacora.caso_id == c.id)
                        .order_by(EventoBitacora.fecha.desc(), EventoBitacora.id.desc()).limit(max_eventos)).all()
    return CasoOut(
        id=c.id, tipo=c.tipo, estado=c.estado, resultado_sugerido=c.resultado_sugerido, resultado_final=c.resultado_final,
        explicacion=c.explicacion, archivo=doc.nombre if doc else None, responsable=c.responsable_nombre, creado_en=c.creado_en,
        campos=[CampoCaso(campo=x.campo, etiqueta=x.etiqueta, valor=x.valor, confianza=x.confianza, valor_corregido=x.valor_corregido)
                for x in campos],
        hallazgos=[HallazgoOut(regla_id=h.regla_id, regla_version=h.regla_version, politica_id=h.politica_id or "",
                               efecto=h.efecto, severidad=h.severidad, titulo=h.titulo, texto=h.texto,
                               cifras=[tuple(x) for x in h.cifras] if h.cifras else None, campos=h.campos or [],
                               filas=h.filas, evidencia=h.evidencia, evidencia_detalle=h.evidencia_detalle) for h in hallazgos],
        eventos=[EventoOut(id=f"EV-{e.id}", fecha=e.fecha, actor=e.actor_nombre, accion=e.accion, tono=e.tono, detalle=e.detalle,
                           regla=f"{e.regla_id} · v{e.regla_version}" if e.regla_id else None) for e in eventos],
    )


ORDENES = {
    "fecha_desc": (Factura.fecha_emision.desc().nulls_last(),), "fecha_asc": (Factura.fecha_emision.asc().nulls_last(),),
    "total_desc": (Factura.total.desc().nulls_last(),), "total_asc": (Factura.total.asc().nulls_last(),),
}


def buscar_facturas(entrada: BuscarFacturasEntrada, s: Optional[Session] = None) -> BuscarFacturasSalida:
    if s is None:
        with sesion() as s2:
            return buscar_facturas(entrada, s2)
    filtros = []
    if entrada.emisor:
        patron = f"%{entrada.emisor.strip()}%"
        filtros.append(Factura.emisor_nombre.ilike(patron) | Factura.emisor_rfc.ilike(patron))
    if entrada.folio:
        filtros.append(Factura.folio.ilike(f"%{entrada.folio.strip()}%"))
    if entrada.fecha_desde:
        filtros.append(Factura.fecha_emision >= entrada.fecha_desde)
    if entrada.fecha_hasta:
        filtros.append(Factura.fecha_emision <= entrada.fecha_hasta)
    if entrada.total_min is not None:
        filtros.append(Factura.total >= entrada.total_min)
    if entrada.total_max is not None:
        filtros.append(Factura.total <= entrada.total_max)
    if entrada.moneda:
        filtros.append(Factura.moneda == entrada.moneda.upper())
    if entrada.resultado:
        filtros.append(func.coalesce(Caso.resultado_final, Caso.resultado_sugerido) == entrada.resultado)
    if entrada.estado:
        filtros.append(Caso.estado == entrada.estado)
    if entrada.con_regla:
        filtros.append(exists().where(Hallazgo.caso_id == Caso.id, Hallazgo.regla_id == entrada.con_regla.upper()))

    base = select(Factura, Caso).join(Caso, Caso.id == Factura.caso_id).where(*filtros)
    total = s.scalar(select(func.count()).select_from(base.subquery()))
    filas = s.execute(base.order_by(*ORDENES[entrada.orden], Caso.id).limit(entrada.limite)).all()
    reglas = {}
    if filas:
        for caso_id, regla in s.execute(select(Hallazgo.caso_id, Hallazgo.regla_id)
                                        .where(Hallazgo.caso_id.in_([c.id for _, c in filas])).distinct()):
            reglas.setdefault(caso_id, []).append(regla)
    return BuscarFacturasSalida(total_coincidencias=total, facturas=[
        FacturaResumen(caso_id=c.id, folio=f.folio, fecha_emision=f.fecha_emision, emisor_nombre=f.emisor_nombre,
                       emisor_rfc=f.emisor_rfc, total=float(f.total) if f.total is not None else None, moneda=f.moneda,
                       estado=c.estado, resultado_sugerido=c.resultado_final or c.resultado_sugerido,
                       reglas_con_hallazgo=sorted(reglas.get(c.id, [])))
        for f, c in filas
    ])
