"""Borrador de contrato del chat: respuestas fijas, sin IA ni base de datos."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/chat", tags=["Chat provisional"])


class ConsultaChat(BaseModel):
    """Datos que enviaría la pantalla del chat."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    mensaje: str = Field(min_length=1, max_length=2000)
    caso_id: str | None = Field(default=None, min_length=1, max_length=100)


class RespuestaChat(BaseModel):
    """Respuesta de ejemplo, pendiente de revisión del equipo."""

    respuesta: str
    caso_id: str | None
    simulado: bool


@router.post("/consulta", response_model=RespuestaChat)
def consultar_chat(consulta: ConsultaChat) -> RespuestaChat:
    """Devuelve una respuesta fija para probar el contrato del chat."""

    return RespuestaChat(
        respuesta=(
            "Esta es una respuesta de prueba del chat. "
            "Todavía no se consultan casos, políticas ni modelos de IA."
        ),
        caso_id=consulta.caso_id,
        simulado=True,
    )
class PasoChat(BaseModel):
    """Formato propuesto para los pasos visibles del chat."""

    id: str
    texto: str
    detalle: str | None = None
    estado: Literal["pendiente", "en_curso", "completado", "error"]


def formar_evento(
    nombre: str,
    contenido: PasoChat | RespuestaChat,
) -> str:
    """Convierte los datos al formato de un evento SSE."""

    return f"event: {nombre}\ndata: {contenido.model_dump_json()}\n\n"


@router.post(
    "/consulta/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Eventos simulados de paso y respuesta.",
            "content": {"text/event-stream": {}},
        }
    },
)
async def consultar_chat_stream(
    consulta: ConsultaChat,
) -> StreamingResponse:
    """Simula progreso y respuesta, sin consultar herramientas ni IA."""

    async def generar_eventos() -> AsyncIterator[str]:
        yield formar_evento(
            "paso",
            PasoChat(
                id="demo-1",
                texto="Preparando ejemplo",
                detalle="Paso simulado para probar la interfaz.",
                estado="en_curso",
            ),
        )

        await asyncio.sleep(0.5)

        yield formar_evento(
            "paso",
            PasoChat(
                id="demo-1",
                texto="Preparando ejemplo",
                detalle="La preparación simulada terminó.",
                estado="completado",
            ),
        )

        yield formar_evento(
            "respuesta",
            consultar_chat(consulta),
        )

    return StreamingResponse(
        generar_eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )