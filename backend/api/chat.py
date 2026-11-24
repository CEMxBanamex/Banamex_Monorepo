"""Endpoints HTTP para el chat agéntico."""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.api.autenticacion import resolver_usuario
from backend.grafo_chat.flujo import FlujoChat
from contratos.eventos_sse import EventoSSE
from steward_datos.contratos import ContextoUsuario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

flujo_chat = FlujoChat()


class SolicitudChat(BaseModel):
    """Entrada para una conversación con el agente."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pregunta: str = Field(min_length=1, max_length=10000)
    historial: list[dict] = Field(default_factory=list, max_length=50)
    caso_id: str | None = Field(default=None, max_length=200)


def _serializar_evento(evento: EventoSSE) -> str:
    """Convierte un evento del grafo al formato Server-Sent Events."""

    return f"data: {evento.model_dump_json()}\n\n"


async def _generar_eventos(
    solicitud: SolicitudChat,
    usuario: ContextoUsuario,
) -> AsyncIterator[str]:
    """Ejecuta el grafo y transmite sus eventos al cliente."""

    try:
        async for evento in flujo_chat.astream_chat(
            pregunta=solicitud.pregunta,
            usuario_id=usuario.usuario_id,
            rol=usuario.rol,
            historial=solicitud.historial,
            caso_id=solicitud.caso_id,
        ):
            yield _serializar_evento(evento)

    except Exception:
        logger.exception("Error durante la ejecución del chat")
        error = {
            "tipo": "error",
            "mensaje": "Ocurrió un error al procesar la solicitud.",
        }
        yield f"event: error\ndata: {json.dumps(error, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def transmitir_chat(
    solicitud: SolicitudChat,
    usuario: ContextoUsuario = Depends(resolver_usuario),
) -> StreamingResponse:
    """Transmite el progreso y la respuesta del agente mediante SSE."""

    return StreamingResponse(
        _generar_eventos(solicitud, usuario),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
