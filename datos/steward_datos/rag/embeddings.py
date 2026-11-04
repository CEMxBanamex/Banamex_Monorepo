"""Embeddings para el RAG. El modelo es el mismo al indexar y al consultar (README · Modelos e inferencia)."""
import hashlib
import math
import re

import httpx

from .. import config
from ..reglas.normalizar import sin_acentos


class ErrorEmbeddings(RuntimeError):
    pass


def nombre_modelo() -> str:
    return "falso-hash" if config.EMBEDDING_PROVEEDOR == "falso" else config.EMBEDDING_MODELO


def embeber(textos: list[str], lote: int = 16) -> list[list[float]]:
    if config.EMBEDDING_PROVEEDOR == "falso":
        return [_falso(t) for t in textos]
    vectores = []
    with httpx.Client(base_url=config.OLLAMA_URL, timeout=120) as cliente:
        for i in range(0, len(textos), lote):
            r = cliente.post("/api/embed", json={"model": config.EMBEDDING_MODELO, "input": textos[i:i + lote]})
            if r.status_code != 200:
                raise ErrorEmbeddings(f"Ollama respondió {r.status_code}: {r.text[:200]}")
            vectores.extend(r.json()["embeddings"])
    if vectores and len(vectores[0]) != config.EMBEDDING_DIM:
        raise ErrorEmbeddings(f"El modelo {config.EMBEDDING_MODELO} da vectores de {len(vectores[0])} dimensiones, "
                              f"pero la tabla espera {config.EMBEDDING_DIM}. Ajusta EMBEDDING_DIM y crea una migración.")
    return vectores


_VACIAS = set("de la el los las y o a en del al que se por con para un una es no su sus lo como si este esta".split())


def _falso(texto: str) -> list[float]:
    """Solo para pruebas sin GPU: bolsa de palabras y bigramas con hashing. Determinista y normalizado."""
    palabras = [w for w in re.findall(r"[a-z0-9ñ\-]+", sin_acentos(texto.lower())) if w not in _VACIAS]
    v = [0.0] * config.EMBEDDING_DIM
    for t in palabras + [f"{a} {b}" for a, b in zip(palabras, palabras[1:])]:
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        v[h % config.EMBEDDING_DIM] += 1.0 if " " not in t else 0.5
    norma = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norma for x in v]
