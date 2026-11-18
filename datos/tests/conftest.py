import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
REPO = RAIZ.parent  # migraciones en db/migrations/ y semillas en db/semillas/
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


@pytest.fixture(scope="session")
def base_lista():
    """Base desechable: borra el esquema, aplica las migraciones y carga la semilla completa."""
    from sqlalchemy import create_engine, text
    url = os.environ["DATABASE_URL_PRUEBAS"]
    with create_engine(url, isolation_level="AUTOCOMMIT").connect() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    env = {**os.environ, "DATABASE_URL": url, "EMBEDDING_PROVEEDOR": "falso"}
    subprocess.run(["alembic", "-c", str(REPO / "db" / "migrations" / "alembic.ini"), "upgrade", "head"], cwd=REPO, env=env, check=True, capture_output=True)
    subprocess.run([sys.executable, str(REPO / "db" / "semillas" / "cargar_semilla.py"), "--embeddings"], cwd=REPO, env=env, check=True, capture_output=True)
