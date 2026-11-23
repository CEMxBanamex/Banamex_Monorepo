"""Consultas de Mauricio con autorización por vistas y transacciones de solo lectura."""
from contextlib import contextmanager

from pydantic import ConfigDict, Field, model_validator
from sqlalchemy import text

from ..contexto import fijar_en_bd, requerir_usuario
from ..contratos import BuscarFacturasEntrada, BuscarFacturasSalida, CasoOut, FacturaResumen
from ..db.sesion import sesion
from .consultas_chat import consultar_caso as leer_detalle


class CasoNoDisponible(ValueError):
    pass


class FiltrosFacturas(BuscarFacturasEntrada):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    emisor: str | None = Field(None, max_length=200)
    folio: str | None = Field(None, max_length=100)
    moneda: str | None = Field(None, min_length=3, max_length=3)
    con_regla: str | None = Field(None, pattern=r"^[Rr]-[0-9]{3}$")
    total_min: float | None = Field(None, ge=0)
    total_max: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def validar_rangos(self):
        if self.fecha_desde and self.fecha_hasta and self.fecha_desde > self.fecha_hasta:
            raise ValueError("La fecha inicial no puede superar la final")
        if self.total_min is not None and self.total_max is not None and self.total_min > self.total_max:
            raise ValueError("El importe mínimo no puede superar el máximo")
        return self


@contextmanager
def sesion_autorizada(usuario=None):
    usuario = requerir_usuario(usuario)
    with sesion() as s:
        s.execute(text("SET TRANSACTION READ ONLY"))
        fijar_en_bd(s, usuario)
        yield s


def consultar_caso(caso_id: str, usuario=None) -> CasoOut:
    identificador = caso_id.strip().upper()
    if not identificador or len(identificador) > 100:
        raise ValueError("Identificador de caso inválido")
    with sesion_autorizada(usuario) as s:
        permitido = s.execute(
            text("SELECT caso_id FROM v_casos WHERE caso_id = :id"), {"id": identificador}
        ).scalar_one_or_none()
        if permitido is None:
            raise CasoNoDisponible("CASO_NO_DISPONIBLE: caso inexistente o sin acceso")
        # La vista autoriza primero; el detalle se recupera en la misma transacción.
        # No existe una vista que incluya campos extraídos y evidencia completa.
        return leer_detalle(identificador, s=s)


ORDENES = {
    "fecha_desc": "f.fecha_emision DESC NULLS LAST",
    "fecha_asc": "f.fecha_emision ASC NULLS LAST",
    "total_desc": "f.total DESC NULLS LAST",
    "total_asc": "f.total ASC NULLS LAST",
}


def _patron(valor):
    return "%" + valor.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"


def buscar_facturas(entrada: FiltrosFacturas, usuario=None) -> BuscarFacturasSalida:
    entrada = FiltrosFacturas.model_validate(entrada.model_dump())
    filtros = []
    parametros = {"limite": entrada.limite}
    if entrada.emisor:
        filtros.append("(f.proveedor ILIKE :emisor ESCAPE '!' OR f.proveedor_rfc ILIKE :emisor ESCAPE '!')")
        parametros["emisor"] = _patron(entrada.emisor)
    if entrada.folio:
        filtros.append("f.folio ILIKE :folio ESCAPE '!'")
        parametros["folio"] = _patron(entrada.folio)
    for nombre, columna, operador in (
        ("fecha_desde", "fecha_emision", ">="), ("fecha_hasta", "fecha_emision", "<="),
        ("total_min", "total", ">="), ("total_max", "total", "<="),
        ("moneda", "moneda", "="), ("resultado", "resultado", "="), ("estado", "estado", "="),
    ):
        valor = getattr(entrada, nombre)
        if valor is not None:
            filtros.append(f"f.{columna} {operador} :{nombre}")
            parametros[nombre] = valor.upper() if nombre == "moneda" else valor
    if entrada.con_regla:
        filtros.append("EXISTS (SELECT 1 FROM v_hallazgos h WHERE h.caso_id=f.caso_id AND h.regla_id=:regla)")
        parametros["regla"] = entrada.con_regla.upper()
    donde = " AND ".join(filtros) or "TRUE"
    # Solo nombres de columnas/operadores internos; todos los valores son parámetros.
    consulta = f"""
        SELECT f.*, ARRAY(SELECT DISTINCT h.regla_id FROM v_hallazgos h
            WHERE h.caso_id=f.caso_id ORDER BY h.regla_id) AS reglas
        FROM v_facturas f WHERE {donde}
        ORDER BY {ORDENES[entrada.orden]}, f.caso_id LIMIT :limite
    """
    with sesion_autorizada(usuario) as s:
        total = s.execute(text(f"SELECT count(*) FROM v_facturas f WHERE {donde}"), parametros).scalar_one()
        filas = s.execute(text(consulta), parametros).mappings().all()
        return BuscarFacturasSalida(total_coincidencias=total, facturas=[
            FacturaResumen(
                caso_id=f["caso_id"], folio=f["folio"], fecha_emision=f["fecha_emision"],
                emisor_nombre=f["proveedor"], emisor_rfc=f["proveedor_rfc"],
                total=float(f["total"]) if f["total"] is not None else None, moneda=f["moneda"],
                estado=f["estado"], resultado_sugerido=f["resultado"], reglas_con_hallazgo=f["reglas"],
            ) for f in filas
        ])
