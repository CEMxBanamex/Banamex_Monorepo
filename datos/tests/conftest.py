import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("EMBEDDING_PROVEEDOR", "falso")
if os.getenv("DATABASE_URL_PRUEBAS"):
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_PRUEBAS"]  # antes de importar steward_datos.config


def pytest_collection_modifyitems(config, items):
    if os.getenv("DATABASE_URL_PRUEBAS"):
        return
    salto = pytest.mark.skip(reason="Define DATABASE_URL_PRUEBAS (una base desechable con pgvector) para las pruebas de integración")
    for item in items:
        if "bd" in item.keywords:
            item.add_marker(salto)


def pytest_configure(config):
    config.addinivalue_line("markers", "bd: requiere PostgreSQL con pgvector (DATABASE_URL_PRUEBAS)")
