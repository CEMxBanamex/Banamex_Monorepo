"""Prueba manual local: python -m backend.grafo_casos.piloto --help."""
import argparse
from datetime import date
import json
import os
from pathlib import Path

from steward_datos.contratos import ContextoUsuario

from .flujo_real import FlujoCasosReal


def main():
    parser = argparse.ArgumentParser(description="Procesar una factura PNG, JPEG o PDF y registrar una decisión humana en la base local.")
    parser.add_argument("archivo")
    parser.add_argument("--caso", required=True, help="Identificador nuevo, por ejemplo F-9001")
    parser.add_argument("--usuario", default="dev-ana")
    parser.add_argument("--fecha", type=date.fromisoformat, default=date.today())
    parser.add_argument("--salida", required=True, help="Carpeta fuera del repositorio para guardar evidencia")
    parser.add_argument("--revisar-lecturas", action="store_true",
                        help="Experimental: conservar lecturas y exigir revisión humana con informe de evidencia")
    args = parser.parse_args()
    if os.getenv("AUTH_MODE") != "dev":
        parser.error("Este piloto interactivo requiere AUTH_MODE=dev y una base de desarrollo.")
    if not os.getenv("DATABASE_URL"):
        parser.error("Definir DATABASE_URL para la base de desarrollo antes de ejecutar el piloto.")
    carpeta = Path(args.salida)
    carpeta.mkdir(parents=True, exist_ok=False)
    flujo = FlujoCasosReal(ContextoUsuario(usuario_id=args.usuario, rol="analista"),
                          revisar_lecturas=args.revisar_lecturas)
    estado = flujo.procesar_caso(args.caso, args.archivo, fecha_recepcion=args.fecha)
    evidencia = {k: v for k, v in estado.items() if k != "__interrupt__"}
    (carpeta / "pausa.json").write_text(json.dumps(evidencia, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(estado["factura"], ensure_ascii=False, indent=2))
    print(estado["explicacion"])
    print("El caso está en revisión. Comprueba el documento original antes de decidir.")
    while True:
        try:
            resultado = input("Decisión (aceptado/rechazado; salir conserva revisión): ").strip().lower()
        except EOFError:
            print("\nNo hay entrada interactiva. El caso se conserva para revisión sin decisión final.")
            print(f"Evidencia: {(carpeta / 'pausa.json').resolve()}")
            return
        if resultado == "salir":
            print("La base conserva el resultado para revisión. Esta pausa en memoria termina con el proceso.")
            return
        if resultado not in {"aceptado", "rechazado"}:
            continue
        try:
            motivo = input("Motivo de tu decisión: ").strip()
        except EOFError:
            print("\nNo se recibió un motivo. El caso se conserva para revisión sin decisión final.")
            return
        if motivo:
            break
    final = flujo.reanudar_caso(args.caso, {"resultado": resultado, "motivo": motivo})
    (carpeta / "final.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Caso {args.caso} revisado. Evidencia: {carpeta.resolve()}")


if __name__ == "__main__":
    main()
