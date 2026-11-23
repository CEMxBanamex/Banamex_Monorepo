# Evaluacion semantica de text-to-SQL

Modelo: qwen2.5-coder:7b
Total de preguntas: 10

| Pregunta | Resultado | Problema |
|---|---|---|
| 1 | Incorrecta | No agrupa las facturas por resultado. |
| 2 | Incorrecta | Columnas inexistentes: id_proveedor, nombre_proveedor, monto_factura. |
| 3 | Incorrecta | Filtra por estado en lugar de resultado. |
| 4 | Incorrecta | Columnas inexistentes: id_factura y pagado. |
| 5 | Incorrecta | Utiliza fechas inexistentes en lugar de horas_revision. |
| 6 | Incorrecta | id_hallazgo no existe; debe utilizar hallazgo_id y contar casos distintos. |
| 7 | Incorrecta | Utiliza id en lugar de caso_id y un estado incorrecto. |
| 8 | Incorrecta | Columnas inexistentes para relacionar pagos y proveedores. |
| 9 | Incorrecta | Utiliza una fuente y columnas incorrectas para el monto comprometido. |
| 10 | Incorrecta | JOIN con columna inexistente y filtro incorrecto para clientes activos. |

## Resultados

- Consultas completamente correctas: 0/10 (0%).
- Consultas sintacticamente validas: 10/10 (100%).
- Consultas estructuralmente validas: 9/10 (90%).

## Conclusion

El modelo demuestra capacidad para generar consultas SQL con sintaxis PostgreSQL,
pero presenta dificultades para identificar las columnas disponibles,
establecer relaciones correctas entre vistas y respetar la semantica
de las metricas del proyecto.

La evaluacion es estatica y se basa en el catalogo de vistas,
la migracion 0002 y metricas.yaml. No se han ejecutado las consultas
contra PostgreSQL.
