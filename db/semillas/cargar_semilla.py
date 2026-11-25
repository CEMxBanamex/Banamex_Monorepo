"""Carga los datos semilla en la base (tarea 1.4.4). Requiere la migración aplicada (alembic -c db/migrations/alembic.ini upgrade head).

Carga, en este orden:
  1. Padrón de proveedores y entidades receptoras (sinteticos/catalogos/).
  2. Catálogo de reglas (reglas/catalogo.yaml).
  3. Políticas (politicas/*.md) con sus fragmentos; con --embeddings también genera los vectores (necesita Ollama
     o EMBEDDING_PROVEEDOR=falso).
  4. Histórico: 30 facturas ya revisadas (F-1000 a F-1029).
  5. Casos de la demo con los mismos IDs que el mock del frontend: F-1040, F-1041, F-1042, V-0206 y V-0207.
  6. Datos de negocio (sinteticos/negocio/): centros de costo, órdenes de compra, clientes, permisos por entidad y
     960 facturas ya revisadas (F-0001 a F-0960) con sus pagos.
  7. Gobernanza: catálogo de datos, glosario, métricas y reglas de calidad con sus resultados.

Los casos de sinteticos/facturas/evaluacion/ NO se cargan: se suben por la aplicación durante la evaluación.

Uso:  python db/semillas/cargar_semilla.py [--embeddings] [--reiniciar]
"""
import argparse
import csv
import hashlib
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import text

RAIZ = Path(__file__).resolve().parents[2] / "datos"  # steward_datos vive en datos/
sys.path.insert(0, str(RAIZ))
from steward_datos.config import CARPETA_POLITICAS, CARPETA_SINTETICOS  # noqa: E402
from steward_datos.db.models import (  # noqa: E402
    CampoExtraido, Caso, Documento, EntidadReceptora, EventoBitacora, Proveedor, Regla,
)
from steward_datos.db.sesion import sesion  # noqa: E402
from steward_datos.gobernanza import cargar_calidad, cargar_catalogo, cargar_glosario, cargar_metricas  # noqa: E402
from steward_datos.negocio import cargar_negocio  # noqa: E402
from steward_datos.persistencia import guardar_extraccion, guardar_resultado  # noqa: E402
from steward_datos.rag.ingesta import ingestar_politica  # noqa: E402
from steward_datos.reglas.catalogo import catalogo  # noqa: E402
from steward_datos.reglas.motor import Contexto, validar_factura, validar_registros  # noqa: E402
from steward_datos.sinteticos import (  # noqa: E402
    anotaciones, contexto_para, factura_desde_anotacion, leer_tabla, registros,
)

MX = ZoneInfo("America/Mexico_City")
USUARIOS = {
    "ana": ("dev-ana", "Ana López"),
    "diego": ("dev-diego", "Diego Ruiz"),
    "luis": ("dev-luis", "Luis Ortega"),
}
MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".xlsx":
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".csv": "text/csv"}
TABLAS = ["resultados_calidad", "reglas_calidad", "catalogo_columnas", "catalogo_tablas", "glosario_terminos", "metricas",
          "consultas_libres", "pagos", "clientes", "usuarios_entidades", "bitacora", "mensajes", "conversaciones", "hallazgos", "campos_extraidos", "conceptos_factura", "facturas",
          "documentos", "casos", "politica_fragmentos", "politicas", "reglas", "ordenes_compra", "centros_costo", "proveedores", "entidades_receptoras"]


def hora(d: date | str, hh: int, mm: int) -> datetime:
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=MX)


def evento(s, caso_id, cuando, accion, detalle, *, usuario=None, tono="info", regla=None, datos=None):
    uid, nombre = USUARIOS[usuario] if usuario else (None, "Agente")
    s.add(EventoBitacora(caso_id=caso_id, fecha=cuando, actor_tipo="usuario" if usuario else ("sistema" if accion == "caso_creado" else "agente"),
                         actor_id=uid, actor_nombre=nombre, accion=accion, tono=tono, detalle=detalle,
                         regla_id=regla[0] if regla else None, regla_version=regla[1] if regla else None, datos=datos))


def crear_caso(s, caso_id, tipo, usuario, cuando, ruta: Path, sha256: str, paginas=1):
    uid, nombre = USUARIOS[usuario]
    c = Caso(id=caso_id, tipo=tipo, estado="procesando", origen="semilla", responsable_id=uid, responsable_nombre=nombre, creado_en=cuando)
    s.add(c)
    s.flush()
    s.add(Documento(caso_id=caso_id, nombre=ruta.name, s3_key=f"casos/{caso_id}/{ruta.name}", mime=MIME[ruta.suffix],
                    tamano_bytes=ruta.stat().st_size, sha256=sha256, paginas=paginas, subido_en=cuando))
    evento(s, caso_id, cuando, "caso_creado", f"Caso creado con {ruta.name}", usuario=usuario)
    return c


def procesar_factura(s, d, usuario, cuando):
    c = crear_caso(s, d["caso_id"], "factura", usuario, cuando, d["_ruta_archivo"], d["sha256"], d["paginas"])
    f = factura_desde_anotacion(d)
    f.modelo = "semilla"
    t = cuando + timedelta(minutes=1)
    guardar_extraccion(s, c.id, f, cuando=t, archivo=d["archivo"])
    r = validar_factura(c.id, f, contexto_para(d))
    guardar_resultado(s, r, cuando=t + timedelta(minutes=1))
    return c, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--embeddings", action="store_true", help="Genera los embeddings de las políticas")
    ap.add_argument("--reiniciar", action="store_true", help="Vacía las tablas antes de cargar")
    args = ap.parse_args()
    if not (CARPETA_SINTETICOS / "facturas" / "demo").exists() or not (CARPETA_SINTETICOS / "negocio").exists():
        sys.exit("Primero genera los datos: python db/semillas/generar_facturas.py, generar_registros.py y generar_negocio.py (en db/semillas/)")

    with sesion() as s:
        if not args.reiniciar and s.execute(text("SELECT count(*) FROM casos")).scalar():
            sys.exit("La base ya tiene casos. Usa --reiniciar para vaciarla y volver a cargar la semilla.")
        if args.reiniciar:
            s.execute(text("ALTER TABLE bitacora DISABLE TRIGGER tr_bitacora_solo_insercion"))
            s.execute(text(f"TRUNCATE {', '.join(TABLAS)} RESTART IDENTITY CASCADE"))
            s.execute(text("ALTER TABLE bitacora ENABLE TRIGGER tr_bitacora_solo_insercion"))

        with open(CARPETA_SINTETICOS / "catalogos" / "proveedores.csv", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                s.merge(Proveedor(rfc=r["rfc"], razon_social=r["razon_social"], activo=r["activo"] == "true", alta=date(2025, 1, 1)))
        with open(CARPETA_SINTETICOS / "catalogos" / "entidades_receptoras.csv", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                s.merge(EntidadReceptora(rfc=r["rfc"], razon_social=r["razon_social"]))

        for r in catalogo().reglas.values():
            s.merge(Regla(id=r.id, version=r.version, nombre=r.nombre, descripcion=r.descripcion, historia=r.historia,
                          politica_id=r.politica_id, politica_version=r.politica_version, seccion=r.seccion, efecto=r.efecto,
                          parametros=r.parametros, activa=True))
        s.flush()

        for ruta in sorted(CARPETA_POLITICAS.glob("*.md")):
            p, accion = ingestar_politica(s, ruta.read_text(encoding="utf-8"), ruta.name, s3_key=f"politicas/{ruta.name}",
                                          con_embeddings=args.embeddings)
            print(f"  política {p.id} v{p.version}: {accion}, {len(p.fragmentos)} fragmentos")

        # Histórico: revisado y confirmado por el responsable
        for i, d in enumerate(anotaciones("historico")):
            usuario = ["ana", "luis"][i % 2]
            cuando = hora(d["fecha_recepcion"], 9 + i % 8, (i * 7) % 60)
            c, r = procesar_factura(s, d, usuario, cuando)
            c.estado, c.resultado_final, c.revisado_por, c.revisado_en = "revisado", r.resultado_sugerido, USUARIOS[usuario][1], cuando + timedelta(hours=2)
            evento(s, c.id, c.revisado_en, "confirmacion", f"Confirmó el resultado sugerido: {r.resultado_sugerido.capitalize()}",
                   usuario=usuario, tono="exito")
        print("  histórico: 30 facturas")

        demo = {d["caso_id"]: d for d in anotaciones("demo") if d["caso_id"]}

        # F-1040: monto alto con total que no cuadra; Luis lo escala y lo rechaza
        c, r = procesar_factura(s, demo["F-1040"], "luis", hora("2026-10-25", 16, 40))
        evento(s, c.id, hora("2026-10-25", 17, 30), "escalamiento", "Caso escalado a supervisión", usuario="luis", tono="error",
               regla=("R-021", "1.2"), datos={"motivo": "Monto mayor al umbral y total que no cuadra"})
        c.estado, c.resultado_final, c.revisado_por, c.revisado_en = "revisado", "rechazado", "Luis Ortega", hora("2026-10-25", 18, 5)
        evento(s, c.id, c.revisado_en, "confirmacion", "Resultado final: Rechazado", usuario="luis", tono="error")

        # F-1041: sin hallazgos, Ana confirma
        c, r = procesar_factura(s, demo["F-1041"], "ana", hora("2026-10-26", 11, 20))
        c.estado, c.resultado_final, c.revisado_por, c.revisado_en = "revisado", "aceptado", "Ana López", hora("2026-10-26", 11, 58)
        evento(s, c.id, c.revisado_en, "confirmacion", "Confirmó el resultado sugerido: Aceptado", usuario="ana", tono="exito")

        # F-1042: en revisión; Ana corrige la fecha leída con baja confianza
        c, r = procesar_factura(s, demo["F-1042"], "ana", hora("2026-10-26", 10, 13))
        campo = s.query(CampoExtraido).filter_by(caso_id="F-1042", campo="fecha").one()
        campo.valor_corregido, campo.corregido_por, campo.corregido_en = "12/08/2026", "Ana López", hora("2026-10-26", 11, 42)
        evento(s, c.id, campo.corregido_en, "correccion", "Campo fecha corregido", usuario="ana", tono="adv", regla=("R-003", "1.0"),
               datos={"texto": "Se corrigió el campo fecha después de verificarlo contra el documento original (página 1).",
                      "antes": "12/03/2026", "despues": "12/08/2026"})
        c.explicacion = ("El total impreso es 400.00 mayor que la suma de subtotal e impuestos, y la fecha no se pudo leer con "
                         "seguridad. El agente no puede determinar si la factura cumple las reglas sin que una persona lo verifique.")

        # V-0207: registros de clientes con 8 correos faltantes
        regs = {d.get("caso_id"): d for d in registros() if d.get("caso_id")}
        d = regs["V-0207"]
        c = crear_caso(s, "V-0207", "validacion", "diego", hora("2026-10-26", 12, 5), d["_ruta_archivo"],
                       hashlib.sha256(d["_ruta_archivo"].read_bytes()).hexdigest())
        r = validar_registros("V-0207", leer_tabla(d["_ruta_archivo"]), Contexto(fecha_recepcion=date(2026, 10, 26)))
        guardar_resultado(s, r, cuando=hora("2026-10-26", 12, 7),
                          explicacion="El archivo no cumple la política P-007 porque 8 registros no tienen correo de contacto. "
                                      "Las otras políticas se cumplen.")

        # V-0206: archivo ilegible
        d = regs["V-0206"]
        c = crear_caso(s, "V-0206", "validacion", "diego", hora("2026-10-25", 16, 1), d["_ruta_archivo"],
                       hashlib.sha256(d["_ruta_archivo"].read_bytes()).hexdigest())
        c.estado, c.error_detalle = "error", "No se pudo leer registros_prueba.csv: el contenido no es texto UTF-8 ni Excel."
        evento(s, c.id, hora("2026-10-25", 16, 2), "error", "No se pudo leer registros_prueba.csv", tono="error")
        print("  demo: F-1040, F-1041, F-1042, V-0206, V-0207")

        print(f"  negocio: {cargar_negocio(s)}")
        print(f"  catálogo: {cargar_catalogo(s)} tablas · glosario: {cargar_glosario(s)} términos · "
              f"métricas: {cargar_metricas(s)} · reglas de calidad: {cargar_calidad(s)}")

    with sesion() as s:
        for t in ("casos", "hallazgos", "bitacora", "politica_fragmentos", "pagos", "clientes", "resultados_calidad"):
            print(f"  {t}: {s.execute(text(f'SELECT count(*) FROM {t}')).scalar()}")


if __name__ == "__main__":
    main()
