"""Evaluación del agente de gobernanza.

Uso:
  python scripts/evaluar_gobernanza.py fuentes
      Sin LLM. Revisa que cada fuente esperada exista en la base y diga lo que la respuesta debe contener.
      Requiere la semilla cargada. Sale con código 1 si algo falla (sirve en CI).
  python scripts/evaluar_gobernanza.py respuestas --archivo salidas.jsonl [--detalle]
      Califica las salidas del agente. Cada línea: {"id": "G-01", "tools": [{"nombre": "...", "argumentos": {}}], "respuesta": "..."}
      El grafo del chat puede armarla con los eventos de paso (tools) y el evento de respuesta.
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.eval_agentes import calificar, cargar_preguntas, resumen, revisar_fuente  # noqa: E402

PREGUNTAS = RAIZ / "evaluacion" / "preguntas_gobernanza.yaml"


def fuentes(preguntas: list[dict]) -> int:
    from steward_datos.db.sesion import sesion
    fallas = 0
    with sesion() as s:
        for p in preguntas:
            ok, motivo = revisar_fuente(s, p)
            fallas += not ok
            print(f"{'✓' if ok else '✗'} {p['id']}  {p['pregunta'][:70]:<70}  {motivo}")
    print(f"\n{len(preguntas) - fallas}/{len(preguntas)} preguntas con su fuente en la base")
    return 1 if fallas else 0


def respuestas(preguntas: list[dict], archivo: Path, detalle: bool) -> int:
    salidas = {}
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            d = json.loads(linea)
            salidas[d["id"]] = d
    resultados = []
    for p in preguntas:
        if p["id"] not in salidas:
            print(f"  {p['id']}  sin salida del agente")
            continue
        r = calificar(p, salidas[p["id"]])
        resultados.append(r)
        if detalle or not r["ok"]:
            fallidas = [k for k, v in r["checks"].items() if not v]
            print(f"{'✓' if r['ok'] else '✗'} {p['id']}  {p['pregunta'][:60]:<60}  {', '.join(fallidas)}")
    res = resumen(resultados)
    print(f"\nAciertos: {res['aciertos']}/{res['total']}")
    for cat, (a, n) in sorted(res["por_categoria"].items()):
        print(f"  {cat:<18} {a}/{n}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["fuentes", "respuestas"])
    ap.add_argument("--preguntas", type=Path, default=PREGUNTAS)
    ap.add_argument("--archivo", type=Path, help="JSONL con las salidas del agente (modo respuestas)")
    ap.add_argument("--detalle", action="store_true")
    args = ap.parse_args()
    preguntas = cargar_preguntas(args.preguntas)
    if args.modo == "fuentes":
        sys.exit(fuentes(preguntas))
    if not args.archivo:
        ap.error("--archivo es obligatorio en modo respuestas")
    sys.exit(respuestas(preguntas, args.archivo, args.detalle))


if __name__ == "__main__":
    main()
