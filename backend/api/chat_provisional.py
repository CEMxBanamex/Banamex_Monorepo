"""Borrador de contrato del chat: respuestas fijas, sin IA ni base de datos."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

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