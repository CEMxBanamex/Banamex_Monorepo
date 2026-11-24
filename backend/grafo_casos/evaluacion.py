"""Evaluación S3-13: imágenes reales, verdad solo al calificar y BD aislada por rollback."""
import argparse
from contextlib import contextmanager
import csv
from datetime import date, datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
import platform
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from PIL import Image
from steward_datos.contratos import CAMPOS_FACTURA, ContextoUsuario
from steward_datos.reglas import normalizar

RAIZ = Path(__file__).resolve().parents[2]
CORPUS = RAIZ / "db/semillas/sinteticos/facturas/evaluacion"
CLASES = ("aceptado", "rechazado", "humana")


def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def huellas_codigo():
    from steward_datos.config import CATALOGO_REGLAS
    from . import extraccion
    return {"extraccion_sha256": sha(Path(extraccion.__file__)),
            "evaluador_sha256": sha(Path(__file__)),
            "herramientas_sha256": sha(RAIZ / "backend/grafo_casos/herramientas_reales.py"),
            "catalogo_reglas_sha256": sha(CATALOGO_REGLAS)}


def escribir(ruta, datos):
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(ruta)


def cargar_corpus(carpeta=CORPUS):
    documentos = []
    for ruta in sorted(carpeta.glob("piloto_*.json")):
        d = json.loads(ruta.read_text(encoding="utf-8"))
        if Path(d["archivo"]).name != d["archivo"]:
            raise ValueError("La anotación debe referir a un archivo de la misma carpeta.")
        archivo = carpeta / d["archivo"]
        if sha(archivo) != d["sha256"]:
            raise ValueError(f"El SHA no coincide: {archivo.name}")
        documentos.append(d)
    if not documentos:
        raise ValueError("No se encontraron anotaciones del piloto.")
    return documentos


def normalizado(nombre, valor):
    if valor is None or str(valor).strip() == "":
        return None
    texto = " ".join(str(valor).split()).casefold()
    convertido = None
    if nombre in {"subtotal", "impuestos", "retenciones", "total"}:
        convertido = normalizar.monto(valor)
    elif nombre == "tasa_iva":
        convertido = normalizar.tasa(valor)
    elif nombre == "fecha":
        convertido = normalizar.fecha(valor)
    elif nombre.endswith("_rfc"):
        return normalizar.rfc_normalizado(valor)
    else:
        return texto
    # No convertir dos lecturas inválidas diferentes al mismo None.
    return str(convertido) if convertido is not None else "invalido:" + texto


def calificar(d, registro):
    completo = registro.get("estado") == "pausa"
    salida = registro.get("salida", {})
    extraidos = salida.get("factura", {}).get("campos", {})
    campos = []
    for nombre in CAMPOS_FACTURA:
        esperado = d["verdad"]["campos"].get(nombre)
        leido = extraidos.get(nombre, {}).get("valor")
        presente = esperado is not None and str(esperado).strip() != ""
        emitido = completo and leido is not None and str(leido).strip() != ""
        campos.append({"campo": nombre, "esperado": esperado, "leido": leido,
                       "presente": presente, "emitido": emitido,
                       "correcto": completo and normalizado(nombre, esperado) == normalizado(nombre, leido)})
    pred = salida.get("resultado", {}).get("resultado_sugerido") if completo else "sin_salida"
    if pred not in CLASES:
        pred = "sin_salida"
    reglas = {h["regla_id"] for h in salida.get("resultado", {}).get("hallazgos", [])
              if h["efecto"] != "informativo"} if completo else set()
    return {"archivo": d["archivo"], "estado": registro.get("estado", "pendiente"),
            "esperado": d["esperado"]["resultado"], "predicho": pred,
            "correcto": completo and pred == d["esperado"]["resultado"],
            "reglas_esperadas": sorted(d["esperado"]["reglas"]), "reglas_obtenidas": sorted(reglas),
            "campos": campos}


def cociente(a, b):
    return a / b if b else None


def resumir(documentos, registros):
    casos = [calificar(d, registros.get(d["archivo"], {})) for d in documentos]
    campos = [c for caso in casos for c in caso["campos"]]
    matriz = {e: {p: 0 for p in (*CLASES, "sin_salida")} for e in CLASES}
    for caso in casos:
        matriz[caso["esperado"]][caso["predicho"]] += 1
    por_clase = {}
    for clase in CLASES:
        tp = matriz[clase][clase]
        fp = sum(matriz[e][clase] for e in CLASES if e != clase)
        fn = sum(matriz[clase][p] for p in (*CLASES, "sin_salida") if p != clase)
        por_clase[clase] = {"precision": cociente(tp, tp + fp), "recall": cociente(tp, tp + fn),
                            "f1": cociente(2 * tp, 2 * tp + fp + fn)}
    f1 = [p["f1"] for p in por_clase.values() if p["f1"] is not None]
    correctos = sum(c["correcto"] and c["presente"] and c["emitido"] for c in campos)
    por_campo = {}
    for nombre in CAMPOS_FACTURA:
        filas = [c for c in campos if c["campo"] == nombre]
        por_campo[nombre] = {"correctos": sum(c["correcto"] for c in filas), "total": len(filas),
                             "exactitud": cociente(sum(c["correcto"] for c in filas), len(filas))}
    return {"total_corpus": len(casos), "con_pausa": sum(c["estado"] == "pausa" for c in casos),
            "errores": sum(c["estado"] == "error" for c in casos),
            "pendientes": sum(c["estado"] == "pendiente" for c in casos),
            "clasificacion": {"aciertos": sum(c["correcto"] for c in casos),
                "exactitud_sobre_corpus": cociente(sum(c["correcto"] for c in casos), len(casos)),
                "falsos_aceptados": sum(c["predicho"] == "aceptado" and c["esperado"] != "aceptado" for c in casos),
                "matriz": matriz, "por_clase": por_clase, "macro_f1": sum(f1) / len(f1) if f1 else None},
            "extraccion": {"valores_correctos": correctos, "valores_emitidos": sum(c["emitido"] for c in campos),
                "valores_esperados": sum(c["presente"] for c in campos),
                "precision_valores": cociente(correctos, sum(c["emitido"] for c in campos)),
                "recall_sobre_corpus": cociente(correctos, sum(c["presente"] for c in campos)),
                "por_campo": por_campo}, "casos": casos}


def generar_reportes(carpeta, documentos, registros):
    resumen = resumir(documentos, registros)
    escribir(carpeta / "resumen.json", resumen)
    with (carpeta / "campos.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["archivo", "campo", "esperado", "leido", "presente", "emitido", "correcto"])
        w.writeheader()
        for caso in resumen["casos"]:
            w.writerows({"archivo": caso["archivo"], **campo} for campo in caso["campos"])
    with (carpeta / "casos.csv").open("w", newline="", encoding="utf-8-sig") as f:
        claves = ["archivo", "estado", "esperado", "predicho", "correcto", "reglas_esperadas", "reglas_obtenidas"]
        w = csv.DictWriter(f, fieldnames=claves)
        w.writeheader()
        w.writerows({k: c[k] for k in claves} for c in resumen["casos"])
    def pct(v):
        return "no calculable" if v is None else f"{100*v:.2f}%"
    texto = (f"# S3-13: evaluación del grafo\n\nCorpus: {resumen['total_corpus']}; con pausa: {resumen['con_pausa']}; "
             f"errores: {resumen['errores']}; pendientes: {resumen['pendientes']}.\n\n"
             f"Exactitud de clasificación sobre todo el corpus: {pct(resumen['clasificacion']['exactitud_sobre_corpus'])}.\n\n"
             f"Precisión de valores emitidos: {pct(resumen['extraccion']['precision_valores'])}; "
             f"recall de valores sobre todo el corpus: {pct(resumen['extraccion']['recall_sobre_corpus'])}.\n\n"
             "Errores y pendientes permanecen en los denominadores del corpus. No son aprobaciones humanas.\n\n"
             "Se evalúan 14 campos; conceptos, bbox y confianza no se califican como precisión de extracción. "
             "El grafo llega a la pausa con herramientas reales; sus escrituras se revierten al terminar cada caso. "
             "La verdad no se envía a Gemma ni se usa para decidir. Los PDF se rasterizan completos; "
             "no se inspecciona texto oculto. Los embeddings falso-hash no miden calidad semántica del RAG.\n\n"
             "La tabla por campo y la matriz de confusión están en resumen.json; el detalle, en campos.csv y casos.csv.\n")
    texto += "\n## Clasificación: filas esperadas, columnas predichas\n\n| Esperado | aceptado | rechazado | humana | sin salida |\n| --- | --- | --- | --- | --- |\n"
    for esperado, fila in resumen["clasificacion"]["matriz"].items():
        texto += "| " + esperado + " | " + " | ".join(str(fila[p]) for p in (*CLASES, "sin_salida")) + " |\n"
    texto += "\n## Extracción por campo\n\n| Campo | Coincidencias / corpus | Exactitud normalizada |\n| --- | --- | --- |\n"
    for nombre, fila in resumen["extraccion"]["por_campo"].items():
        texto += f"| {nombre} | {fila['correctos']}/{fila['total']} | {pct(fila['exactitud'])} |\n"
    texto += ("\nEl piloto_001 se usó durante el ajuste del extractor: el corpus no constituye una prueba "
              "independiente de generalización. La referencia de clasificación se mantiene incluso en "
              "escenarios con confianza simulada o texto oculto que el extractor visual no reproduce.\n")
    (carpeta / "informe.md").write_text(texto, encoding="utf-8")
    return resumen


def extraer_documento(archivo, extraer=None):
    """Adaptador exclusivo de evaluación: PDF visible completo convertido a una imagen vertical."""
    from .extraccion import extraer_campos_factura
    extraer = extraer or extraer_campos_factura
    ruta = Path(archivo)
    if ruta.suffix.lower() != ".pdf":
        return extraer(str(ruta))
    import pymupdf
    with pymupdf.open(ruta) as doc:
        if not 1 <= len(doc) <= 4:
            raise ValueError("PDF fuera del límite de evaluación (1 a 4 páginas).")
        imagenes = []
        for pagina in doc:
            pix = pagina.get_pixmap(dpi=150, alpha=False, colorspace=pymupdf.csRGB)
            imagenes.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        ancho, alto = max(i.width for i in imagenes), sum(i.height for i in imagenes)
        if ancho * alto > 40_000_000:
            raise ValueError("PDF renderizado supera el límite de píxeles.")
        lienzo = Image.new("RGB", (ancho, alto), "white")
        y = 0
        for imagen in imagenes:
            lienzo.paste(imagen, (0, y))
            y += imagen.height
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "paginas.png"
            lienzo.save(png)
            factura = extraer(str(png))
        factura.paginas = len(doc)
        return factura


def ejecutar_caso(engine, usuario, caso_id, archivo, fecha):
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from .flujo_real import FlujoCasosReal
    from .herramientas_reales import HerramientasReales
    with engine.connect() as conexion:
        existente = conexion.scalar(text("SELECT count(*) FROM casos WHERE id = :id"), {"id": caso_id})
        conexion.rollback()
        if existente:
            raise ValueError("El identificador de evaluación ya existe.")
        transaccion = conexion.begin()
        @contextmanager
        def sesiones():
            with Session(bind=conexion, join_transaction_mode="create_savepoint") as s:
                try:
                    yield s
                    s.commit()
                except Exception:
                    s.rollback()
                    raise
        try:
            herramientas = HerramientasReales(usuario, sesiones=sesiones)
            flujo = FlujoCasosReal(usuario, herramientas=herramientas, extraer=extraer_documento)
            salida = flujo.procesar_caso(caso_id, str(archivo), fecha_recepcion=date.fromisoformat(fecha))
            if not salida.get("__interrupt__"):
                raise RuntimeError("El grafo no se detuvo para revisión humana.")
            return {k: v for k, v in salida.items() if k != "__interrupt__"}
        finally:
            transaccion.rollback()
            if conexion.scalar(text("SELECT count(*) FROM casos WHERE id = :id"), {"id": caso_id}):
                raise RuntimeError("Falló el aislamiento: quedó un caso de evaluación en la base.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--limite", type=int, help="Número máximo de documentos nuevos; el corpus del informe sigue completo.")
    ap.add_argument("--reanudar", action="store_true", help="Retomar solo pendientes, sin repetir errores ya registrados.")
    args = ap.parse_args()
    if args.limite is not None and args.limite < 1:
        ap.error("--limite debe ser positivo.")
    url = os.environ.get("GRAFO_EVAL_DATABASE_URL", "")
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    if os.getenv("AUTH_MODE") != "dev" or not url:
        ap.error("Definir AUTH_MODE=dev y GRAFO_EVAL_DATABASE_URL de una base de evaluación.")
    db = make_url(url)
    if db.database != "dsa_pruebas" and not (db.database or "").startswith("dsa_eval_"):
        ap.error("Usar dsa_pruebas o una base dsa_eval_*, nunca la base de la aplicación.")
    os.environ["DATABASE_URL"] = url
    os.environ.setdefault("EMBEDDING_PROVEEDOR", "falso")
    engine = create_engine(url)
    with engine.connect() as c:
        if c.scalar(text("SELECT count(*) FROM casos WHERE origen = 'aplicacion'")):
            ap.error("La base contiene casos de aplicación. Preparar una base nueva con las semillas originales.")
        if not c.scalar(text("SELECT count(*) FROM reglas")):
            ap.error("Falta cargar el catálogo de reglas.")
    import httpx
    documentos = cargar_corpus()
    direccion = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    with httpx.Client(base_url=direccion, timeout=15) as cliente:
        r = cliente.get("/api/tags"); r.raise_for_status()
        modelo = os.getenv("VISION_MODELO", "gemma3:4b")
        modelos = [m for m in r.json()["models"] if m["name"] == modelo]
        if not modelos:
            ap.error(f"El modelo {modelo} no está disponible en Ollama.")
    congelado = {"modelo": modelo, "digest_modelo": modelos[0]["digest"],
                 "embeddings": os.getenv("EMBEDDING_PROVEEDOR", "falso"),
                 **huellas_codigo(),
                 "python": platform.python_version(),
                 "librerias": {p: version(p) for p in ("langgraph", "httpx", "PyMuPDF", "sqlalchemy")},
                 "pdf_dpi": 150, "pdf_modo": "paginas_visibles_en_imagen_vertical",
                 "corpus": {d["archivo"]: {"sha256": d["sha256"], "anotacion_sha256": sha(CORPUS / (Path(d["archivo"]).stem + ".json"))} for d in documentos}}
    carpeta = args.salida.resolve()
    if carpeta == RAIZ or RAIZ in carpeta.parents:
        ap.error("Guardar resultados fuera del repositorio.")
    manifiesto = carpeta / "ejecucion.json"
    if args.reanudar:
        previo = json.loads(manifiesto.read_text(encoding="utf-8"))
        if previo["configuracion"] != congelado:
            ap.error("Cambió el código, modelo, corpus o configuración; usar otra carpeta para una evaluación nueva.")
    else:
        carpeta.mkdir(parents=True, exist_ok=False)
        (carpeta / "documentos").mkdir()
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
        previo = {"inicio_utc": datetime.now(timezone.utc).isoformat(), "id": uuid.uuid4().hex,
                  "commit": commit, "base": db.database, "configuracion": congelado}
        escribir(manifiesto, previo)
    registros = {}
    for d in documentos:
        archivo = carpeta / "documentos" / (Path(d["archivo"]).stem + ".json")
        if archivo.exists():
            registros[d["archivo"]] = json.loads(archivo.read_text(encoding="utf-8"))
    generar_reportes(carpeta, documentos, registros)
    nuevos = 0
    for i, d in enumerate(documentos):
        if d["archivo"] in registros:
            continue
        if args.limite is not None and nuevos >= args.limite:
            break
        nuevos += 1
        caso_id = "F-" + str(int(previo["id"][:8], 16)).zfill(10)[:8] + f"{i:02d}"
        print(f"[{i+1}/{len(documentos)}] {d['archivo']} -> {caso_id}", flush=True)
        inicio = time.monotonic()
        registro = {"archivo": d["archivo"], "caso_id": caso_id, "sha256": d["sha256"]}
        try:
            registro["salida"] = ejecutar_caso(engine, ContextoUsuario(usuario_id="dev-evaluacion", rol="analista"),
                                               caso_id, CORPUS / d["archivo"], d["fecha_recepcion"])
            registro["estado"] = "pausa"
            # Retirar rutas absolutas de la evidencia exportable.
            registro["salida"]["archivo"] = d["archivo"]
        except Exception as exc:
            registro.update(estado="error", error_tipo=type(exc).__name__, error=str(exc))
        registro["segundos"] = round(time.monotonic() - inicio, 3)
        escribir(carpeta / "documentos" / (Path(d["archivo"]).stem + ".json"), registro)
        registros[d["archivo"]] = registro
        resumen = generar_reportes(carpeta, documentos, registros)
        print(f"  {registro['estado']} ({registro['segundos']} s)", flush=True)
    resumen = generar_reportes(carpeta, documentos, registros)
    print(f"Con pausa: {resumen['con_pausa']}; errores: {resumen['errores']}; pendientes: {resumen['pendientes']}.")
    print(f"Informe: {carpeta / 'informe.md'}")


if __name__ == "__main__":
    main()
