from pathlib import Path
import re
import sqlglot

archivo = Path("experimentos/text-to-sql/referencias.sql")
contenido = archivo.read_text(encoding="utf-8-sig")

# Eliminar comentarios SQL de una linea
contenido = re.sub(r"--.*$", "", contenido, flags=re.MULTILINE)

# Separar las sentencias por punto y coma
consultas = [
    q.strip()
    for q in contenido.split(";")
    if q.strip()
]

correctas = 0

for i, consulta in enumerate(consultas, start=1):
    try:
        sqlglot.parse_one(consulta, read="postgres")
        print(f"[OK] Consulta {i:02d}: sintaxis valida")
        correctas += 1
    except Exception as error:
        print(f"[ERROR] Consulta {i:02d}: {error}")

print(f"\nResultado: {correctas}/{len(consultas)} consultas validas")
