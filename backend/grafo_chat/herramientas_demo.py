
"""Herramientas falsas para probar el grafo de chat."""

from typing import Any


def buscar_politicas(pregunta: str) -> dict[str, Any]:
    """Simula una búsqueda de políticas de gobernanza."""
    return {
        "dominio": "gobernanza",
        "respuesta": (
            "Se encontraron políticas de demostración "
            "relacionadas con la consulta."
        ),
        "fuentes": ["politicas_demo"],
    }


def consultar_datos(pregunta: str) -> dict[str, Any]:
    """Simula una consulta de datos e indicadores."""
    return {
        "dominio": "consultas",
        "respuesta": (
            "Se obtuvo un resultado de demostración "
            "para la consulta de datos."
        ),
        "fuentes": ["datos_demo"],
    }


def consultar_casos(pregunta: str) -> dict[str, Any]:
    """Simula la consulta de un caso y su bitácora."""
    return {
        "dominio": "casos",
        "respuesta": (
            "Se encontró información de demostración "
            "para el caso solicitado."
        ),
        "fuentes": ["casos_demo"],
    }


def responder_general(pregunta: str) -> dict[str, Any]:
    """Simula una respuesta de información general."""
    return {
        "dominio": "general",
        "respuesta": (
            "Todavía no sé responder esa pregunta. Puedo ayudarte con políticas, "
            "glosario y calidad de datos (por ejemplo, \"¿Qué significa factura "
            "conciliada?\"), y con casos y facturas (por ejemplo, \"¿Por qué se "
            "rechazó la factura F-0936?\")."
        ),
        "fuentes": [],
    }


def responder_fuera_alcance(pregunta: str) -> dict[str, Any]:
    """Devuelve una respuesta fija fuera del alcance."""
    return {
        "dominio": "fuera_de_alcance",
        "respuesta": (
            "Lo siento, esta solicitud está fuera "
            "del alcance del Data Steward."
        ),
        "fuentes": [],
    }
