"""Comparación de extracción local sin BD: mismas imágenes y solicitud para ambos modelos."""
import argparse
import base64
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import statistics
import time

import httpx

from steward_datos import contratos
from steward_datos.contratos import CAMPOS_FACTURA
from steward_datos.reglas import normalizar
from . import extraccion

RAIZ = Path(__file__).resolve().parents[2]
CORPUS = RAIZ / "db/semillas/sinteticos/facturas/evaluacion"
AJUSTE = {"piloto_001.png", "piloto_003.png", "piloto_012.png"}
CRITICOS = {"folio", "fecha", "emisor_rfc", "receptor_rfc", "subtotal", "impuestos", "total"}


def huella(datos):
    return hashlib.sha256(datos).hexdigest()


def escribir(ruta, datos):
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(ruta)


def corpus(carpeta):
    documentos = []
    for ruta in sorted(carpeta.glob("piloto_*.json")):
        dato = json.loads(ruta.read_text(encoding="utf-8"))
        nombre = dato["archivo"]
        if Path(nombre).name != nombre or "\\" in nombre:
            raise ValueError("La referencia debe nombrar un archivo local, sin rutas.")
        if huella((carpeta / nombre).read_bytes()) != dato["sha256"]:
            raise ValueError(f"El archivo no coincide con la referencia: {nombre}")
        documentos.append(dato)
    if not documentos:
        raise ValueError("No hay documentos anotados.")
    return documentos


def normalizado(nombre, valor):
    if valor is None or not str(valor).strip():
        return None
    texto = " ".join(str(valor).split()).casefold()
    if nombre.endswith("_rfc"):
        return normalizar.rfc_normalizado(str(valor))
    funcion = (normalizar.fecha if nombre == "fecha" else normalizar.tasa if nombre == "tasa_iva"
               else normalizar.monto if nombre in {"subtotal", "impuestos", "retenciones", "total",
                                                   "cantidad", "precio_unitario", "importe"} else None)
    if funcion is None:
        return texto
    convertido = funcion(str(valor))
    if convertido is None:
        return "invalido:" + texto
    return format(convertido.normalize(), "f") if hasattr(convertido, "normalize") else str(convertido)


def concepto_normalizado(c):
    return tuple(normalizado(k, c.get(k)) for k in ("descripcion", "cantidad", "precio_unitario", "importe"))


def division(a, b):
    return a / b if b else None


def puntuar(documentos, registros, etapa):
    campos = []
    conceptos_correctos = conceptos_emitidos = conceptos_esperados = conceptos_documentos_exactos = 0
    completos = 0
    for d in documentos:
        r = registros.get(d["archivo"], {})
        ok = r.get("estado") == "ok"
        factura = r.get(etapa, {}) if ok else {}
        leidos = factura.get("campos", {})
        completo = ok
        for nombre in CAMPOS_FACTURA:
            esperado = normalizado(nombre, d["verdad"]["campos"].get(nombre))
            leido = normalizado(nombre, leidos.get(nombre, {}).get("valor"))
            correcto = ok and esperado == leido
            completo = completo and correcto
            campos.append({"archivo": d["archivo"], "campo": nombre, "esperado": esperado,
                           "leido": leido, "correcto": correcto, "presente": esperado is not None,
                           "emitido": ok and leido is not None})
        completos += bool(completo)
        esperados = [concepto_normalizado(c) for c in d["verdad"].get("conceptos", [])]
        emitidos = [concepto_normalizado(c) for c in factura.get("conceptos", [])]
        # Comparación estricta por posición: duplicar u omitir filas no mejora la puntuación.
        conceptos_correctos += sum(a == b for a, b in zip(esperados, emitidos)) if ok else 0
        conceptos_esperados += len(esperados)
        conceptos_emitidos += len(emitidos)
        conceptos_documentos_exactos += bool(ok and esperados == emitidos)
    correctos = sum(c["correcto"] and c["presente"] and c["emitido"] for c in campos)
    emitidos = sum(c["emitido"] for c in campos)
    esperados = sum(c["presente"] for c in campos)
    return {
        "documentos": len(documentos), "documentos_14_campos_correctos": completos,
        "valores_correctos": correctos, "valores_emitidos": emitidos, "valores_esperados": esperados,
        "precision_valores": division(correctos, emitidos), "recall_valores": division(correctos, esperados),
        "errores_criticos_emitidos": sum(c["campo"] in CRITICOS and c["emitido"] and not c["correcto"] for c in campos),
        "criticos_esperados_sin_lectura": sum(c["campo"] in CRITICOS and c["presente"] and not c["emitido"] for c in campos),
        "por_campo": {nombre: {"correctos": sum(c["correcto"] for c in campos if c["campo"] == nombre),
                                "total": len(documentos)} for nombre in CAMPOS_FACTURA},
        "conceptos": {"filas_correctas_en_orden": conceptos_correctos, "filas_emitidas": conceptos_emitidos,
                      "filas_esperadas": conceptos_esperados,
                      "precision_filas": division(conceptos_correctos, conceptos_emitidos),
                      "recall_filas": division(conceptos_correctos, conceptos_esperados),
                      "documentos_tabla_exacta": conceptos_documentos_exactos},
        "detalle_campos": campos,
    }


def resumir(documentos, registros, modelos):
    salida = {}
    for modelo in modelos:
        datos = registros.get(modelo, {})
        intentos = list(datos.values())
        tiempos = [r["segundos"] for r in intentos]
        salida[modelo] = {
            "ok": sum(r.get("estado") == "ok" for r in intentos),
            "errores": sum(r.get("estado") == "error" for r in intentos),
            "pendientes": len(documentos) - len(intentos),
            "segundos_totales": sum(tiempos), "mediana_segundos": statistics.median(tiempos) if tiempos else None,
            "grupos": {},
        }
        for grupo, seleccion in {
            "todos": documentos,
            "usados_ajuste_qwen": [d for d in documentos if d["archivo"] in AJUSTE],
            "restantes": [d for d in documentos if d["archivo"] not in AJUSTE],
            "pdf": [d for d in documentos if d["archivo"].lower().endswith(".pdf")],
            "imagenes": [d for d in documentos if not d["archivo"].lower().endswith(".pdf")],
        }.items():
            salida[modelo]["grupos"][grupo] = {
                etapa: puntuar(seleccion, datos, etapa) for etapa in ("sin_filtro", "filtro_anterior")}
    return salida


def reportar(carpeta, documentos, registros, modelos):
    # Detectar cambios accidentales de preprocesamiento o solicitud entre modelos.
    for d in documentos:
        solicitudes = []
        for modelo in modelos:
            r = registros.get(modelo, {}).get(d["archivo"], {})
            if r.get("solicitud"):
                solicitud = {k: v for k, v in r["solicitud"].items() if k != "model"}
                solicitudes.append((solicitud, r["imagenes_enviadas_sha256"]))
        if solicitudes and any(s != solicitudes[0] for s in solicitudes[1:]):
            raise ValueError(f"Solicitudes o imágenes distintas entre modelos: {d['archivo']}. Revisar los registros.")
    resumen = resumir(documentos, registros, modelos)
    escribir(carpeta / "resumen.json", resumen)
    def porcentaje(v):
        return "n/d" if v is None else f"{v * 100:.2f}%"
    texto = ["# Comparación de extracción visual", "",
             "Misma solicitud y documentos para ambos modelos; sin base de datos ni escrituras de casos.",
             "No evalúa clasificación, decisiones humanas ni calidad semántica del RAG.",
             "Errores y pendientes cuentan como lecturas no recuperadas; los nulos correctos no inflan la precisión de valores.",
             "Los tres pilotos usados para ajustar Qwen se muestran separados; los restantes tampoco acreditan generalización externa.", ""]
    for modelo, dato in resumen.items():
        texto.append(f"- {modelo}: {dato['ok']} salidas; {dato['errores']} errores; {dato['pendientes']} pendientes.")
    texto += ["",
             "| Modelo | Grupo | Etapa | Precisión valores | Recall valores | Documentos 14 campos | Recall conceptos |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for modelo, dato in resumen.items():
        for grupo in ("todos", "restantes"):
            for etapa, r in dato["grupos"][grupo].items():
                texto.append(f"| {modelo} | {grupo} | {etapa} | {porcentaje(r['precision_valores'])} | "
                             f"{porcentaje(r['recall_valores'])} | {r['documentos_14_campos_correctos']}/{r['documentos']} | "
                             f"{porcentaje(r['conceptos']['recall_filas'])} |")
    texto += ["", "La etapa filtro_anterior usa la misma lectura: mide pérdidas del filtro sin otra inferencia.",
              "Conservar valores no certifica su exactitud. Revisar errores críticos y documentos completos, además del promedio.",
              "Las métricas históricas de S3-13 corresponden a otra configuración y no son una comparación controlada."]
    (carpeta / "informe.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    with (carpeta / "campos.csv").open("w", newline="", encoding="utf-8-sig") as f:
        claves = ["modelo", "etapa", "archivo", "campo", "esperado", "leido", "correcto", "presente", "emitido"]
        w = csv.DictWriter(f, fieldnames=claves)
        w.writeheader()
        for modelo in modelos:
            for etapa, r in resumen[modelo]["grupos"]["todos"].items():
                w.writerows({"modelo": modelo, "etapa": etapa, **fila} for fila in r["detalle_campos"])
    return resumen


def ejecutar(archivo, modelo, url):
    registro = {"archivo": archivo.name, "modelo": modelo, "estado": "error"}
    inicio = time.perf_counter()
    def solicitud(request):
        payload = json.loads(request.content)
        imagenes = payload.pop("images", [])
        registro["solicitud"] = payload
        registro["imagenes_enviadas_sha256"] = [huella(base64.b64decode(i)) for i in imagenes]
    def respuesta(response):
        response.read()
        registro["http_status"] = response.status_code
        try:
            registro["respuesta_ollama"] = response.json()
        except ValueError:
            registro["respuesta_http_texto"] = response.text
    anterior = os.environ.get("VISION_MODELO")
    try:
        os.environ["VISION_MODELO"] = modelo
        with httpx.Client(base_url=url, timeout=180, event_hooks={"request": [solicitud], "response": [respuesta]}) as cliente:
            factura = extraccion.extraer_campos_factura(str(archivo), cliente=cliente, conservar_lecturas=True)
        registro["sin_filtro"] = factura.model_dump(mode="json")
        filtrada = factura.model_copy(deep=True)
        extraccion._filtrar_evidencia(filtrada)
        registro["filtro_anterior"] = filtrada.model_dump(mode="json")
        registro["estado"] = "ok"
    except Exception as error:
        registro["error"] = f"{type(error).__name__}: {error}"
    finally:
        if anterior is None:
            os.environ.pop("VISION_MODELO", None)
        else:
            os.environ["VISION_MODELO"] = anterior
    registro["segundos"] = round(time.perf_counter() - inicio, 3)
    return registro


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--modelos", nargs="+", default=["qwen3-vl:4b-instruct", "gemma3:4b"])
    parser.add_argument("--reanudar", action="store_true")
    parser.add_argument("--limite", type=int, help="Limita documentos por modelo; el informe conserva el denominador completo")
    args = parser.parse_args()
    if args.limite is not None and args.limite < 1:
        parser.error("El límite debe ser positivo.")
    if len(set(args.modelos)) != len(args.modelos):
        parser.error("No repetir modelos.")
    documentos = corpus(args.corpus)
    url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL", "http://localhost:11434")
    with httpx.Client(base_url=url, timeout=30) as cliente:
        r = cliente.get("/api/tags")
        r.raise_for_status()
        instalados = {m["name"]: m["digest"] for m in r.json()["models"]}
    for modelo in args.modelos:
        if modelo not in instalados:
            parser.error(f"Modelo no instalado: {modelo}")
    identidad = {
        "modelos": {m: instalados[m] for m in args.modelos},
        "codigo": {p.name: huella(p.read_bytes()) for p in (
            Path(__file__), Path(extraccion.__file__), Path(contratos.__file__), Path(normalizar.__file__))},
        "corpus": {d["archivo"]: {"imagen_sha256": d["sha256"],
                                    "referencia_sha256": huella((args.corpus / (Path(d["archivo"]).stem + ".json")).read_bytes())}
                   for d in documentos},
        "python": platform.python_version(),
        "paquetes": {p: version(p) for p in ("httpx", "pydantic", "pypdfium2", "pillow")},
        "ollama_url": url,
    }
    manifiesto = args.salida / "ejecucion.json"
    if args.reanudar:
        previo = json.loads(manifiesto.read_text(encoding="utf-8"))
        if previo["identidad"] != identidad:
            parser.error("Cambió código, corpus, modelos o entorno. Usar una carpeta nueva.")
    else:
        args.salida.mkdir(parents=True, exist_ok=False)
        escribir(manifiesto, {"inicio_utc": datetime.now(timezone.utc).isoformat(), "identidad": identidad,
                             "nota": "No se usó BD. La verdad solo se usa al calificar; no se envía al modelo."})
    registros = {m: {} for m in args.modelos}
    carpetas = {}
    for i, modelo in enumerate(args.modelos):
        carpeta = args.salida / f"modelo_{i + 1}"
        carpeta.mkdir(exist_ok=True)
        carpetas[modelo] = carpeta
        for d in documentos:
            ruta = carpeta / (Path(d["archivo"]).stem + ".json")
            if ruta.exists():
                registro = json.loads(ruta.read_text(encoding="utf-8"))
                if registro.get("modelo") != modelo or registro.get("archivo") != d["archivo"]:
                    parser.error("Un registro no corresponde a esta ejecución.")
                registros[modelo][d["archivo"]] = registro
    reportar(args.salida, documentos, registros, args.modelos)
    for modelo in args.modelos:
        for i, d in enumerate(documentos[:args.limite], 1):
            if d["archivo"] in registros[modelo]:
                continue
            print(f"[{modelo}] {i}/{len(documentos)} {d['archivo']}", flush=True)
            registro = ejecutar(args.corpus / d["archivo"], modelo, url)
            escribir(carpetas[modelo] / (Path(d["archivo"]).stem + ".json"), registro)
            registros[modelo][d["archivo"]] = registro
            reportar(args.salida, documentos, registros, args.modelos)
            print(f"  {registro['estado']} | {registro['segundos']} s | {registro.get('error', '')}", flush=True)
    print(f"Informe: {(args.salida / 'informe.md').resolve()}")


if __name__ == "__main__":
    main()
