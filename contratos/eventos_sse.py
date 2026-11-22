
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EstadoPaso(str, Enum):
    PENDIENTE = "pendiente"
    EN_CURSO = "en_curso"
    COMPLETADO = "completado"
    ERROR = "error"


class TipoRespuesta(str, Enum):
    DATOS = "datos"
    POLITICAS = "politicas"
    INFORMACION_GENERAL = "informacion_general"
    MIXTA = "mixta"


class PasoEvent(BaseModel):
    """Evento que representa el progreso de un paso del agente."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    texto: str = Field(min_length=1)
    detalle: str | None = None
    estado: EstadoPaso


class RespuestaEvent(BaseModel):
    """Evento que contiene la respuesta final del asistente."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    respuesta: str = Field(min_length=1)
    caso_id: str | None = None
    simulado: bool = False
    duracion_ms: int | None = Field(default=None, ge=0)
    tipo: TipoRespuesta
    fuentes: list[str] = Field(default_factory=list)


EventoSSE = PasoEvent | RespuestaEvent
