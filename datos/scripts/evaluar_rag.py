"""Prueba de calidad del RAG (tarea 3.1.3): acierto en el top-1 y top-k y MRR por pregunta.

Uso:  python scripts/evaluar_rag.py [--k 5] [--fecha 2026-11-02]
Requiere la semilla cargada con --embeddings y el mismo modelo de embeddings configurado.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.contratos import BuscarPoliticasEntrada  # noqa: E402
from steward_datos.db.sesion import sesion  # noqa: E402
from steward_datos.rag.embeddings import nombre_modelo  # noqa: E402
from steward_datos.tools.buscar_politicas import buscar_politicas  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--fecha", type=date.fromisoformat, default=date(2026, 11, 2))
    ap.add_argument("--preguntas", type=Path, default=RAIZ / "evaluacion" / "preguntas_rag.yaml")
    args = ap.parse_args()
    preguntas = yaml.safe_load(args.preguntas.read_text(encoding="utf-8"))["preguntas"]
    top1 = topk = 0
    rr = 0.0
    with sesion() as s:
        for p in preguntas:
            fecha = p.get("fecha", args.fecha)
            fecha = date.fromisoformat(str(fecha))
            r = buscar_politicas(BuscarPoliticasEntrada(consulta=p["pregunta"], k=args.k, fecha=fecha, tipo=p.get("tipo")), s)
            esp = p["esperado"]
            pos = next((i for i, f in enumerate(r.fragmentos)
                        if f.politica_id == esp["politica"] and f.version == esp["version"]), None)
            top1 += pos == 0
            topk += pos is not None
            rr += 1 / (pos + 1) if pos is not None else 0
            marca = "✓" if pos == 0 else (f"@{pos + 1}" if pos is not None else "✗")
            primero = f"{r.fragmentos[0].politica_id} v{r.fragmentos[0].version} · {r.fragmentos[0].seccion}" if r.fragmentos else "(sin resultados)"
            print(f"{marca:>3}  {p['pregunta'][:70]:<70}  -> {primero}")
    n = len(preguntas)
    print(f"\nModelo: {nombre_modelo()}  ·  {n} preguntas  ·  acierto@1 {top1 / n:.0%}  ·  acierto@{args.k} {topk / n:.0%}  ·  MRR {rr / n:.2f}")


if __name__ == "__main__":
    main()
