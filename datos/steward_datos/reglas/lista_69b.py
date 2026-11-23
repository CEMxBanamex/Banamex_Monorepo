"""Lista de contribuyentes del artículo 69-B del CFF (operaciones inexistentes), para la regla R-019.

El SAT la publica como CSV. Aquí se usa una lista de prueba con RFC sintéticos (reglas/lista_69b.csv);
en producción se reemplaza con la descarga del SAT definiendo RUTA_LISTA_69B.
"""
import csv
import os
from pathlib import Path
from typing import Optional

from .. import config
from . import normalizar as n

SITUACIONES = {"presunto", "definitivo", "desvirtuado", "sentencia_favorable"}


def ruta_lista() -> Path:
    return Path(os.getenv("RUTA_LISTA_69B", config.RAIZ_DATOS / "reglas" / "lista_69b.csv"))


def cargar_lista_69b(ruta: Optional[Path] = None) -> dict[str, str]:
    """RFC normalizado -> situación. Lista vacía si no existe el archivo."""
    ruta = ruta or ruta_lista()
    if not ruta.exists():
        return {}
    out = {}
    with open(ruta, encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            situacion = fila["situacion"].strip().lower()
            if situacion not in SITUACIONES:
                raise ValueError(f"Situación no válida en {ruta.name}: {situacion!r}")
            out[n.rfc_normalizado(fila["rfc"])] = situacion
    return out
