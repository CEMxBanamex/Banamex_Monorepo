
"""evaluar_rag.py --sin-bd reproduce buscar_politicas en memoria."""

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _correr(*args):
    env = {
        **os.environ,
        "EMBEDDING_PROVEEDOR": "falso",
        "PYTHONIOENCODING": "utf-8",
    }

    resultado = subprocess.run(
        [
            sys.executable,
            str(RAIZ / "scripts" / "evaluar_rag.py"),
            "--sin-bd",
            *args,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
    )

    return resultado.stdout


def test_evaluar_sin_bd():
    salida = _correr()

    assert "acierto@1" in salida
    assert "acierto@5" in salida
    assert "MRR" in salida


def test_evaluar_calibrar_sin_bd():
    salida = _correr("--calibrar")

    assert "umbral" in salida.lower()
