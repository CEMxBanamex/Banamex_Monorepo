# Evaluacion semantica - Segunda prueba

Modelo: qwen2.5-coder:7b
Contexto: esquema de vistas y reglas semanticas
Preguntas: 10

| Pregunta | Resultado | Observacion |
|---|---|---|
| 1 | Correcta | Agrupa facturas por resultado. |
| 2 | Parcial | JOIN potencialmente excluyente; v_facturas ya contiene proveedor. |
| 3 | Correcta | Utiliza resultado = rechazado. |
| 4 | Incorrecta | Riesgo de division entera en el calculo porcentual. |
| 5 | Correcta | Utiliza AVG(horas_revision) y filtra revisadas. |
| 6 | Correcta | Cuenta casos distintos por regla. |
| 7 | Correcta | Utiliza los estados oficiales de casos pendientes. |
| 8 | Incorrecta | Omite conversion de USD a MXN. |
| 9 | Correcta | Ordena centros por comprometido_mxn. |
| 10 | Correcta | Filtra clientes activos y agrupa por segmento. |

## Resultados

- Consultas completamente correctas: 7/10 (70%).
- Consultas parcialmente correctas: 1/10.
- Consultas incorrectas: 2/10.
- Sintaxis valida: 10/10.
- Validez estructural: 10/10.

## Conclusion

El contexto del esquema y las reglas semanticas mejoro la generacion SQL.
El modelo reconocio correctamente las columnas, los estados y las vistas.
Persisten errores relacionados con la precision aritmetica y la conversion
de monedas, ademas de un JOIN potencialmente innecesario.
La evaluacion fue estatica; no se ejecutaron las consultas en PostgreSQL.
