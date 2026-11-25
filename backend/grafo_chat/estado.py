"""Estado compartido del grafo de chat S3-15."""

from typing import Any, Literal, TypedDict

DominioChat = Literal[
    "gobernanza",
    "casos",
    "analista",
    "general",
    "fuera_de_alcance",
]

DominioEjecutable = Literal[
    "gobernanza",
    "casos",
    "analista",
]

RolUsuario = Literal["analista", "administrador"]


class EstadoChat(TypedDict, total=False):
    """Estado que circula entre los nodos del grafo."""

    pregunta: str
    historial: list[dict[str, Any]]
    usuario_id: str
    rol: RolUsuario
    caso_id: str | None

    dominio: DominioChat
    dominios_objetivo: list[DominioEjecutable]
    dominios_ejecutados: list[DominioEjecutable]

    resultados_dominio: list[dict[str, Any]]

    respuesta: str
    fuentes: list[str]
    simulado: bool

    pasos: list[dict[str, Any]]
