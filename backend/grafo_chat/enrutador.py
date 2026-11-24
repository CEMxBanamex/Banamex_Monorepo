"""Enrutador determinista para el grafo de chat."""

import re
import unicodedata
from typing import Any

from .estado import (
    DominioChat,
    DominioEjecutable,
    EstadoChat,
)


PALABRAS_GOBERNANZA = (
    "politica",
    "politicas",
    "glosario",
    "catalogo",
    "calidad de datos",
    "regla de calidad",
    "reglas de calidad",
)

PALABRAS_CONSULTAS = (
    "metrica",
    "metricas",
    "indicador",
    "indicadores",
    "factura",
    "facturas",
    "consulta",
    "consultas",
    "dato",
    "datos",
    "tabla",
    "tablas",
)

PALABRAS_CASOS = (
    "caso",
    "casos",
    "bitacora",
    "expediente",
    "expedientes",
)
PALABRAS_FUERA_ALCANCE = (
    "pronostico del clima",
    "receta de cocina",
    "resultado de futbol",
)


def _normalizar(texto: str) -> str:
    """Convierte el texto a minusculas y elimina los acentos."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.lower()


def _contiene_alguna(
    pregunta: str,
    palabras: tuple[str, ...],
) -> bool:
    """Comprueba coincidencias de palabras completas o frases."""

    return any(
        re.search(
            rf"(?<!\w){re.escape(palabra)}(?!\w)",
            pregunta,
        )
        is not None
        for palabra in palabras
    )


def clasificar_dominio(estado: EstadoChat) -> dict[str, Any]:
    """Clasifica la pregunta y conserva los dominios objetivo."""

    pregunta = estado.get("pregunta")

    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser texto no vacio.")

    pregunta = _normalizar(pregunta.strip())

    gobernanza = _contiene_alguna(
        pregunta, PALABRAS_GOBERNANZA
    )
    frase_calidad_datos = _contiene_alguna(
    pregunta, ("calidad de datos",)
)

    if frase_calidad_datos:
        palabras_consultas = tuple(
            palabra
            for palabra in PALABRAS_CONSULTAS
            if palabra not in ("dato", "datos")
        )
    else:
        palabras_consultas = PALABRAS_CONSULTAS

    consultas = _contiene_alguna(
        pregunta, palabras_consultas
    )

    casos = _contiene_alguna(
        pregunta, PALABRAS_CASOS
    )

    dominios: list[DominioEjecutable] = []

    if gobernanza:
        dominios.append("gobernanza")

    if consultas:
        dominios.append("consultas")

    if casos:
        dominios.append("casos")

    if _contiene_alguna(pregunta, PALABRAS_FUERA_ALCANCE):
        dominio: DominioChat = "fuera_de_alcance"
        dominios = []

    elif len(dominios) >= 2:
        dominio = "mixta"
        dominios = dominios[:2]

    elif len(dominios) == 1:
        dominio = dominios[0]

    else:
        dominio = "general"

    return {
        "dominio": dominio,
        "dominios_objetivo": dominios,
        "dominios_ejecutados": [],
    }
