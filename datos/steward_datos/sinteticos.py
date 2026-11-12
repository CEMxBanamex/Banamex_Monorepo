"""Lectura de los datos sintéticos generados por db/semillas/generar_*.py."""
import csv
import json
from datetime import date
from pathlib import Path
from typing import Iterator

from .config import CARPETA_SINTETICOS
from .contratos import Antecedente, CampoLeido, ConceptoLeido, FacturaExtraida
from .reglas.motor import Contexto


def anotaciones(grupo: str | None = None, base: Path = CARPETA_SINTETICOS) -> Iterator[dict]:
    grupos = [grupo] if grupo else ["historico", "evaluacion", "demo"]
    for g in grupos:
        for ruta in sorted((base / "facturas" / g).glob("*.json")):
            d = json.loads(ruta.read_text(encoding="utf-8"))
            d["_ruta_archivo"] = ruta.with_name(d["archivo"])
            yield d


def factura_desde_anotacion(d: dict, simular_lectura: bool = True) -> FacturaExtraida:
    """La salida que daría un extractor perfecto (con la confianza y las lecturas erróneas simuladas)."""
    v = d["verdad"]
    lectura = d.get("lectura_simulada", {}) if simular_lectura else {}
    conf = d.get("confianza_simulada", {}) if simular_lectura else {}
    campos = {}
    for k, valor in v["campos"].items():
        if valor is None:
            continue
        bbox = None
        for clase, campo in (("NUMBER", "folio"), ("DATE", "fecha"), ("SUB_TOTAL", "subtotal"), ("TAX", "impuestos"), ("TOTAL", "total")):
            if campo == k and clase in d.get("anotacion_fatura", {}):
                bbox = d["anotacion_fatura"][clase]["bbox"][0]
        campos[k] = CampoLeido(valor=lectura.get(k, valor), confianza=conf.get(k, 99), pagina=1, bbox=bbox)
    return FacturaExtraida(
        tipo_documento=v["tipo_documento"], campos=campos,
        conceptos=[ConceptoLeido(**c) for c in v["conceptos"]],
        texto_completo=d.get("texto_completo"), modelo="verdad-de-referencia", paginas=d.get("paginas", 1),
    )


def catalogos(base: Path = CARPETA_SINTETICOS) -> tuple[set[str], set[str]]:
    with open(base / "catalogos" / "proveedores.csv", encoding="utf-8") as fh:
        prov = {r["rfc"] for r in csv.DictReader(fh) if r["activo"] == "true"}
    with open(base / "catalogos" / "entidades_receptoras.csv", encoding="utf-8") as fh:
        ent = {r["rfc"] for r in csv.DictReader(fh)}
    return prov, ent


def antecedentes_historicos(base: Path = CARPETA_SINTETICOS) -> list[Antecedente]:
    return [Antecedente(caso_id=d["caso_id"], emisor_rfc=d["verdad"]["campos"]["emisor_rfc"],
                        folio=d["verdad"]["campos"]["folio"], sha256=d["sha256"])
            for d in anotaciones("historico", base)]


def contexto_para(d: dict, base: Path = CARPETA_SINTETICOS) -> Contexto:
    prov, ent = catalogos(base)
    return Contexto(proveedores_activos=prov, entidades_receptoras=ent,
                    antecedentes=antecedentes_historicos(base) if d["grupo"] != "historico" else [],
                    sha256=d["sha256"], fecha_recepcion=date.fromisoformat(d["fecha_recepcion"]))


def leer_tabla(ruta: Path):
    """Lectura mínima de .xlsx/.csv a TablaRegistros (referencia para leer_pdf_o_excel). Lanza ValueError si no se puede leer."""
    import pandas as pd
    from .contratos import TablaRegistros
    ruta = Path(ruta)
    try:
        if ruta.suffix.lower() in (".xlsx", ".xls"):
            hojas = pd.read_excel(ruta, sheet_name=None, dtype=str)
            hoja, df = next(iter(hojas.items()))
        else:
            df, hoja = pd.read_csv(ruta, dtype=str, encoding="utf-8"), None
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"No se pudo leer {ruta.name}: {e}") from e
    return TablaRegistros(archivo=ruta.name, hoja=hoja, columnas=[str(c) for c in df.columns],
                          filas=[{str(k): (None if pd.isna(v) else str(v)) for k, v in fila.items()} for fila in df.to_dict("records")])


def registros(base: Path = CARPETA_SINTETICOS) -> Iterator[dict]:
    for ruta in sorted((base / "registros").glob("*.json")):
        d = json.loads(ruta.read_text(encoding="utf-8"))
        d["_ruta_archivo"] = ruta.with_name(d["archivo"])
        yield d
