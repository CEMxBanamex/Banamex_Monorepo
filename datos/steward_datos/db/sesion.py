from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import DATABASE_URL

_motor = None
_fabrica = None


def motor():
    global _motor, _fabrica
    if _motor is None:
        _motor = create_engine(DATABASE_URL, pool_pre_ping=True)
        _fabrica = sessionmaker(_motor, expire_on_commit=False)
    return _motor


@contextmanager
def sesion() -> Session:
    motor()
    s = _fabrica()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def siguiente_id_caso(s: Session, tipo: str) -> str:
    """F-1043 para facturas, V-0208 para validaciones, a partir de secuencias de la base."""
    from sqlalchemy import text
    if tipo == "factura":
        n = s.execute(text("SELECT nextval('seq_casos_factura')")).scalar_one()
        return f"F-{n:04d}"
    n = s.execute(text("SELECT nextval('seq_casos_validacion')")).scalar_one()
    return f"V-{n:04d}"
