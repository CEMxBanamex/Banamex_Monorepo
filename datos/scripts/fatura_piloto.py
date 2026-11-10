"""Selección del subconjunto piloto de FATURA y conversión de sus anotaciones a nuestro formato (tareas 0.4.1 y 0.4.2).

1. Descarga FATURA desde Zenodo (https://zenodo.org/records/10371464, ~360 MB) y descomprímela.
2. python scripts/fatura_piloto.py revisar  --fatura /ruta/a/FATURA
      Cuenta imágenes, plantillas y frecuencia de clases (sirve para documentar 0.4.1).
3. python scripts/fatura_piloto.py seleccionar --fatura /ruta/a/FATURA --por-plantilla 2
      Elige N imágenes por plantilla (estratificado, con semilla fija), copia imagen + anotación convertida
      a datos/sinteticos/fatura_piloto/ y escribe seleccion.csv.

Las facturas de FATURA no son CFDI: no traen RFC del receptor ni moneda, así que se usan para medir la
extracción por campo (4.3.1). Las reglas se miden con nuestras facturas sintéticas (casos_referencia_*.json).
"""
import argparse
import csv
import json
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.config import CARPETA_SINTETICOS  # noqa: E402

# Clase FATURA (normalizada) -> campo nuestro
MAPA = {
    "NUMBER": "folio", "DATE": "fecha", "SELLER_NAME": "emisor_nombre", "SELLER_ADDRESS": "emisor_direccion",
    "GST": "emisor_rfc", "BUYER": "receptor_nombre", "BILL_TO": "receptor_nombre", "SUB_TOTAL": "subtotal",
    "TAX": "impuestos", "TOTAL": "total", "CONDITIONS": "condiciones_pago", "DUE_DATE": "fecha_vencimiento",
    "DISCOUNT": "descuento", "AMOUNT_DUE": "saldo", "PO_NUMBER": "orden_compra",
}


def clase(nombre: str) -> str:
    return re.sub(r"[\s\-]+", "_", str(nombre).strip().upper())


def instancias(raiz: Path) -> list[tuple[Path, Path]]:
    """Empareja cada imagen con su anotación en formato original (busca la carpeta sin importar el nombre exacto)."""
    imagenes = {p.stem: p for p in raiz.rglob("*.jpg")}
    anotaciones = {}
    for p in raiz.rglob("*.json"):
        ruta = str(p).lower()
        if "coco" in ruta or "hf" in ruta or "layoutlm" in ruta or "split" in ruta:
            continue
        anotaciones.setdefault(p.stem, p)
    return [(imagenes[k], anotaciones[k]) for k in sorted(imagenes) if k in anotaciones]


def objetos(crudo) -> list[tuple[str, str, list]]:
    """Devuelve (clase, texto, bbox) para las formas de anotación que hemos visto o esperamos."""
    out = []
    if isinstance(crudo, dict):
        for k, v in crudo.items():
            if isinstance(v, dict) and ("text" in v or "bbox" in v):
                out.append((clase(k), v.get("text", ""), v.get("bbox")))
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                for o in v:
                    out.append((clase(o.get("label") or o.get("class") or k), o.get("text", ""), o.get("bbox") or o.get("box")))
            elif isinstance(v, str):
                out.append((clase(k), v, None))
    elif isinstance(crudo, list):
        for o in crudo:
            if isinstance(o, dict):
                out.append((clase(o.get("label") or o.get("class") or o.get("category", "")), o.get("text", ""), o.get("bbox") or o.get("box")))
    return out


def convertir(img: Path, ann: Path) -> dict:
    crudo = json.loads(ann.read_text(encoding="utf-8"))
    campos, cajas = {}, {}
    for c, texto, bbox in objetos(crudo):
        if isinstance(texto, list):
            texto = " ".join(map(str, texto))
        cajas.setdefault(c, {"text": texto, "bbox": bbox})
        if c in MAPA and MAPA[c] not in campos:
            campos[MAPA[c]] = str(texto).strip() or None
    m = re.match(r"(Template\d+)", img.stem, re.IGNORECASE)
    return {
        "archivo": img.name, "grupo": "fatura", "caso_id": None, "escenario": "fatura", "plantilla": m.group(1) if m else "desconocida",
        "verdad": {"tipo_documento": "factura", "campos": campos, "normalizados": {}, "conceptos": []},
        "anotacion_fatura": cajas, "esperado": {"resultado": None, "reglas": []},
        "fuente": "FATURA (Limam, Dhiaf y Kessentini, 2023), CC BY 4.0",
    }


def revisar(args):
    pares = instancias(args.fatura)
    plantillas = Counter(re.match(r"(Template\d+)", i.stem, re.I).group(1) if re.match(r"Template\d+", i.stem, re.I) else "?" for i, _ in pares)
    clases = Counter()
    for _, a in pares[: args.muestra]:
        clases.update({c for c, _, _ in objetos(json.loads(a.read_text(encoding="utf-8")))})
    print(f"Imágenes con anotación: {len(pares)}  ·  plantillas: {len(plantillas)}")
    print(f"Frecuencia de clases (en {min(args.muestra, len(pares))} anotaciones):")
    for c, n in clases.most_common():
        print(f"  {c:<18} {n:>6}  -> {MAPA.get(c, '(no se usa)')}")


def seleccionar(args):
    pares = instancias(args.fatura)
    if not pares:
        sys.exit("No encontré pares imagen/anotación. Revisa la ruta de --fatura.")
    rnd = random.Random(args.semilla)
    por_plantilla = defaultdict(list)
    for img, ann in pares:
        m = re.match(r"(Template\d+)", img.stem, re.I)
        por_plantilla[m.group(1) if m else "?"].append((img, ann))
    salida = args.salida
    salida.mkdir(parents=True, exist_ok=True)
    filas = []
    for plantilla in sorted(por_plantilla, key=lambda s: int(re.sub(r"\D", "", s) or 0)):
        for img, ann in rnd.sample(por_plantilla[plantilla], min(args.por_plantilla, len(por_plantilla[plantilla]))):
            shutil.copy(img, salida / img.name)
            d = convertir(img, ann)
            (salida / f"{img.stem}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            filas.append({"archivo": img.name, "plantilla": plantilla,
                          "campos_con_verdad": sum(v is not None for v in d["verdad"]["campos"].values())})
    with open(salida / "seleccion.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["archivo", "plantilla", "campos_con_verdad"])
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} facturas de {len(por_plantilla)} plantillas copiadas a {salida}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    a = sub.add_parser("revisar")
    a.add_argument("--fatura", type=Path, required=True)
    a.add_argument("--muestra", type=int, default=2000)
    a.set_defaults(fn=revisar)
    b = sub.add_parser("seleccionar")
    b.add_argument("--fatura", type=Path, required=True)
    b.add_argument("--por-plantilla", type=int, default=2)
    b.add_argument("--semilla", type=int, default=2026)
    b.add_argument("--salida", type=Path, default=CARPETA_SINTETICOS / "fatura_piloto")
    b.set_defaults(fn=seleccionar)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
