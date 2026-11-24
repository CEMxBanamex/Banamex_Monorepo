"""Transmisión SSE del grafo de chat de S1-33.

Integración de desarrollo: el grafo todavía utiliza herramientas simuladas.
No guarda conversaciones ni mensajes.
"""

import logging
import os
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.chat_provisional import ConsultaChat, formar_evento
from backend.grafo_chat.flujo import FlujoChat
from contratos.eventos_sse import PasoEvent, RespuestaEvent
from steward_datos.contratos import ContextoUsuario

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


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


def transmitir(
    consulta: ConsultaChat,
    usuario: ContextoUsuario,
) -> Iterator[str]:
    """Convierte los modelos del grafo en eventos SSE.

    Ante un fallo, termina con un paso de error y no inventa una respuesta.
    """
    respuesta_recibida = False
    error_emitido = False

    try:
        flujo = FlujoChat()

        for evento in flujo.stream_chat(
            pregunta=consulta.mensaje,
            usuario_id=usuario.usuario_id,
            rol=usuario.rol,
            historial=[],
            caso_id=consulta.caso_id,
        ):
            if isinstance(evento, PasoEvent):
                if evento.estado == "error":
                    error_emitido = True

                yield formar_evento("paso", evento)

                if error_emitido:
                    return

            elif isinstance(evento, RespuestaEvent):
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
    consulta: ConsultaChat,
    usuario: ContextoUsuario = Depends(obtener_usuario_chat),
) -> StreamingResponse:
    return StreamingResponse(
        transmitir(consulta, usuario),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )