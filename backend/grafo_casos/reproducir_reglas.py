"""Reglas reales sobre lecturas guardadas, con contexto sintético y sin Ollama/BD."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from steward_datos.contratos import FacturaExtraida
from steward_datos.reglas import motor
from steward_datos.sinteticos import contexto_para
from steward_datos import config
from .comparar_vision import CORPUS, corpus, escribir
from .revision_evidencia import revisar_evidencia

CLASES = ("aceptado", "rechazado", "humana")


def clasificar(documentos, registros, etapa, contexto):
    casos = []
    for i, d in enumerate(documentos):
        r = registros[d["archivo"]]
        esperado = d["esperado"]["resultado"]
        salida = None
        informe = None
        if r["estado"] == "ok":
            factura = FacturaExtraida.model_validate(r[etapa])
            # Contexto fijo de catálogos, históricos, SHA y fecha: nunca se usa la
            # categoría/regla esperada para formar la predicción.
            salida = motor.validar_factura(f"F-{9600 + i}", factura, contexto(d)).model_dump(mode="json")
            predicho = salida["resultado_sugerido"]
            informe = revisar_evidencia(factura)
        else:
            predicho = "sin_salida"
        reglas = sorted({h["regla_id"] for h in (salida or {}).get("hallazgos", []) if h["efecto"] != "informativo"})
        casos.append({
            "archivo": d["archivo"], "esperado": esperado, "predicho_reglas": predicho,
            "categoria_correcta": predicho == esperado,
            "reglas_esperadas": d["esperado"]["reglas"], "reglas_obtenidas": reglas,
            "reglas_esperadas_no_detectadas": sorted(set(d["esperado"]["reglas"]) - set(reglas)),
            "resultado_reglas": salida,
            "sugerencia_modo_revision": "humana" if salida else "sin_salida",
            "revision_evidencia": informe,
            "error": r.get("error"),
        })
    matriz = {e: {p: 0 for p in (*CLASES, "sin_salida")} for e in CLASES}
    for c in casos:
        matriz[c["esperado"]][c["predicho_reglas"]] += 1
    falsos = [c["archivo"] for c in casos if c["predicho_reglas"] == "aceptado" and c["esperado"] != "aceptado"]
    return {"casos": casos, "total": len(casos), "aciertos_categoria": sum(c["categoria_correcta"] for c in casos),
            "matriz": matriz, "sugerencias_aceptado_no_esperadas": falsos,
            "nota": "Predicción de reglas sobre lecturas; no es una aceptación final ni una prueba de persistencia."}


def reproducir(entrada, salida, carpeta_corpus=CORPUS):
    documentos = corpus(carpeta_corpus)
    manifiesto = json.loads((entrada / "ejecucion.json").read_text(encoding="utf-8"))
    identidad = manifiesto["identidad"]
    if {d["archivo"]: d["sha256"] for d in documentos} != {
            nombre: dato["imagen_sha256"] for nombre, dato in identidad["corpus"].items()}:
        raise ValueError("El corpus de imágenes no coincide con la evaluación guardada.")
    for d in documentos:
        datos = (carpeta_corpus / (Path(d["archivo"]).stem + ".json")).read_bytes()
        variantes = [datos, datos.replace(b"\r\n", b"\n"), datos.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")]
        if identidad["corpus"][d["archivo"]]["referencia_sha256"] not in [hashlib.sha256(v).hexdigest() for v in variantes]:
            raise ValueError(f"Cambió la referencia: {d['archivo']}")
    salida.mkdir(parents=True, exist_ok=False)
    resultados = {}
    for i, modelo in enumerate(identidad["modelos"], 1):
        registros = {}
        for d in documentos:
            ruta = entrada / f"modelo_{i}" / (Path(d["archivo"]).stem + ".json")
            r = json.loads(ruta.read_text(encoding="utf-8"))
            if r["archivo"] != d["archivo"] or r["modelo"] != modelo:
                raise ValueError(f"Registro incompatible: {ruta}")
            registros[d["archivo"]] = r
        resultados[modelo] = {etapa: clasificar(documentos, registros, etapa, contexto_para)
                              for etapa in ("sin_filtro", "filtro_anterior")}
    escribir(salida / "reglas.json", resultados)
    fuentes = {"motor": Path(motor.__file__), "catalogo": config.CATALOGO_REGLAS,
               "proveedores": config.CARPETA_SINTETICOS / "catalogos/proveedores.csv",
               "entidades": config.CARPETA_SINTETICOS / "catalogos/entidades_receptoras.csv"}
    escribir(salida / "procedencia.json", {
        "sha256_manifiesto_entrada": hashlib.sha256((entrada / "ejecucion.json").read_bytes()).hexdigest(),
        "sha256_fuentes": {k: hashlib.sha256(Path(p).read_bytes()).hexdigest() for k, p in fuentes.items()},
        "contexto": "catálogos sintéticos del repositorio, antecedentes históricos, lista 69-B local y fecha anotada",
        "alcance": "Reproducción determinista; sin llamadas a modelos, consultas o escrituras en BD, ni RAG.",
    })
    texto = ["# Reproducción de reglas sobre las lecturas", "",
             "Reglas reales con contexto sintético del repositorio. Sin Ollama ni base de datos.",
             "No verifica persistencia, permisos, RAG ni decisiones del analista.", "",
             "| Modelo | Etapa | Categorías coincidentes | Sugerencias de aceptar no esperadas |",
             "| --- | --- | --- | --- |"]
    with (salida / "casos_reglas.csv").open("w", newline="", encoding="utf-8-sig") as f:
        claves = ["modelo", "etapa", "archivo", "esperado", "predicho_reglas", "categoria_correcta",
                  "reglas_esperadas", "reglas_obtenidas", "reglas_esperadas_no_detectadas"]
        w = csv.DictWriter(f, fieldnames=claves)
        w.writeheader()
        for modelo, etapas in resultados.items():
            for etapa, r in etapas.items():
                texto.append(f"| {modelo} | {etapa} | {r['aciertos_categoria']}/{r['total']} | "
                             f"{len(r['sugerencias_aceptado_no_esperadas'])} |")
                for c in r["casos"]:
                    w.writerow({"modelo": modelo, "etapa": etapa, **{k: c[k] for k in claves[2:]}})
    texto += ["", "## Límites y decisiones", "",
              "El modo experimental publica sugerencia humana para toda lectura completada, independientemente de las reglas; "
              "no se usa ese bloqueo para inflar la exactitud de clasificación.",
              "Una categoría coincidente no implica que todas las reglas esperadas se detectaron: el detalle incluye reglas esperadas no detectadas.",
              "La referencia contiene escenarios con confianza simulada y texto oculto que el extractor visual puede no reproducir. Se conservan las discrepancias en los resultados.",
              "No se reemplazan lecturas por verdad de referencia ni se corrigen errores durante esta reproducción."]
    (salida / "informe_reglas.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    return resultados


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lecturas", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    resultados = reproducir(args.lecturas, args.salida)
    for modelo, etapas in resultados.items():
        r = etapas["sin_filtro"]
        print(f"{modelo}: {r['aciertos_categoria']}/{r['total']} categorías coincidentes; "
              f"{len(r['sugerencias_aceptado_no_esperadas'])} sugerencias de aceptar no esperadas.")
    print(f"Informe: {(args.salida / 'informe_reglas.md').resolve()}")


if __name__ == "__main__":
    main()
