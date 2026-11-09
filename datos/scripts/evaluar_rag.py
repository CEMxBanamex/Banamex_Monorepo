"""Prueba de calidad del RAG (tarea 3.1.3): acierto en el top-1 y top-k y MRR por pregunta.

Uso:  python scripts/evaluar_rag.py [--k 5] [--fecha 2026-11-02]
      python scripts/evaluar_rag.py --calibrar     # recomienda RAG_UMBRAL_SIMILITUD para el modelo configurado
Requiere la semilla cargada con --embeddings y el mismo modelo de embeddings configurado.
Las preguntas con `esperado: null` no tienen política: deben quedar debajo del umbral.
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.contratos import BuscarPoliticasEntrada  # noqa: E402
from steward_datos.db.sesion import sesion  # noqa: E402
from steward_datos.rag.embeddings import nombre_modelo  # noqa: E402
from steward_datos.tools.buscar_politicas import buscar_politicas, umbral_similitud  # noqa: E402


def _buscar(s, p, k, fecha_defecto):
    fecha = date.fromisoformat(str(p.get("fecha", fecha_defecto)))
    return buscar_politicas(BuscarPoliticasEntrada(consulta=p["pregunta"], k=k, fecha=fecha, tipo=p.get("tipo")), s)


def _posicion(r, esp):
    return next((i for i, f in enumerate(r.fragmentos) if f.politica_id == esp["politica"] and f.version == esp["version"]), None)


def evaluar(preguntas, k, fecha):
    positivas = [p for p in preguntas if p.get("esperado")]
    negativas = [p for p in preguntas if not p.get("esperado")]
    top1 = topk = 0
    rr = 0.0
    with sesion() as s:
        for p in positivas:
            r = _buscar(s, p, k, fecha)
            pos = _posicion(r, p["esperado"])
            top1 += pos == 0
            topk += pos is not None
            rr += 1 / (pos + 1) if pos is not None else 0
            marca = "✓" if pos == 0 else (f"@{pos + 1}" if pos is not None else "✗")
            primero = f"{r.fragmentos[0].politica_id} v{r.fragmentos[0].version} · {r.fragmentos[0].seccion}" if r.fragmentos else "(sin resultados)"
            print(f"{marca:>3}  {p['pregunta'][:70]:<70}  -> {primero}")
        rechazadas = 0
        for p in negativas:
            r = _buscar(s, p, k, fecha)
            rechazadas += r.sin_resultados
            print(f"{'✓' if r.sin_resultados else '✗':>3}  {p['pregunta'][:70]:<70}  -> "
                  f"{'sin resultados' if r.sin_resultados else f'{r.fragmentos[0].politica_id} ({r.fragmentos[0].similitud:.2f})'}")
    n = len(positivas)
    print(f"\nModelo: {nombre_modelo()}  ·  umbral {umbral_similitud():.2f}  ·  {n} preguntas  ·  acierto@1 {top1 / n:.0%}  ·  "
          f"acierto@{k} {topk / n:.0%}  ·  MRR {rr / n:.2f}")
    if negativas:
        print(f"Sin política: {rechazadas}/{len(negativas)} correctamente sin resultados")


def calibrar(preguntas, k, fecha):
    """Sin umbral, mide la similitud del fragmento correcto (positivas) y la del mejor fragmento (negativas)."""
    os.environ["RAG_UMBRAL_SIMILITUD"] = "-1"
    sim_pos, sim_neg, perdidas = [], [], 0
    with sesion() as s:
        for p in preguntas:
            r = _buscar(s, p, k, fecha)
            if p.get("esperado"):
                pos = _posicion(r, p["esperado"])
                if pos is None:
                    perdidas += 1  # no está ni sin umbral: problema del modelo o de la pregunta, no del umbral
                else:
                    sim_pos.append(r.fragmentos[pos].similitud)
            elif r.fragmentos:
                sim_neg.append(r.fragmentos[0].similitud)
    if not sim_pos:
        print("Ninguna pregunta encontró su política; revisa el modelo de embeddings y la semilla.")
        return
    total_pos = len(sim_pos) + perdidas
    print(f"Modelo: {nombre_modelo()}  ·  {total_pos} preguntas con política ({perdidas} no aparecen ni sin umbral)  ·  "
          f"{len(sim_neg)} sin política")
    print(f"Similitud del fragmento correcto: mín {min(sim_pos):.2f}  ·  mediana {sorted(sim_pos)[len(sim_pos) // 2]:.2f}")
    if sim_neg:
        print(f"Similitud del mejor fragmento sin política: máx {max(sim_neg):.2f}")
    print("\numbral  acierto@k  sin política rechazadas")
    for i in range(0, 19):
        t = i * 0.05
        rec = sum(x >= t for x in sim_pos) / total_pos
        rech = sum(x < t for x in sim_neg) / len(sim_neg) if sim_neg else float("nan")
        print(f"  {t:.2f}     {rec:>5.0%}      {rech:>5.0%}")
    if sim_neg and min(sim_pos) > max(sim_neg):
        t = (min(sim_pos) + max(sim_neg)) / 2
        print(f"\nRecomendado: RAG_UMBRAL_SIMILITUD={t:.2f} (punto medio; separa todas las preguntas de este conjunto)")
    else:
        t = min(sim_pos)
        print(f"\nConservador: RAG_UMBRAL_SIMILITUD={t - 0.01:.2f} (no pierde ninguna política; "
              f"algunas preguntas sin política devolverán un fragmento)")
        if sim_neg:
            candidatos = sorted({round(x, 2) for x in sim_pos + sim_neg})
            mejor = max(candidatos, key=lambda u: sum(x >= u for x in sim_pos) / total_pos + sum(x < u for x in sim_neg) / len(sim_neg))
            print(f"Equilibrado: RAG_UMBRAL_SIMILITUD={mejor:.2f} (acierto {sum(x >= mejor for x in sim_pos) / total_pos:.0%}, "
                  f"sin política rechazadas {sum(x < mejor for x in sim_neg) / len(sim_neg):.0%})")
        print("Si sin_resultados manda casos a revisión humana, conviene el conservador: perder una política es peor.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--fecha", type=date.fromisoformat, default=date(2026, 11, 2))
    ap.add_argument("--preguntas", type=Path, default=RAIZ / "evaluacion" / "preguntas_rag.yaml")
    ap.add_argument("--calibrar", action="store_true")
    args = ap.parse_args()
    preguntas = yaml.safe_load(args.preguntas.read_text(encoding="utf-8"))["preguntas"]
    (calibrar if args.calibrar else evaluar)(preguntas, args.k, args.fecha)


if __name__ == "__main__":
    main()
