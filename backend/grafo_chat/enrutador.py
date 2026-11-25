"""Enrutador determinista para el grafo de chat S3-15."""

import re
import unicodedata
from typing import Any

from .estado import DominioChat, EstadoChat

PALABRAS_GOBERNANZA = (
    "politica",
    "politicas",
    "glosario",
    "catalogo",
    "calidad de datos",
    "regla de calidad",
    "reglas de calidad",
    "data owner",
    "propietario de datos",
    "data steward",
    "regla de negocio",
    "completitud",
    "unicidad",
    "validez",
    "oportunidad",
    "politica vigente",
    "clasificacion de la informacion",
    "enmascaramiento",
    "bitacora de auditoria",
    "confianza de lectura",
    "proveedor activo",
    "padron de proveedores",
    "entidad receptora",
    "centro de costo",
    "factura conciliada",
    "monto facturado",
    "tasa de rechazo",
    "tasa de conciliacion",
    "tiempo de revision",
    "resultado sugerido",
    "revision humana",
    "hallazgo",
    "dato personal",
    "factura extemporanea",
    # Preguntas del guion de la demo (datos/evaluacion/preguntas_demo.yaml).
    "rfc",
    "asteriscos",
    "enmascarado",
    "enmascarada",
    "calidad",
    "dueno",
    "datos personales",
)

PALABRAS_CASOS = (
    "caso",
    "casos",
    "bitacora",
    "expediente",
    "expedientes",
    "factura",
    "facturas",
)

# Un folio de caso (F-1042, V-0207) manda la pregunta a casos aunque mencione términos de gobernanza.
PATRON_FOLIO = re.compile(r"(?<!\w)[fv]-\d{4,}(?!\w)")

PALABRAS_FUERA_ALCANCE = (
    "pronostico del clima",
    "receta de cocina",
    "resultado de futbol",
)


def _normalizar(texto: str) -> str:
    """Convierte el texto a minúsculas y elimina los acentos."""
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
        ) is not None
        for palabra in palabras
    )


def clasificar_dominio(estado: EstadoChat) -> dict[str, Any]:
    """Clasifica cada pregunta en un único dominio."""

    pregunta = estado.get("pregunta")

    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser texto no vacío.")

    pregunta = _normalizar(pregunta.strip())

    if _contiene_alguna(pregunta, PALABRAS_FUERA_ALCANCE):
        dominio: DominioChat = "fuera_de_alcance"

    elif PATRON_FOLIO.search(pregunta):
        dominio = "casos"

    elif _contiene_alguna(pregunta, PALABRAS_GOBERNANZA):
        dominio = "gobernanza"

    elif _contiene_alguna(pregunta, PALABRAS_CASOS):
        dominio = "casos"

    else:
        dominio = "general"

    dominios = (
        [dominio]
        if dominio in ("gobernanza", "casos")
        else []
    )

    return {
        "dominio": dominio,
        "dominios_objetivo": dominios,
        "dominios_ejecutados": [],
    }
