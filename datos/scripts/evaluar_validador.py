"""Evaluación del agente validador (dueña: Iris).

Uso:
  python scripts/evaluar_validador.py citas [--fecha 2026-11-02]
      Sin LLM. Para cada regla del catálogo, revisa que buscar_politicas (filtrando por regla e historia, sin tipo)
      devuelva la sección exacta que la sustenta. Correrlo al cambiar de modelo de embeddings o de umbral.
      Sale con código 1 si alguna regla se queda sin su sección.
  python scripts/evaluar_validador.py entradas --salida entradas.jsonl
      Escribe las 39 entradas de evaluación (ValidarReglasEntrada con la extracción de referencia) para correr el agente.
  python scripts/evaluar_validador.py respuestas --archivo salidas.jsonl
      Califica las salidas del agente. Cada línea: {"caso_id", "tools": [{"nombre"}], "resultado_sugerido",
      "hallazgos": [{"regla_id", "politica_id", "politica_version", "politica_seccion"}]}
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.contratos import BuscarPoliticasEntrada, ValidarReglasEntrada  # noqa: E402
from steward_datos.eval_agentes import calificar_validador  # noqa: E402
from steward_datos.reglas.catalogo import catalogo  # noqa: E402
from steward_datos.sinteticos import anotaciones, factura_desde_anotacion  # noqa: E402


def citas(fecha: date) -> int:
    from steward_datos.db.sesion import sesion
    from steward_datos.tools.buscar_politicas import buscar_politicas
    fallas = 0
    with sesion() as s:
        for r in catalogo().reglas.values():
            res = buscar_politicas(BuscarPoliticasEntrada(consulta=r.nombre, k=5, reglas=[r.id], historia=r.historia,
                                                          fecha=fecha), s)
            pos = next((i for i, f in enumerate(res.fragmentos) if (f.politica_id, f.version, f.seccion)
                        == (r.politica_id, r.politica_version, r.seccion)), None)
            fallas += pos is None
            sim = f"{res.fragmentos[pos].similitud:.2f}" if pos is not None else "—"
            print(f"{'✓' if pos is not None else '✗'} {r.id}  {r.politica_id} v{r.politica_version} · {r.seccion:<38} "
                  f"posición {pos + 1 if pos is not None else '—'}  similitud {sim}")
    print(f"\n{len(catalogo().reglas) - fallas}/{len(catalogo().reglas)} reglas encuentran su sección")
    return 1 if fallas else 0


def _casos():
    return [d for d in anotaciones("evaluacion")]


def entradas(salida: Path) -> int:
    with salida.open("w", encoding="utf-8") as f:
        for d in _casos():
            e = ValidarReglasEntrada(caso_id=d.get("caso_id") or d["archivo"], historia=1, factura=factura_desde_anotacion(d),
                                     sha256=d.get("sha256"), fecha_recepcion=date.fromisoformat(d["fecha_recepcion"]))
            f.write(e.model_dump_json() + "\n")
    print(f"{len(_casos())} entradas en {salida}")
    return 0


def respuestas(archivo: Path) -> int:
    salidas = {}
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            d = json.loads(linea)
            salidas[d["caso_id"]] = d
    cat = catalogo()
    ok = falsos = n = 0
    for d in _casos():
        cid = d.get("caso_id") or d["archivo"]
        if cid not in salidas:
            print(f"  {cid}  sin salida del agente")
            continue
        r = calificar_validador(d["esperado"], salidas[cid], cat)
        n += 1
        ok += r["ok"]
        falsos += r["falso_aceptado"]
        if not r["ok"]:
            fallidas = [k for k, v in r["checks"].items() if not v]
            print(f"✗ {cid:<18} {d['escenario']:<28} {', '.join(fallidas)}{'  FALSO ACEPTADO' if r['falso_aceptado'] else ''}")
    print(f"\nAciertos: {ok}/{n}  ·  falsos aceptados: {falsos}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["citas", "entradas", "respuestas"])
    ap.add_argument("--fecha", type=date.fromisoformat, default=date(2026, 11, 2))
    ap.add_argument("--salida", type=Path, default=Path("entradas_validador.jsonl"))
    ap.add_argument("--archivo", type=Path)
    args = ap.parse_args()
    if args.modo == "citas":
        sys.exit(citas(args.fecha))
    if args.modo == "entradas":
        sys.exit(entradas(args.salida))
    if not args.archivo:
        ap.error("--archivo es obligatorio en modo respuestas")
    sys.exit(respuestas(args.archivo))


if __name__ == "__main__":
    main()
