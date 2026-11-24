
"""Estado compartido del grafo de chat."""

from typing import Any, Literal, TypedDict


DominioChat = Literal[
    "gobernanza",
    "consultas",
    "casos",
    "mixta",
    "general",
    "fuera_de_alcance",
]

DominioEjecutable = Literal[
    "gobernanza",
    "consultas",
    "casos",
]

RolUsuario = Literal["analista", "administrador"]


class EstadoChat(TypedDict, total=False):
    """Estado que circula entre los nodos del grafo de chat."""

    # Entrada y contexto de la conversación
    pregunta: str
    historial: list[dict[str, Any]]
    usuario_id: str
    rol: RolUsuario
    caso_id: str | None

    # Enrutamiento
    dominio: DominioChat
    dominios_objetivo: list[DominioEjecutable]
    dominios_ejecutados: list[DominioEjecutable]

    # Resultados de las herramientas falsas
    resultados_dominio: list[dict[str, Any]]

    # Respuesta final
    respuesta: str
    fuentes: list[str]

    # Seguimiento de la ejecución
    pasos: list[dict[str, Any]]
