
"""Herramientas falsas para probar el grafo de chat."""

import re
import unicodedata
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


# Saludos y preguntas sobre el propio asistente: se contestan con una presentación fija, sin modelo.
_SALUDOS = re.compile(
    r"(?<!\w)(hola|buen[oa]s? (dias|tardes|noches)|que tal|hey|saludos)(?!\w)"
)
_IDENTIDAD = re.compile(
    r"(quien eres|que eres|como te llamas|que (puedes|sabes) hacer|en que (me )?(puedes|podrias) ayudar"
    r"|para que sirves|como funcionas|(?<!\w)ayuda(?!\w))"
)
_GRACIAS = re.compile(r"(?<!\w)(gracias|muchas gracias|te agradezco)(?!\w)")

PRESENTACION = (
    "Hola, soy el asistente del Data Steward. Puedo explicarte por qué se aceptó o rechazó "
    "una factura (por ejemplo, \"¿Por qué se rechazó la factura F-0936?\"), consultar "
    "políticas, el glosario y la calidad de datos (\"¿Qué significa factura conciliada?\") "
    "y darte métricas como la tasa de rechazo o el monto facturado. Siempre te digo de "
    "dónde sale la respuesta; las decisiones las tomas tú."
)
NO_ENTENDIDA = (
    "Todavía no sé responder esa pregunta. Puedo ayudarte con políticas, glosario y "
    "calidad de datos (por ejemplo, \"¿Qué significa factura conciliada?\"), con casos y "
    "facturas (\"¿Por qué se rechazó la factura F-0936?\") y con métricas como la tasa "
    "de rechazo."
)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.lower().split())


def responder_general(pregunta: str) -> dict[str, Any]:
    """Responde saludos y preguntas sobre el asistente; lo demás, con lo que sí puede responder."""
    texto = _normalizar(pregunta)
    if _IDENTIDAD.search(texto) or _SALUDOS.search(texto):
        respuesta = PRESENTACION
    elif _GRACIAS.search(texto):
        respuesta = "De nada. Si necesitas revisar otro caso o consultar una política, aquí estoy."
    else:
        respuesta = NO_ENTENDIDA
    return {
        "dominio": "general",
        "respuesta": respuesta,
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
