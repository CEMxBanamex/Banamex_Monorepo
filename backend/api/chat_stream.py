"""Transmisión SSE del chat con identidad por solicitud e historial persistente."""

import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.api.autenticacion import resolver_usuario
from backend.api.chat_provisional import ConsultaChat, formar_evento
from backend.api.historial_chat import (
    HistorialNoDisponible,
    guardar_turno,
    obtener_conversacion,
)
from backend.grafo_chat.flujo import FlujoChat
from contratos.eventos_sse import PasoEvent, RespuestaEvent
from steward_datos.contratos import ContextoUsuario
from steward_datos.db.models import Mensaje
from steward_datos.db.sesion import sesion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ConsultaStream(ConsultaChat):
    conversacion_id: UUID | None = None


def obtener_usuario_chat(
    usuario: ContextoUsuario = Depends(resolver_usuario),
) -> ContextoUsuario:
    """Comparte la identidad autenticada entre el stream y el historial."""
    return usuario


async def transmitir(
    consulta: ConsultaStream,
    usuario: ContextoUsuario,
    historial=None,
) -> AsyncIterator[str]:
    """Convierte los eventos del grafo al formato SSE.

    Guarda los turnos completados cuando existe conversacion_id.
    Ante un fallo, emite un paso de error sin inventar una respuesta.
    """
    pasos = []
    respuesta_recibida = False
    error_emitido = False

    try:
        flujo = FlujoChat()

        async for evento in flujo.astream_chat(
            pregunta=consulta.mensaje,
            usuario_id=usuario.usuario_id,
            rol=usuario.rol,
            historial=historial or [],
            caso_id=consulta.caso_id,
        ):
            if isinstance(evento, PasoEvent):
                pasos.append(evento)

                if evento.estado == "error":
                    error_emitido = True

                yield formar_evento("paso", evento)

                if error_emitido:
                    return

            elif isinstance(evento, RespuestaEvent):
                if consulta.conversacion_id is not None:
                    with sesion() as s:
                        guardar_turno(
                            s,
                            usuario,
                            consulta.conversacion_id,
                            consulta.mensaje,
                            pasos,
                            evento,
                        )

                respuesta_recibida = True
                yield formar_evento("respuesta", evento)
                return

            else:
                raise TypeError("El grafo devolvió un evento no admitido.")

        if not respuesta_recibida:
            raise RuntimeError("El grafo terminó sin respuesta final.")

    except Exception:
        logger.exception("No se pudo completar el flujo del chat.")

        if not error_emitido:
            yield formar_evento(
                "paso",
                PasoEvent(
                    id="chat-error",
                    texto="No se pudo completar la consulta",
                    detalle="Intenta nuevamente. Si persiste, reporta el problema.",
                    estado="error",
                ),
            )


@router.post(
    "/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Pasos y respuesta del grafo de chat.",
            "content": {"text/event-stream": {}},
        },
        401: {
            "description": "Falta una identidad válida.",
        },
        403: {
            "description": "El usuario no tiene un rol autorizado.",
        },
        404: {
            "description": "Conversación o caso no disponible.",
        },
        503: {
            "description": "Autenticación o historial no disponibles.",
        },
    },
)
def consultar_chat_stream(
    consulta: ConsultaStream,
    usuario: ContextoUsuario = Depends(obtener_usuario_chat),
) -> StreamingResponse:
    historial = []

    if consulta.conversacion_id is not None:
        try:
            with sesion() as s:
                conversacion = obtener_conversacion(
                    s,
                    usuario,
                    consulta.conversacion_id,
                )

                if (
                    consulta.caso_id is not None
                    and consulta.caso_id != conversacion.caso_id
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="El caso no coincide con la conversación",
                    )

                consulta = consulta.model_copy(
                    update={"caso_id": conversacion.caso_id},
                )

                anteriores = list(
                    s.scalars(
                        select(Mensaje)
                        .where(
                            Mensaje.conversacion_id == conversacion.id,
                        )
                        .order_by(Mensaje.id.desc())
                        .limit(50)
                    )
                )

                roles = {
                    "usuario": "user",
                    "asistente": "assistant",
                    "sistema": "system",
                }

                historial = [
                    {
                        "role": roles[mensaje.rol],
                        "content": mensaje.contenido,
                    }
                    for mensaje in reversed(anteriores)
                ]

        except HistorialNoDisponible:
            raise HTTPException(
                status_code=404,
                detail="Conversación o caso no disponible",
            ) from None

        except SQLAlchemyError:
            logger.exception("No se pudo recuperar el historial del chat.")
            raise HTTPException(
                status_code=503,
                detail="El historial no está disponible temporalmente",
            ) from None

    return StreamingResponse(
        transmitir(consulta, usuario, historial),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
