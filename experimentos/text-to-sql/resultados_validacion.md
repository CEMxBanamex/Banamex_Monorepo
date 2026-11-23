# Validacion estructural de text-to-SQL

Modelo: qwen2.5-coder:7b
Total de consultas: 10

## Resultados

- Sintaxis SQL valida: 10/10 (100%)
- Uso exclusivo de vistas permitidas: 10/10 (100%)
- Consultas con LIMIT: 9/10 (90%)
- Consultas estructuralmente validas: 9/10 (90%)

## Incidencias

- Pregunta 05: la consulta no contiene LIMIT.

## Observacion

La validez estructural no garantiza la correccion semantica.
Todavia deben comprobarse los nombres de columnas, las relaciones,
los filtros y la correspondencia entre cada consulta y su pregunta.
