"""Guardar en la base lo que produce el grafo: la extracción de una factura y el resultado de validar_reglas.

Lo usan procesar_caso() (Agentes) y el script de semilla.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .contratos import ETIQUETAS, FacturaExtraida, ResultadoValidacion
from .db.models import CampoExtraido, Caso, ConceptoFactura, EventoBitacora, Factura, Hallazgo
from .reglas import normalizar as n

CAMPOS_VISIBLES = ("emisor_nombre", "fecha", "subtotal", "impuestos", "total", "moneda",
                   "folio", "emisor_rfc", "receptor_nombre", "receptor_rfc", "tasa_iva", "retenciones")


def guardar_extraccion(s: Session, caso_id: str, f: FacturaExtraida, *, cuando: Optional[datetime] = None,
                       archivo: str = "", registrar_evento: bool = True) -> Factura:
    v = lambda c: f.campos[c].valor if c in f.campos else None
    fac = s.get(Factura, caso_id) or Factura(caso_id=caso_id)
    fac.tipo_documento = f.tipo_documento
    fac.folio, fac.fecha_emision = v("folio"), n.fecha(v("fecha"))
    fac.emisor_nombre, fac.emisor_rfc = v("emisor_nombre"), (n.rfc_normalizado(v("emisor_rfc"))[:13] or None)
    fac.receptor_nombre, fac.receptor_rfc = v("receptor_nombre"), (n.rfc_normalizado(v("receptor_rfc"))[:13] or None)
    fac.moneda = (v("moneda") or "")[:3].upper() or None
    fac.subtotal, fac.impuestos, fac.total = n.monto(v("subtotal")), n.monto(v("impuestos")), n.monto(v("total"))
    fac.retenciones, fac.tasa_iva = n.monto(v("retenciones")), n.tasa(v("tasa_iva"))
    fac.modelo_extraccion, fac.extraido_en = f.modelo, cuando
    fac.salida_cruda = f.model_dump(mode="json")
    s.add(fac)
    s.flush()
    fac.conceptos.clear()
    for i, c in enumerate(f.conceptos):
        fac.conceptos.append(ConceptoFactura(orden=i, descripcion=c.descripcion, cantidad=n.monto(c.cantidad),
                                             precio_unitario=n.monto(c.precio_unitario), importe=n.monto(c.importe)))
    s.query(CampoExtraido).filter_by(caso_id=caso_id).delete()
    for campo in CAMPOS_VISIBLES:
        if campo in f.campos:
            c = f.campos[campo]
            s.add(CampoExtraido(caso_id=caso_id, campo=campo, etiqueta=ETIQUETAS[campo], valor=c.valor,
                                confianza=c.confianza, pagina=c.pagina, bbox=c.bbox))
    if registrar_evento:
        s.add(EventoBitacora(caso_id=caso_id, fecha=cuando, actor_tipo="agente", actor_nombre="Agente", accion="extraccion",
                             tono="info", detalle=f"{len([c for c in f.campos.values() if c.valor])} campos extraídos" + (f" de {archivo}" if archivo else ""),
                             datos={"modelo": f.modelo}))
    s.flush()
    return fac


def guardar_resultado(s: Session, r: ResultadoValidacion, *, cuando: Optional[datetime] = None, explicacion: Optional[str] = None,
                      fragmentos_por_regla: Optional[dict[str, list[int]]] = None) -> list[Hallazgo]:
    caso = s.get(Caso, r.caso_id)
    s.query(Hallazgo).filter_by(caso_id=r.caso_id).delete()
    guardados = []
    for h in r.hallazgos:
        fila = Hallazgo(caso_id=r.caso_id, regla_id=h.regla_id, regla_version=h.regla_version, politica_id=h.politica_id,
                        efecto=h.efecto, severidad=h.severidad, titulo=h.titulo, texto=h.texto,
                        cifras=[list(c) for c in h.cifras] if h.cifras else None, campos=h.campos or None, filas=h.filas,
                        evidencia=h.evidencia, evidencia_detalle=h.evidencia_detalle, origen="codigo",
                        fragmentos_ids=(fragmentos_por_regla or {}).get(h.regla_id), creado_en=cuando)
        s.add(fila)
        s.flush()
        s.add(EventoBitacora(caso_id=r.caso_id, fecha=cuando, actor_tipo="agente", actor_nombre="Agente", accion="regla_aplicada",
                             tono="info", detalle=h.titulo, regla_id=h.regla_id, regla_version=h.regla_version, hallazgo_id=fila.id))
        guardados.append(fila)
    caso.resultado_sugerido = r.resultado_sugerido
    caso.explicacion = explicacion or r.motivo
    caso.estado = "revision"
    s.add(EventoBitacora(caso_id=r.caso_id, fecha=cuando, actor_tipo="agente", actor_nombre="Agente", accion="resultado_sugerido",
                         tono="info", detalle=f"Resultado sugerido: {r.resultado_sugerido}",
                         datos={"reglas_evaluadas": r.reglas_evaluadas, "motivo": r.motivo}))
    s.flush()
    return guardados
