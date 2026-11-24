"""Transmisión SSE del grafo de chat de S1-33.

Integración de desarrollo: el grafo todavía utiliza herramientas simuladas.
Guarda turnos completados cuando se proporciona conversacion_id.
"""

import logging
import os
from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from backend.api.historial_chat import (
    HistorialNoDisponible, obtener_conversacion, guardar_turno,
)
from steward_datos.db.sesion import sesion
from steward_datos.db.models import Mensaje

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.chat_provisional import ConsultaChat, formar_evento
from backend.grafo_chat.flujo import FlujoChat
from contratos.eventos_sse import PasoEvent, RespuestaEvent
from steward_datos.contratos import ContextoUsuario

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ConsultaStream(ConsultaChat):
    conversacion_id: UUID | None = None


def obtener_usuario_chat() -> ContextoUsuario:
    """Identidad configurada en el servidor, solo para desarrollo.

    No toma usuario ni rol del cuerpo de la pregunta.
    La autenticación de producción debe sustituir esta dependencia.
    """
    if os.getenv("AUTH_MODE", "").strip().lower() != "dev":
        raise HTTPException(
            status_code=503,
            detail="La integración del chat requiere autenticación configurada.",
        )

    usuario_id = os.getenv("CHAT_DEV_USUARIO", "dev-ana").strip()

    if not usuario_id:
        raise HTTPException(
            status_code=503,
            detail="Falta configurar el usuario de desarrollo del chat.",
        )

    return ContextoUsuario(
        usuario_id=usuario_id,
        rol="analista",
    )


async def transmitir(
    consulta: ConsultaStream,
    usuario: ContextoUsuario,
    historial=None,
) -> AsyncIterator[str]:
    """Convierte los modelos del grafo en eventos SSE.

    Ante un fallo, termina con un paso de error y no inventa una respuesta.
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
                            s, usuario, consulta.conversacion_id,
                            consulta.mensaje, pasos, evento,
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
        503: {
            "description": "Autenticación de desarrollo no configurada.",
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
                c = obtener_conversacion(s, usuario, consulta.conversacion_id)
                if consulta.caso_id is not None and consulta.caso_id != c.caso_id:
                    raise HTTPException(422, 'El caso no coincide con la conversación')
                consulta = consulta.model_copy(update={'caso_id': c.caso_id})
                anteriores = list(s.scalars(
                    select(Mensaje).where(Mensaje.conversacion_id == c.id)
                    .order_by(Mensaje.id.desc()).limit(50)
                ))
                roles = {'usuario': 'user', 'asistente': 'assistant', 'sistema': 'system'}
                historial = [
                    {'role': roles[m.rol], 'content': m.contenido}
                    for m in reversed(anteriores)
                ]
        except HistorialNoDisponible:
            raise HTTPException(404, 'Conversación o caso no disponible') from None
        except SQLAlchemyError:
            logger.exception('No se pudo recuperar el historial del chat')
            raise HTTPException(503, 'El historial no está disponible temporalmente') from None
    return StreamingResponse(
        transmitir(consulta, usuario, historial),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )