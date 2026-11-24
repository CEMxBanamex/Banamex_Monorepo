"""Borrador de contrato del chat: respuestas fijas, sin IA ni base de datos."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from contratos.eventos_sse import PasoEvent, RespuestaEvent

router = APIRouter(prefix="/api/chat", tags=["Chat provisional"])


class ConsultaChat(BaseModel):
    """Datos que enviaría la pantalla del chat."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    mensaje: str = Field(min_length=1, max_length=2000)
    caso_id: str | None = Field(default=None, min_length=1, max_length=100)


@router.post("/consulta", response_model=RespuestaEvent)
def consultar_chat(consulta: ConsultaChat) -> RespuestaEvent:
    """Devuelve una respuesta fija para probar el contrato del chat."""

    return RespuestaEvent(
        respuesta=(
            "Esta es una respuesta de prueba del chat. "
            "Todavía no se consultan casos, políticas ni modelos de IA."
        ),
        caso_id=consulta.caso_id,
        simulado=True,
        tipo="informacion_general",
        fuentes=[],
    )


def formar_evento(
    nombre: str,
    contenido: PasoEvent | RespuestaEvent,
) -> str:
    """Convierte los datos al formato de un evento SSE."""

    return f"event: {nombre}\ndata: {contenido.model_dump_json()}\n\n"


class ConversacionChat(BaseModel):
    """Conversación de ejemplo para construir la interfaz."""

    id: str
    titulo: str
    caso_id: str | None
    simulado: bool = True


class MensajeHistorial(BaseModel):
    """Mensaje de ejemplo del historial."""

    id: str
    rol: Literal["usuario", "asistente"]
    contenido: str


class HistorialChat(BaseModel):
    """Historial fijo; no guarda mensajes enviados por el usuario."""

    conversacion_id: str
    mensajes: list[MensajeHistorial]
    simulado: bool = True


@router.get(
    "/conversaciones",
    response_model=list[ConversacionChat],
)
def listar_conversaciones() -> list[ConversacionChat]:
    """Devuelve una conversación ficticia."""

    return [
        ConversacionChat(
            id="demo-conversacion-1",
            titulo="Ejemplo de consulta de un caso",
            caso_id="F-1042",
        )
    ]


@router.get(
    "/conversaciones/{conversacion_id}/mensajes",
    response_model=HistorialChat,
)
def consultar_historial(conversacion_id: str) -> HistorialChat:
    """Devuelve el historial del ejemplo o 404 si no existe."""

    if conversacion_id != "demo-conversacion-1":
        raise HTTPException(
            status_code=404,
            detail="Conversación de ejemplo no encontrada",
        )

    return HistorialChat(
        conversacion_id=conversacion_id,
        mensajes=[
            MensajeHistorial(
                id="demo-mensaje-1",
                rol="usuario",
                contenido="¿Qué información tiene este caso?",
            ),
            MensajeHistorial(
                id="demo-mensaje-2",
                rol="asistente",
                contenido=(
                    "Este historial es ficticio. "
                    "Todavía no se ha consultado información del caso."
                ),
            ),
        ],
    )
