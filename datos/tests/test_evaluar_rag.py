"""evaluar_rag.py --sin-bd reproduce buscar_politicas en memoria (para calibrar sin PostgreSQL)."""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _correr(*args):
    env = {**os.environ, "EMBEDDING_PROVEEDOR": "falso"}
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "evaluar_rag.py"), "--sin-bd", *args],
                       capture_output=True, text=True, env=env, check=True)
    return r.stdout


def test_evaluar_sin_bd():
    salida = _correr()
    assert "acierto@1" in salida and "27 preguntas" in salida


def test_calibrar_sin_bd_recomienda_umbral():
    salida = _correr("--calibrar")
    assert "RAG_UMBRAL_SIMILITUD=" in salida and "6 sin política" in salida
