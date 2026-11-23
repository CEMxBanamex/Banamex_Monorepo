# Evaluación inicial de text-to-SQL

Modelo: qwen2.5-coder:7b
Preguntas: 10
Vistas permitidas: v_facturas, v_proveedores, v_casos, v_hallazgos, v_ordenes_compra, v_pagos, v_centros_costo, v_clientes

| Pregunta | Resultado | Observación |
|---|---|---|
| 1 | Parcial | Cuenta facturas, pero no agrupa por resultado. |
| 2 | Incorrecta | Columnas inexistentes en v_proveedores y v_facturas. |
| 3 | Pendiente de validación | Conteo conceptual correcto; verificar valor de rechazo. |
| 4 | Incorrecta | Columnas inexistentes y confusión entre pago y conciliación. |
| 5 | Incorrecta | Debía utilizar horas_revision. |
| 6 | Correcta conceptual | Agrupa por regla y cuenta hallazgos. |
| 7 | Incorrecta | Columnas y estado no respaldados por el catálogo. |
| 8 | Incorrecta | Columnas de relación inexistentes. |
| 9 | Incorrecta | Columnas inexistentes y fuente incorrecta. |
| 10 | Incorrecta | Columnas inexistentes y JOIN innecesario. |

Aciertos confirmados: 1/10.
Aciertos conceptuales adicionales pendientes de validación: pregunta 3.
