from pathlib import Path
import re
import sqlglot
from sqlglot import exp

CARPETA = Path("experimentos/text-to-sql")

VISTAS_PERMITIDAS = {
    "v_facturas",
    "v_proveedores",
    "v_casos",
    "v_hallazgos",
    "v_ordenes_compra",
    "v_pagos",
    "v_centros_costo",
    "v_clientes",
}

def limpiar_sql(texto):
    texto = re.sub(r"```(?:sql)?", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"--.*$", "", texto, flags=re.MULTILINE)
    return texto.strip()

archivos = sorted(CARPETA.glob("pregunta_*.sql"))

resultados = []

for archivo in archivos:
    sql = limpiar_sql(archivo.read_text(encoding="utf-8-sig"))

    try:
        sentencias = sqlglot.parse(sql, read="postgres")
        sentencias = [s for s in sentencias if s is not None]

        if len(sentencias) != 1:
            raise ValueError(f"Se esperó 1 sentencia y se encontraron {len(sentencias)}")

        consulta = sentencias[0]

        es_select = isinstance(consulta, exp.Select)
        tablas = {
            tabla.name.lower()
            for tabla in consulta.find_all(exp.Table)
        }
        vistas_validas = tablas.issubset(VISTAS_PERMITIDAS)
        tiene_limit = consulta.args.get("limit") is not None

        valido = es_select and vistas_validas and tiene_limit

        print(f"\n{archivo.name}")
        print(f"  Sintaxis: OK")
        print(f"  SELECT: {'OK' if es_select else 'ERROR'}")
        print(f"  Vistas: {'OK' if vistas_validas else 'ERROR'}")
        print(f"  LIMIT: {'OK' if tiene_limit else 'ERROR'}")
        print(f"  Tablas detectadas: {sorted(tablas)}")

        resultados.append(valido)

    except Exception as error:
        print(f"\n{archivo.name}")
        print(f"  ERROR: {error}")
        resultados.append(False)

print("\n==============================")
print(f"Consultas evaluadas: {len(archivos)}")
print(f"Consultas estructuralmente validas: {sum(resultados)}/{len(archivos)}")
