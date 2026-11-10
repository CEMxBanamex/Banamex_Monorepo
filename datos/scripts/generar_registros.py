"""Genera archivos de registros de clientes para la Historia 2, con errores intencionales y verdad de referencia.

Salida en datos/sinteticos/registros/: un .xlsx o .csv por caso y un .json con lo esperado.
clientes_octubre.xlsx reproduce el caso V-0207 del frontend (8 de 120 sin correo, filas 14, 27, 33, 48, 61, 79, 95 y 112).
registros_prueba.csv reproduce V-0206: un archivo que no se puede leer.
"""
import argparse
import csv
import json
import random
import shutil
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from faker import Faker
from openpyxl import Workbook

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.config import CARPETA_SINTETICOS  # noqa: E402

FECHA_VALIDACION = date(2026, 11, 2)
COLUMNAS = ["id_cliente", "nombre", "rfc", "correo_contacto", "alta"]


class Gen:
    def __init__(self, semilla):
        self.rnd = random.Random(semilla)
        self.fake = Faker("es_MX")
        self.fake.seed_instance(semilla)

    def rfc(self, nombre: str, fisica: bool, nacimiento: date) -> str:
        limpio = unicodedata.normalize("NFD", nombre).encode("ascii", "ignore").decode().upper()
        letras = "".join(c for c in limpio if c.isalpha())
        base = (letras[:4] if fisica else letras[:3]).ljust(4 if fisica else 3, "X")
        homo = "".join(self.rnd.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(3))
        return f"{base}{nacimiento:%y%m%d}{homo}"

    def cliente(self, n: int, alta_desde=date(2026, 10, 1), alta_hasta=date(2026, 10, 31)) -> dict:
        fisica = self.rnd.random() < 0.6
        nombre = self.fake.name() if fisica else f"{self.fake.last_name()} {self.rnd.choice(['Comercial', 'Industrial', 'Logística'])} SA de CV"
        nac = date(self.rnd.randint(1960, 2004), self.rnd.randint(1, 12), self.rnd.randint(1, 28))
        usuario = unicodedata.normalize("NFD", nombre.split()[0]).encode("ascii", "ignore").decode().lower()
        alta = alta_desde + timedelta(days=self.rnd.randint(0, (alta_hasta - alta_desde).days))
        return {"id_cliente": f"C-{n:05d}", "nombre": nombre, "rfc": self.rfc(nombre, fisica, nac),
                "correo_contacto": f"{usuario}{n}@{self.rnd.choice(['ejemplo.mx', 'correo.com', 'empresa.com.mx'])}",
                "alta": alta.strftime("%d/%m/%Y")}


def escribir(ruta: Path, columnas: list[str], filas: list[dict], hoja="clientes"):
    if ruta.suffix == ".csv":
        with open(ruta, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, columnas)
            w.writeheader()
            w.writerows(filas)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = hoja
        ws.append(columnas)
        for f in filas:
            ws.append([f.get(c) for c in columnas])
        for col, ancho in zip("ABCDEF", (12, 34, 16, 34, 12, 14)):
            ws.column_dimensions[col].width = ancho
        wb.save(ruta)


def casos(g: Gen) -> list[dict]:
    out = []

    def caso(archivo, escenario, descripcion, filas, esperado_res, esperado_reglas, filas_esperadas=None, columnas=COLUMNAS,
             caso_id=None, hoja="clientes"):
        out.append({"archivo": archivo, "escenario": escenario, "descripcion": descripcion, "_filas": filas,
                    "_columnas": columnas, "hoja": hoja if archivo.endswith(".xlsx") else None, "caso_id": caso_id,
                    "fecha_recepcion": FECHA_VALIDACION.isoformat(),
                    "esperado": {"resultado": esperado_res, "reglas": sorted(esperado_reglas), "filas": filas_esperadas or {}}})

    faltan = [14, 27, 33, 48, 61, 79, 95, 112]
    filas = [g.cliente(i) for i in range(1, 121)]
    for i in faltan:
        filas[i - 1]["correo_contacto"] = None
    caso("clientes_octubre.xlsx", "correo_faltante", "8 de 120 clientes sin correo (caso V-0207 del frontend)", filas,
         "rechazado", ["R-101"], {"R-101": faltan}, caso_id="V-0207")

    caso("clientes_septiembre.xlsx", "correcto", "Archivo que cumple todas las políticas",
         [g.cliente(200 + i, date(2026, 9, 1), date(2026, 9, 30)) for i in range(80)], "aceptado", [])

    filas = [g.cliente(300 + i) for i in range(60)]
    malos = [5, 18, 40]
    filas[4]["rfc"] = filas[4]["rfc"][:-1]
    filas[17]["rfc"] = filas[17]["rfc"][:4] + "991332" + filas[17]["rfc"][10:] if len(filas[17]["rfc"]) == 13 else filas[17]["rfc"][:3] + "991332" + filas[17]["rfc"][9:]
    filas[39]["rfc"] = "RFC-PENDIENTE"
    caso("clientes_rfc.csv", "rfc_invalido", "3 RFC con estructura inválida", filas, "rechazado", ["R-103"], {"R-103": malos})

    filas = [g.cliente(400 + i) for i in range(50)]
    filas[9]["alta"] = "31/02/2026"
    filas[21]["alta"] = "2026-13-01"
    filas[30]["alta"] = "15/12/2026"
    filas[44]["alta"] = "03/05/1998"
    caso("clientes_fechas.xlsx", "fechas_invalidas", "Fechas de alta inexistentes, futuras y anteriores a 2000", filas,
         "rechazado", ["R-104"], {"R-104": [10, 22, 31, 45]})

    filas = [g.cliente(500 + i) for i in range(40)]
    filas[25]["id_cliente"] = filas[3]["id_cliente"]
    filas[33]["id_cliente"] = filas[3]["id_cliente"].lower() + " "
    filas[38]["id_cliente"] = filas[11]["id_cliente"]
    caso("clientes_duplicados.csv", "id_duplicado", "Identificadores repetidos (uno con minúsculas y espacio)", filas,
         "rechazado", ["R-105"], {"R-105": [4, 12, 26, 34, 39]})

    filas = [g.cliente(600 + i) for i in range(30)]
    filas[6]["correo_contacto"] = "ventas.empresa.com"
    filas[19]["correo_contacto"] = "contacto @correo.com"
    caso("clientes_correo_formato.xlsx", "correo_formato", "Correos sin @ o con espacios", filas, "rechazado", ["R-102"],
         {"R-102": [7, 20]})

    filas = [{k: v for k, v in g.cliente(700 + i).items() if k != "correo_contacto"} for i in range(25)]
    caso("clientes_sin_columna.csv", "columna_faltante", "Falta la columna correo_contacto",
         filas, "rechazado", ["R-106"], columnas=["id_cliente", "nombre", "rfc", "alta"])

    filas = [g.cliente(800 + i) for i in range(45)]
    renombrar = {"id_cliente": "numero_cliente", "nombre": "razon_social", "correo_contacto": "email", "alta": "fecha_alta"}
    filas = [{renombrar.get(k, k): v for k, v in f.items()} for f in filas]
    caso("clientes_alias.xlsx", "alias_columnas", "Columnas con nombres alternativos aceptados", filas, "aceptado", [],
         columnas=["numero_cliente", "razon_social", "rfc", "email", "fecha_alta"])

    filas = [g.cliente(900 + i) for i in range(70)]
    filas[2]["nombre"] = None
    filas[8]["correo_contacto"] = None
    filas[15]["rfc"] = "ABC12"
    filas[40]["id_cliente"] = filas[41]["id_cliente"]
    filas[60]["alta"] = "01/01/2027"
    caso("clientes_mixto.xlsx", "varios_errores", "Varios errores en el mismo archivo", filas, "rechazado",
         ["R-101", "R-103", "R-104", "R-105"], {"R-101": [3, 9], "R-103": [16], "R-104": [61], "R-105": [41, 42]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--salida", type=Path, default=CARPETA_SINTETICOS)
    args = ap.parse_args()
    carpeta = args.salida / "registros"
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)

    indice = []
    for c in casos(Gen(args.semilla)):
        ruta = carpeta / c["archivo"]
        escribir(ruta, c["_columnas"], c["_filas"])
        reg = {k: v for k, v in c.items() if not k.startswith("_")}
        reg["grupo"] = "demo" if c["caso_id"] else "evaluacion"
        reg["total_registros"] = len(c["_filas"])
        reg["columnas"] = c["_columnas"]
        (carpeta / f"{ruta.stem}.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
        indice.append(reg)

    # V-0206: archivo ilegible (bytes binarios con extensión .csv). El caso debe terminar en estado error, no en un resultado.
    (carpeta / "registros_prueba.csv").write_bytes(bytes(random.Random(7).randrange(256) for _ in range(4096)))
    reg = {"archivo": "registros_prueba.csv", "escenario": "archivo_ilegible", "caso_id": "V-0206", "grupo": "demo",
           "descripcion": "Archivo que no se puede leer (caso V-0206 del frontend)", "fecha_recepcion": FECHA_VALIDACION.isoformat(),
           "esperado": {"resultado": None, "estado": "error", "reglas": []}}
    (carpeta / "registros_prueba.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    indice.append(reg)
    (args.salida / "casos_referencia_registros.json").write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(indice)} archivos de registros en {carpeta}")


if __name__ == "__main__":
    main()
