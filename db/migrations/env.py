from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from steward_datos.config import DATABASE_URL
from steward_datos.db.models import Base

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

# Las tablas de checkpoints de LangGraph (PostgresSaver) no son nuestras; autogenerate las ignora.
TABLAS_AJENAS = {"checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"}


def incluir(obj, nombre, tipo, reflejado, comparado):
    return not (tipo == "table" and nombre in TABLAS_AJENAS)


def run_migrations_offline():
    context.configure(url=DATABASE_URL, target_metadata=Base.metadata, literal_binds=True, include_object=incluir)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    motor = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=Base.metadata, include_object=incluir)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
