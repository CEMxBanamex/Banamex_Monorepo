"""Genera los datos de negocio sintéticos para las consultas del chat (capa semántica y vistas consultables).

Salida en datos/sinteticos/negocio/:
  centros_costo.csv, proveedores_detalle.csv, ordenes_compra.csv, clientes.csv, usuarios_entidades.csv
  facturas_negocio.jsonl  12 meses de facturas (nov. 2025 a oct. 2026) ya revisadas, sin archivo, con su orden de compra,
                          la decisión del analista cuando hubo revisión humana y el pago de Tesorería.

Las facturas se cargan como casos con origen "negocio" (IDs F-0001 a F-0960) y la semilla les aplica el mismo motor de
reglas que al resto, así que las métricas por regla salen de hallazgos reales.

Uso:  python scripts/generar_negocio.py [--semilla 2026]
"""
import argparse
import csv
import json
import random
import sys
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from faker import Faker

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.config import CARPETA_SINTETICOS  # noqa: E402

FECHA_CORTE = date(2026, 11, 2)
D = Decimal

CENTROS = [
    ("CC-110", "Tecnología", "Dirección de Tecnología", "GFD960701AB4", 9_500_000),
    ("CC-120", "Operaciones", "Dirección de Operaciones", "GFD960701AB4", 6_200_000),
    ("CC-130", "Recursos Humanos", "Dirección de Personas", "GFD960701AB4", 2_400_000),
    ("CC-210", "Banca Comercial", "Dirección Comercial", "BDM970315QW2", 7_800_000),
    ("CC-220", "Riesgos", "Dirección de Riesgos", "BDM970315QW2", 3_100_000),
    ("CC-230", "Cumplimiento", "Dirección de Cumplimiento", "BDM970315QW2", 2_000_000),
    ("CC-310", "Servicios Generales", "Dirección de Administración", "SCD050920LM8", 4_300_000),
    ("CC-320", "Compras", "Dirección de Administración", "SCD050920LM8", 1_500_000),
]

CATEGORIAS = {
    "Tecnología": [("Licencia anual de software", 8_000, 60_000), ("Hospedaje de servidores", 4_000, 25_000),
                   ("Soporte técnico mensual", 3_000, 18_000), ("Desarrollo de reporte analítico", 10_000, 45_000)],
    "Consultoría": [("Servicio de consultoría", 12_000, 80_000), ("Auditoría de seguridad informática", 25_000, 90_000),
                    ("Capacitación en línea", 5_000, 20_000)],
    "Servicios generales": [("Servicio de limpieza", 6_000, 18_000), ("Servicio de cafetería", 2_000, 9_000),
                            ("Mantenimiento preventivo de equipo", 3_000, 15_000), ("Mensajería y paquetería", 400, 4_000)],
    "Suministros": [("Papelería y artículos de oficina", 500, 6_000), ("Renta de equipo de cómputo", 4_000, 14_000),
                    ("Traducción de documentos", 1_500, 9_000)],
}
CENTROS_POR_CATEGORIA = {
    "Tecnología": ["CC-110", "CC-210", "CC-220"], "Consultoría": ["CC-110", "CC-220", "CC-230", "CC-130"],
    "Servicios generales": ["CC-310", "CC-120"], "Suministros": ["CC-320", "CC-120", "CC-130", "CC-210"],
}
USUARIOS = [  # usuario_id, nombre, rol, entidades
    ("dev-ana", "Ana López", "analista", ["GFD960701AB4", "BDM970315QW2", "CPR180301KJ7"]),
    ("dev-luis", "Luis Ortega", "analista", ["SCD050920LM8"]),
    ("dev-diego", "Diego Ruiz", "analista", ["GFD960701AB4", "BDM970315QW2", "SCD050920LM8", "CPR180301KJ7"]),
    ("dev-admin", "Administrador Demo", "administrador", []),
]
RESPONSABLE_POR_ENTIDAD = {"GFD960701AB4": "dev-ana", "BDM970315QW2": "dev-ana", "SCD050920LM8": "dev-luis"}


def r2(v) -> Decimal:
    return D(v).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def fmt(v: Decimal) -> str:
    return f"{v:,.2f}"


def leer_proveedores() -> list[dict]:
    with open(CARPETA_SINTETICOS / "catalogos" / "proveedores.csv", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--facturas-por-mes", type=int, default=80)
    args = ap.parse_args()
    rnd = random.Random(args.semilla)
    fake = Faker("es_MX")
    fake.seed_instance(args.semilla)
    salida = CARPETA_SINTETICOS / "negocio"
    salida.mkdir(parents=True, exist_ok=True)

    # Proveedores: categoría, contacto, plazo y peso (unos cuantos concentran el gasto, como en la realidad)
    proveedores = []
    for i, p in enumerate(leer_proveedores()):
        cat = "Consultoría" if p["razon_social"] == "Proveedor Demo SA" else list(CATEGORIAS)[i % 4]
        dominio = p["razon_social"].split()[0].lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        proveedores.append({**p, "categoria": cat, "correo_contacto": f"facturacion@{dominio}.com.mx",
                            "plazo_pago_dias": rnd.choice([15, 30, 30, 45]), "peso": rnd.choice([1, 1, 1, 2, 3, 6])})
    with open(salida / "proveedores_detalle.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["rfc", "categoria", "correo_contacto", "plazo_pago_dias"])
        w.writeheader()
        w.writerows({k: p[k] for k in w.fieldnames} for p in proveedores)

    with open(salida / "centros_costo.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "nombre", "area", "entidad_rfc", "responsable", "presupuesto_anual"])
        for cid, nombre, area, ent, pres in CENTROS:
            w.writerow([cid, nombre, area, ent, fake.name(), f"{pres:.2f}"])
    centros = {c[0]: c for c in CENTROS}

    with open(salida / "usuarios_entidades.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["usuario_id", "nombre", "rol", "entidad_rfc"])
        for uid, nombre, rol, ents in USUARIOS:
            for e in ents or [""]:
                w.writerow([uid, nombre, rol, e])

    # Facturas de 12 meses con su orden de compra y su pago
    ordenes, facturas = [], []
    folios = {}
    n = 0
    pesos = [p["peso"] for p in proveedores]
    for m in range(12):
        inicio = date(2025 + (10 + m) // 12, (10 + m) % 12 + 1, 1)
        fin = date(inicio.year + inicio.month // 12, inicio.month % 12 + 1, 1) - timedelta(days=1)
        for _ in range(args.facturas_por_mes):
            n += 1
            p = rnd.choices(proveedores, weights=pesos)[0]
            cc = rnd.choice(CENTROS_POR_CATEGORIA[p["categoria"]])
            entidad = centros[cc][3]
            fecha = inicio + timedelta(days=rnd.randint(0, (fin - inicio).days))
            conceptos = []
            for desc, lo, hi in rnd.sample(CATEGORIAS[p["categoria"]], rnd.randint(1, 3)):
                cant = D(rnd.choice([1, 1, 1, 2, 3]))
                precio = r2(rnd.uniform(lo, hi))
                conceptos.append({"descripcion": desc, "cantidad": f"{cant:g}", "precio_unitario": fmt(precio), "importe": fmt(r2(cant * precio))})
            subtotal = sum((D(c["importe"].replace(",", "")) for c in conceptos), D(0))
            moneda = "USD" if p["categoria"] == "Tecnología" and rnd.random() < 0.25 else "MXN"
            if moneda == "USD":
                subtotal = r2(subtotal / D("18.5"))
                conceptos = [{**c, "precio_unitario": fmt(r2(D(c["precio_unitario"].replace(",", "")) / D("18.5"))),
                              "importe": fmt(r2(D(c["importe"].replace(",", "")) / D("18.5")))} for c in conceptos]
                subtotal = sum((D(c["importe"].replace(",", "")) for c in conceptos), D(0))
            tasa = D("0.08") if rnd.random() < 0.06 else D("0.16")
            impuestos = r2(subtotal * tasa)
            total = subtotal + impuestos
            folio = f"{p['rfc'][:3]}-{rnd.randint(1000, 99999)}"
            conf = {c: rnd.randint(88, 99) for c in ("folio", "fecha", "emisor_nombre", "emisor_rfc", "receptor_nombre", "receptor_rfc",
                                                     "moneda", "subtotal", "impuestos", "tasa_iva", "total")}
            escenario = "correcta"
            x = rnd.random()
            impreso_total, impreso_impuestos, impreso_folio = total, impuestos, folio
            if x < 0.03:
                escenario, impreso_total = "total_no_cuadra", total + D(rnd.choice([50, 200, 1000]))
            elif x < 0.05:
                escenario, impreso_impuestos = "iva_incorrecto", r2(impuestos * D("1.07"))
                impreso_total = subtotal + impreso_impuestos
            elif x < 0.06:
                escenario, impreso_folio = "sin_folio", None
            elif x < 0.07 and folios:
                escenario = "duplicado_folio"
                rfc_prev, impreso_folio = rnd.choice([k for k in folios if k[0] == p["rfc"]] or [(p["rfc"], folio)])
            elif x < 0.10:
                escenario = "baja_confianza"
                for c in rnd.sample(["fecha", "total", "folio"], 1):
                    conf[c] = rnd.randint(55, 76)
            if impreso_folio:
                folios[(p["rfc"], impreso_folio)] = n

            oc_id = None
            if rnd.random() < 0.9:
                oc_id = f"OC-{fecha.year}-{n:05d}"
                monto_oc = impreso_total if rnd.random() < 0.95 else r2(impreso_total * D(rnd.choice(["0.9", "1.1"])))
                ordenes.append({"id": oc_id, "proveedor_rfc": p["rfc"], "entidad_rfc": entidad, "centro_costo_id": cc,
                                "fecha": (fecha - timedelta(days=rnd.randint(5, 40))).isoformat(),
                                "descripcion": conceptos[0]["descripcion"], "moneda": moneda, "monto": str(monto_oc), "estado": "facturada"})

            recibida = datetime.combine(fecha + timedelta(days=rnd.randint(1, 5)), time(rnd.randint(8, 18), rnd.randint(0, 59)))
            horas = rnd.uniform(0.3, 40) if rnd.random() < 0.92 else rnd.uniform(48, 150)
            revisada = recibida + timedelta(hours=horas)
            facturas.append({
                "caso_id": f"F-{n:04d}", "escenario": escenario, "emisor_rfc": p["rfc"], "emisor_nombre": p["razon_social"],
                "receptor_rfc": entidad, "centro_costo_id": cc, "orden_compra_id": oc_id, "plazo_pago_dias": int(p["plazo_pago_dias"]),
                "campos": {
                    "folio": impreso_folio, "fecha": f"{fecha:%d/%m/%Y}", "emisor_nombre": p["razon_social"], "emisor_rfc": p["rfc"],
                    "receptor_nombre": next(c for c in [("GFD960701AB4", "Grupo Financiero Demo SA de CV"),
                                                        ("BDM970315QW2", "Banco Demo SA, Institución de Banca Múltiple"),
                                                        ("SCD050920LM8", "Servicios Corporativos Demo SA de CV")] if c[0] == entidad)[1],
                    "receptor_rfc": entidad, "moneda": moneda, "subtotal": fmt(subtotal), "impuestos": fmt(impreso_impuestos),
                    "tasa_iva": f"IVA {tasa * 100:.0f} %", "total": fmt(impreso_total),
                },
                "confianza": conf, "conceptos": conceptos,
                "recibida_en": recibida.isoformat(), "revisada_en": revisada.isoformat() if revisada.date() <= FECHA_CORTE else None,
                "responsable": RESPONSABLE_POR_ENTIDAD[entidad],
                # Si el motor sugiere revisión humana, esta es la decisión del analista
                "decision_humana": "aceptado" if rnd.random() < 0.7 else "rechazado",
                "pago_atraso_dias": 0 if rnd.random() < 0.87 else rnd.randint(1, 20),
                "pago_difiere": rnd.random() < 0.02,
            })

    with open(salida / "ordenes_compra.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(ordenes[0]))
        w.writeheader()
        w.writerows(ordenes)
    with open(salida / "facturas_negocio.jsonl", "w", encoding="utf-8") as fh:
        for f in facturas:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")

    # Clientes ya dados de alta, con algunos problemas de calidad a propósito
    clientes = []
    for i in range(600):
        fisica = rnd.random() < 0.65
        nombre = fake.name() if fisica else f"{fake.last_name()} {rnd.choice(['Comercial', 'Industrial', 'Logística', 'Agropecuaria'])} SA de CV"
        limpio = "".join(c for c in nombre.upper().encode("ascii", "ignore").decode() if c.isalpha())
        nac = date(rnd.randint(1955, 2005), rnd.randint(1, 12), rnd.randint(1, 28))
        rfc = (limpio[:4] if fisica else limpio[:3]) + f"{nac:%y%m%d}" + "".join(rnd.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(3))
        correo = f"{limpio[:6].lower()}{i}@{rnd.choice(['correo.com', 'ejemplo.mx', 'empresa.com.mx'])}"
        alta = date(rnd.randint(2003, 2026), rnd.randint(1, 12), rnd.randint(1, 28))
        alta = min(alta, FECHA_CORTE)
        r = rnd.random()
        if r < 0.015:
            correo = ""
        elif r < 0.022:
            rfc = rfc[:-2]
        elif r < 0.025:
            alta = None
        elif r < 0.030:
            correo = correo.replace("@", " at ")
        clientes.append({"id_cliente": f"C-{10001 + i}", "nombre": nombre, "tipo_persona": "fisica" if fisica else "moral",
                         "rfc": rfc, "correo_contacto": correo, "segmento": rnd.choice(["Personas", "Personas", "PyME", "Empresarial", "Gobierno"]),
                         "entidad_rfc": rnd.choice(["GFD960701AB4", "BDM970315QW2", "BDM970315QW2", "SCD050920LM8"]),
                         "alta": alta.isoformat() if alta else "", "activo": "true" if rnd.random() < 0.93 else "false"})
    with open(salida / "clientes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(clientes[0]))
        w.writeheader()
        w.writerows(clientes)

    esc = {}
    for f in facturas:
        esc[f["escenario"]] = esc.get(f["escenario"], 0) + 1
    print(f"{len(facturas)} facturas de negocio, {len(ordenes)} órdenes de compra, {len(clientes)} clientes en {salida}")
    print(json.dumps(esc, ensure_ascii=False))


if __name__ == "__main__":
    main()
