"""Evaluación contra los casos de referencia (tareas 4.3.1, 4.3.2 y 4.3.3).

Entrada: un archivo de predicciones en JSON Lines, una línea por caso procesado por el sistema:
  {"archivo": "piloto_001.png", "campos": {"total": "12,000.00", ...}, "resultado": "rechazado",
   "reglas": ["R-014"], "segundos": 41.2}
(procesar_caso() puede escribirlo; también se puede armar desde la tabla casos con --desde-bd).

Salida: precisión de extracción por campo, aciertos de clasificación con matriz de confusión,
precisión y exhaustividad por regla, y tiempos comparados con la línea base manual (CSV opcional).

Uso:
  python scripts/evaluar.py --predicciones pred.jsonl [--linea-base evaluacion/linea_base_manual.csv] [--salida reporte.md]
  python scripts/evaluar.py --referencia          # predicciones = verdad de referencia + motor (debe dar 100 %)
"""
import argparse
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.reglas import normalizar as n  # noqa: E402
from steward_datos.reglas.motor import validar_factura  # noqa: E402
from steward_datos.sinteticos import anotaciones, contexto_para, factura_desde_anotacion  # noqa: E402

CAMPOS = ["folio", "fecha", "emisor_nombre", "emisor_rfc", "receptor_nombre", "receptor_rfc", "moneda",
          "subtotal", "impuestos", "total"]
RESULTADOS = ["aceptado", "rechazado", "humana"]


def iguales(campo: str, esperado, obtenido) -> bool:
    if n.vacio(esperado):
        return n.vacio(obtenido)
    if n.vacio(obtenido):
        return False
    if campo in ("subtotal", "impuestos", "total", "retenciones"):
        return n.monto(esperado) == n.monto(obtenido)
    if campo == "fecha":
        return n.fecha(esperado) is not None and n.fecha(esperado) == n.fecha(obtenido)
    if campo.endswith("rfc"):
        return n.rfc_normalizado(esperado) == n.rfc_normalizado(obtenido)
    limpio = lambda s: " ".join(n.sin_acentos(str(s)).lower().replace(",", " ").replace(".", " ").split())
    return limpio(esperado) == limpio(obtenido)


def predicciones_referencia() -> list[dict]:
    out = []
    for d in anotaciones("evaluacion"):
        f = factura_desde_anotacion(d)
        r = validar_factura(d["archivo"], f, contexto_para(d))
        out.append({"archivo": d["archivo"], "campos": {k: c.valor for k, c in f.campos.items()},
                    "resultado": r.resultado_sugerido, "reglas": sorted({h.regla_id for h in r.hallazgos})})
    return out


def evaluar(pred: list[dict], linea_base: dict[str, float] | None) -> str:
    verdad = {d["archivo"]: d for d in anotaciones("evaluacion")}
    pred = [p for p in pred if p["archivo"] in verdad]
    faltan = sorted(set(verdad) - {p["archivo"] for p in pred})
    L = ["# Evaluación contra casos de referencia\n", f"Casos evaluados: {len(pred)} de {len(verdad)}"
         + (f" (sin predicción: {', '.join(faltan)})" if faltan else "") + "\n"]

    # 4.3.1 extracción por campo
    aciertos, totales = Counter(), Counter()
    for p in pred:
        v = verdad[p["archivo"]]["verdad"]["campos"]
        for c in CAMPOS:
            totales[c] += 1
            aciertos[c] += iguales(c, v.get(c), p.get("campos", {}).get(c))
    L.append("## Precisión de extracción por campo\n\n| Campo | Aciertos | Precisión |\n|---|---:|---:|")
    for c in CAMPOS:
        L.append(f"| {c} | {aciertos[c]}/{totales[c]} | {aciertos[c] / max(totales[c], 1):.1%} |")
    tot = sum(aciertos.values()), sum(totales.values())
    L.append(f"| **Todos** | {tot[0]}/{tot[1]} | **{tot[0] / max(tot[1], 1):.1%}** |\n")

    # 4.3.2 clasificación
    matriz = defaultdict(Counter)
    for p in pred:
        matriz[verdad[p["archivo"]]["esperado"]["resultado"]][p.get("resultado")] += 1
    bien = sum(matriz[r][r] for r in RESULTADOS)
    L.append(f"## Clasificación de casos\n\nAciertos: **{bien}/{len(pred)} ({bien / max(len(pred), 1):.1%})**\n")
    L.append("| Esperado \\ Obtenido | " + " | ".join(RESULTADOS) + " | otro |\n|---|" + "---:|" * 4)
    for r in RESULTADOS:
        otro = sum(v for k, v in matriz[r].items() if k not in RESULTADOS)
        L.append(f"| {r} | " + " | ".join(str(matriz[r][o]) for o in RESULTADOS) + f" | {otro} |")
    peligrosos = [p["archivo"] for p in pred if p.get("resultado") == "aceptado" and verdad[p["archivo"]]["esperado"]["resultado"] != "aceptado"]
    L.append(f"\nFalsos aceptados (el error más grave): **{len(peligrosos)}**" + (f" → {', '.join(peligrosos)}" if peligrosos else "") + "\n")

    # Reglas
    tp, fp, fn = Counter(), Counter(), Counter()
    for p in pred:
        esp, obt = set(verdad[p["archivo"]]["esperado"]["reglas"]), set(p.get("reglas", []))
        for r in esp & obt:
            tp[r] += 1
        for r in obt - esp:
            fp[r] += 1
        for r in esp - obt:
            fn[r] += 1
    L.append("## Detección por regla\n\n| Regla | VP | FP | FN | Precisión | Exhaustividad |\n|---|---:|---:|---:|---:|---:|")
    for r in sorted(set(tp) | set(fp) | set(fn)):
        prec = tp[r] / (tp[r] + fp[r]) if tp[r] + fp[r] else 0
        rec = tp[r] / (tp[r] + fn[r]) if tp[r] + fn[r] else 0
        L.append(f"| {r} | {tp[r]} | {fp[r]} | {fn[r]} | {prec:.0%} | {rec:.0%} |")

    # 4.3.3 tiempos
    seg = [p["segundos"] for p in pred if p.get("segundos") is not None]
    if seg or linea_base:
        L.append("\n## Tiempos\n")
        if seg:
            L.append(f"Con agente: mediana {statistics.median(seg):.1f} s, media {statistics.mean(seg):.1f} s ({len(seg)} casos)")
        if linea_base:
            comunes = [a for a in linea_base if a in {p['archivo'] for p in pred}]
            L.append(f"Línea base manual: mediana {statistics.median(linea_base.values()):.1f} s ({len(linea_base)} casos)")
            pares = [(linea_base[a], next(p["segundos"] for p in pred if p["archivo"] == a)) for a in comunes
                     if next(p.get("segundos") for p in pred if p["archivo"] == a) is not None]
            if pares:
                ahorro = 1 - sum(b for _, b in pares) / sum(a for a, _ in pares)
                L.append(f"Mismos casos con y sin agente: {len(pares)} · ahorro de tiempo total {ahorro:.0%}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--predicciones", type=Path)
    g.add_argument("--referencia", action="store_true")
    ap.add_argument("--linea-base", type=Path, help="CSV con columnas archivo,segundos_manual (y opcionalmente errores_encontrados)")
    ap.add_argument("--salida", type=Path)
    args = ap.parse_args()
    pred = predicciones_referencia() if args.referencia else [json.loads(linea) for linea in args.predicciones.read_text(encoding="utf-8").splitlines() if linea.strip()]
    base = None
    if args.linea_base:
        with open(args.linea_base, encoding="utf-8") as fh:
            base = {r["archivo"]: float(r["segundos_manual"]) for r in csv.DictReader(fh) if r.get("segundos_manual")}
    reporte = evaluar(pred, base)
    print(reporte)
    if args.salida:
        args.salida.write_text(reporte, encoding="utf-8")


if __name__ == "__main__":
    main()
