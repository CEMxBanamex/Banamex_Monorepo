"""Adaptador de herramientas de Datos y persistencia para el piloto local."""
from datetime import date, datetime, timezone
import uuid

from sqlalchemy import select

from steward_datos.contratos import ContextoUsuario, FacturaExtraida, ResultadoValidacion, ValidarReglasEntrada
from steward_datos.db.models import Caso, EventoBitacora
from steward_datos.db.sesion import sesion
from steward_datos.persistencia import guardar_extraccion, guardar_resultado
from steward_datos.tools.buscar_politicas import buscar_politicas
from steward_datos.tools.validar_reglas import validar_reglas
from steward_datos.validador import preparar_para_redactor


class HerramientasReales:
    def __init__(self, usuario: ContextoUsuario):
        if usuario.rol != "analista":
            raise PermissionError("Solo un analista puede procesar y decidir casos.")
        self.usuario = usuario

    def _caso(self, s, caso_id: str) -> Caso:
        caso = s.scalar(select(Caso).where(Caso.id == caso_id).with_for_update())
        if caso is None or caso.responsable_id != self.usuario.usuario_id:
            raise PermissionError("Caso inexistente o no autorizado.")
        return caso

    def iniciar(self, caso_id: str) -> str:
        with sesion() as s:
            if s.get(Caso, caso_id) is not None:
                raise ValueError("El caso ya existe; usar un identificador nuevo.")
            thread = uuid.uuid4()
            s.add(Caso(id=caso_id, tipo="factura", estado="procesando", thread_id=thread,
                       responsable_id=self.usuario.usuario_id, responsable_nombre=self.usuario.usuario_id))
            s.flush()
            s.add(EventoBitacora(caso_id=caso_id, actor_tipo="usuario", actor_id=self.usuario.usuario_id,
                                 actor_nombre=self.usuario.usuario_id, accion="caso_creado", tono="info",
                                 detalle="Caso iniciado desde el piloto local."))
            return str(thread)

    def validar(self, caso_id: str, factura: dict, sha256: str, fecha: str):
        with sesion() as s:
            self._caso(s, caso_id)
            entrada = ValidarReglasEntrada(caso_id=caso_id, historia=1,
                                          factura=FacturaExtraida.model_validate(factura),
                                          sha256=sha256, fecha_recepcion=date.fromisoformat(fecha))
            return validar_reglas(entrada, s)

    def politicas(self, resultado: dict, fecha: str):
        with sesion() as s:
            r = ResultadoValidacion.model_validate(resultado)
            self._caso(s, r.caso_id)
            ids = {}

            def buscar(entrada):
                salida = buscar_politicas(entrada, s)
                for f in salida.fragmentos:
                    for regla in entrada.reglas or []:
                        hallazgo = next((h for h in r.hallazgos if h.regla_id == regla), None)
                        if hallazgo and (f.politica_id, f.version, f.seccion) == (
                            hallazgo.politica_id, hallazgo.politica_version, hallazgo.politica_seccion
                        ):
                            ids.setdefault(regla, []).append(f.fragmento_id)
                return salida

            salida = preparar_para_redactor(r, historia=1, buscar=buscar, fecha=date.fromisoformat(fecha))
            return salida.model_dump(mode="json"), ids

    def guardar(self, caso_id: str, factura: dict, resultado: dict, explicacion: str, fragmentos: dict):
        with sesion() as s:
            caso = self._caso(s, caso_id)
            if caso.estado == "revision":
                return  # reejecución del nodo tras un checkpoint fallido
            if caso.estado != "procesando":
                raise ValueError("El caso no está en procesamiento.")
            ahora = datetime.now(timezone.utc)
            guardar_extraccion(s, caso_id, FacturaExtraida.model_validate(factura), cuando=ahora)
            guardar_resultado(s, ResultadoValidacion.model_validate(resultado), cuando=ahora,
                              explicacion=explicacion, fragmentos_por_regla=fragmentos)
            # guardar_resultado usa registrar_hallazgo dentro de esta misma transacción.

    def cerrar(self, caso_id: str, decision: dict):
        with sesion() as s:
            caso = self._caso(s, caso_id)
            if caso.estado == "revisado":
                anterior = s.scalar(select(EventoBitacora).where(
                    EventoBitacora.caso_id == caso_id, EventoBitacora.accion == "confirmacion"
                ).order_by(EventoBitacora.id.desc()))
                if anterior and anterior.datos == decision and anterior.actor_id == self.usuario.usuario_id:
                    return
                raise ValueError("El caso ya tiene otra decisión final.")
            if caso.estado != "revision":
                raise ValueError("El caso no está esperando revisión.")
            caso.estado, caso.resultado_final = "revisado", decision["resultado"]
            caso.revisado_por, caso.revisado_en = self.usuario.usuario_id, datetime.now(timezone.utc)
            s.add(EventoBitacora(caso_id=caso_id, actor_tipo="usuario", actor_id=self.usuario.usuario_id,
                                 actor_nombre=self.usuario.usuario_id, accion="confirmacion",
                                 tono="exito" if decision["resultado"] == "aceptado" else "error",
                                 detalle=decision["motivo"], datos=decision))

    def error(self, caso_id: str):
        with sesion() as s:
            caso = self._caso(s, caso_id)
            if caso.estado != "procesando":
                return
            caso.estado, caso.error_detalle = "error", "No se completó el análisis; requiere revisión técnica."
            s.add(EventoBitacora(caso_id=caso_id, actor_tipo="agente", actor_nombre="Agente",
                                 accion="error", tono="error", detalle=caso.error_detalle))
