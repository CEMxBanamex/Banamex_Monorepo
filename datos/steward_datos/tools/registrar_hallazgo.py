"""Tool registrar_hallazgo (2.2.3): escribe un hallazgo y su evento en la bitácora, en la misma transacción."""
from typing import Optional

from sqlalchemy.orm import Session

from ..contratos import RegistrarHallazgoEntrada, RegistrarHallazgoSalida
from ..db.models import Caso, EventoBitacora, Hallazgo, Regla
from ..db.sesion import sesion


def registrar_hallazgo(entrada: RegistrarHallazgoEntrada, s: Optional[Session] = None) -> RegistrarHallazgoSalida:
    if s is None:
        with sesion() as s2:
            return registrar_hallazgo(entrada, s2)
    h = entrada.hallazgo
    if s.get(Caso, entrada.caso_id) is None:
        raise ValueError(f"El caso {entrada.caso_id} no existe.")
    if s.get(Regla, (h.regla_id, h.regla_version)) is None:
        raise ValueError(f"La regla {h.regla_id} v{h.regla_version} no está en el catálogo.")
    fila = Hallazgo(caso_id=entrada.caso_id, regla_id=h.regla_id, regla_version=h.regla_version, politica_id=h.politica_id,
                    efecto=h.efecto, severidad=h.severidad, titulo=h.titulo, texto=h.texto,
                    cifras=[list(c) for c in h.cifras] if h.cifras else None, campos=h.campos or None, filas=h.filas,
                    evidencia=h.evidencia, evidencia_detalle=h.evidencia_detalle, origen=entrada.origen,
                    fragmentos_ids=entrada.fragmentos_ids or None)
    s.add(fila)
    s.flush()
    ev = EventoBitacora(caso_id=entrada.caso_id, actor_tipo="agente" if entrada.origen != "humano" else "usuario",
                        actor_nombre=entrada.actor_nombre, accion="regla_aplicada", tono="info", detalle=h.titulo,
                        regla_id=h.regla_id, regla_version=h.regla_version, hallazgo_id=fila.id)
    s.add(ev)
    s.flush()
    return RegistrarHallazgoSalida(hallazgo_id=fila.id, evento_id=ev.id)
