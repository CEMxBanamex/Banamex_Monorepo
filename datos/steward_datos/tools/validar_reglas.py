"""Tool validar_reglas (2.2.1): comprobaciones exactas en código. Lee de la base el padrón, las entidades y los antecedentes."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contratos import Antecedente, ResultadoValidacion, ValidarReglasEntrada
from ..db.models import Documento, EntidadReceptora, Factura, Proveedor
from ..db.sesion import sesion
from ..reglas.motor import Contexto, validar_factura, validar_registros


def contexto_desde_bd(s: Session, entrada: ValidarReglasEntrada) -> Contexto:
    prov = set(s.scalars(select(Proveedor.rfc).where(Proveedor.activo.is_(True))))
    ent = set(s.scalars(select(EntidadReceptora.rfc)))
    filas = s.execute(
        select(Factura.caso_id, Factura.emisor_rfc, Factura.folio, Documento.sha256)
        .join(Documento, (Documento.caso_id == Factura.caso_id) & Documento.principal, isouter=True)
        .where(Factura.caso_id != entrada.caso_id)
    ).all()
    antecedentes = [Antecedente(caso_id=c, emisor_rfc=r, folio=f, sha256=h) for c, r, f, h in filas]
    # Un archivo idéntico puede estar en un caso cuya extracción falló; también cuenta.
    antecedentes += [Antecedente(caso_id=c, emisor_rfc=None, folio=None, sha256=h) for c, h in s.execute(
        select(Documento.caso_id, Documento.sha256).where(Documento.caso_id != entrada.caso_id, Documento.principal)
    ).all() if c not in {a.caso_id for a in antecedentes}]
    return Contexto(proveedores_activos=prov or None, entidades_receptoras=ent or None, antecedentes=antecedentes,
                    sha256=entrada.sha256, fecha_recepcion=entrada.fecha_recepcion)


def validar_reglas(entrada: ValidarReglasEntrada, s: Optional[Session] = None) -> ResultadoValidacion:
    if entrada.historia == 1 and entrada.factura is None:
        raise ValueError("La Historia 1 necesita `factura` (salida de extraer_campos_factura).")
    if entrada.historia == 2 and entrada.registros is None:
        raise ValueError("La Historia 2 necesita `registros` (salida de leer_pdf_o_excel).")
    if s is None:
        with sesion() as s2:
            return validar_reglas(entrada, s2)
    if entrada.historia == 1:
        return validar_factura(entrada.caso_id, entrada.factura, contexto_desde_bd(s, entrada))
    return validar_registros(entrada.caso_id, entrada.registros, Contexto(fecha_recepcion=entrada.fecha_recepcion))
