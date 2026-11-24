from pathlib import Path
import re
import sqlglot
from sqlglot import exp

CARPETA = Path("experimentos/text-to-sql/segunda_prueba")

VISTAS_PERMITIDAS = {
    "v_facturas", "v_proveedores", "v_casos", "v_hallazgos",
    "v_ordenes_compra", "v_pagos", "v_centros_costo", "v_clientes"
}

archivos = sorted(CARPETA.glob("pregunta_*.sql"))
resultados = []

for archivo in archivos:
    sql = archivo.read_text(encoding="utf-8-sig")
    sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE).strip()

    try:
        sentencias = [s for s in sqlglot.parse(sql, read="postgres") if s]

        if len(sentencias) != 1:
            raise ValueError(f"Se encontraron {len(sentencias)} sentencias")

        consulta = sentencias[0]
        es_select = isinstance(consulta, exp.Select)
        tablas = {t.name.lower() for t in consulta.find_all(exp.Table)}
        vistas_validas = tablas.issubset(VISTAS_PERMITIDAS)
        tiene_limit = consulta.args.get("limit") is not None

        valido = es_select and vistas_validas and tiene_limit
        resultados.append(valido)

        print(f"\n{archivo.name}")
        print(f"  Sintaxis: OK")
        print(f"  SELECT: {'OK' if es_select else 'ERROR'}")
        print(f"  Vistas: {'OK' if vistas_validas else 'ERROR'}")
        print(f"  LIMIT: {'OK' if tiene_limit else 'ERROR'}")
        print(f"  Tablas: {sorted(tablas)}")

    except Exception as error:
        resultados.append(False)
        print(f"\n{archivo.name}: ERROR - {error}")

print("\n==============================")
print(f"Consultas evaluadas: {len(archivos)}")
print(f"Consultas estructuralmente validas: {sum(resultados)}/{len(archivos)}")
