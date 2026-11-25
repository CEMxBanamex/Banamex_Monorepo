"""Borrador de contrato del chat: respuestas fijas, sin IA ni base de datos."""



from fastapi import APIRouter
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
