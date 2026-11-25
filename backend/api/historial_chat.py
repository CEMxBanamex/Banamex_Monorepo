"""Persistencia del chat; la transacción pertenece al llamador."""

from uuid import UUID

from sqlalchemy import func, select, text

from contratos.eventos_sse import PasoEvent, RespuestaEvent
from steward_datos.contexto import fijar_en_bd, requerir_usuario
from steward_datos.db.models import Conversacion, Mensaje


class HistorialNoDisponible(ValueError):
    pass


def _autorizar_caso(s, usuario, caso_id):
    if caso_id is not None:
        fijar_en_bd(s, usuario)
        permitido = s.execute(
            text("SELECT caso_id FROM v_casos WHERE caso_id = :id"),
            {"id": caso_id},
        ).scalar_one_or_none()
        if permitido is None:
            raise HistorialNoDisponible("Caso inexistente o sin acceso")


def crear_conversacion(s, usuario, titulo, caso_id=None):
    usuario = requerir_usuario(usuario)
    titulo = titulo.strip()
    if not titulo or len(titulo) > 200:
        raise ValueError("El título debe tener entre 1 y 200 caracteres")
    _autorizar_caso(s, usuario, caso_id)
    conversacion = Conversacion(
        usuario_id=usuario.usuario_id,
        usuario_nombre=usuario.usuario_id,
        titulo=titulo,
        caso_id=caso_id,
    )
    s.add(conversacion)
    s.flush()
    return conversacion


def obtener_conversacion(s, usuario, conversacion_id, bloquear=False):
    usuario = requerir_usuario(usuario)
    try:
        identificador = UUID(str(conversacion_id))
    except (ValueError, TypeError, AttributeError):
        raise HistorialNoDisponible("Conversación no disponible") from None
    consulta = select(Conversacion).where(
        Conversacion.id == identificador,
        Conversacion.usuario_id == usuario.usuario_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    conversacion = s.scalar(consulta)
    if conversacion is None:
        raise HistorialNoDisponible("Conversación no disponible")
    _autorizar_caso(s, usuario, conversacion.caso_id)
    return conversacion


def leer_mensajes(s, usuario, conversacion_id):
    conversacion = obtener_conversacion(s, usuario, conversacion_id)
    return list(s.scalars(
        select(Mensaje)
        .where(Mensaje.conversacion_id == conversacion.id)
        .order_by(Mensaje.id)
    ))


def guardar_turno(s, usuario, conversacion_id, pregunta, pasos, respuesta):
    """Guarda pregunta y respuesta juntas; no realiza commit por su cuenta.

    Esta función admite únicamente turnos completados. Los fallos y las
    cancelaciones deben incorporarse al conectar la persistencia al stream.
    """
    pregunta = pregunta.strip()
    if not pregunta or len(pregunta) > 2000:
        raise ValueError("La pregunta debe tener entre 1 y 2000 caracteres")
    pasos = [PasoEvent.model_validate(paso) for paso in pasos]
    respuesta = RespuestaEvent.model_validate(respuesta)
    if any(paso.estado == "error" for paso in pasos):
        raise ValueError("Un turno con error no puede guardarse como exitoso")
    conversacion = obtener_conversacion(
        s, usuario, conversacion_id, bloquear=True,
    )
    if respuesta.caso_id != conversacion.caso_id:
        raise ValueError("El caso de la respuesta no coincide con la conversación")
    entrada = Mensaje(
        conversacion_id=conversacion.id, rol="usuario", contenido=pregunta,
        pasos=[],
    )
    salida = Mensaje(
        conversacion_id=conversacion.id,
        rol="asistente",
        contenido=respuesta.respuesta,
        pasos=[paso.model_dump(mode="json") for paso in pasos],
        citas=[{"fuente": fuente} for fuente in respuesta.fuentes],
        duracion_ms=respuesta.duracion_ms,
    )
    s.add(entrada)
    s.flush()
    s.add(salida)
    conversacion.actualizada_en = func.now()
    s.flush()
    return entrada, salida
