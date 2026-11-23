# S1-31 - Comparacion de experimentos Text-to-SQL

## 1. Configuracion experimental

- Modelo: qwen2.5-coder:7b
- Ejecuciones: 2
- Preguntas por ejecucion: 10
- Dialecto SQL: PostgreSQL
- Herramienta de validacion: SQLGlot 30.33.0

### Primera prueba
Prompt sin contexto detallado del esquema.

### Segunda prueba
Prompt con:
- Columnas de las ocho vistas disponibles.
- Reglas semanticas de metricas.yaml.
- Restricciones de generacion SQL.
- Uso exclusivo de SELECT y LIMIT 100.

## 2. Comparacion de resultados

| Indicador | Primera prueba | Segunda prueba |
|---|---:|---:|
| Consultas generadas | 10/10 | 10/10 |
| Sintaxis SQL valida | 10/10 | 10/10 |
| Uso exclusivo de vistas permitidas | 10/10 | 10/10 |
| Uso de LIMIT | 9/10 | 10/10 |
| Validez estructural completa | 9/10 | 10/10 |
| Correccion semantica completa | 0/10 | 7/10 |

## 3. Evaluacion semantica

### Primera prueba
- Correctas: 0
- Parciales: 0
- Incorrectas: 10
- Precision semantica: 0%

### Segunda prueba
- Correctas: 7
- Parciales: 1
- Incorrectas: 2
- Precision semantica estricta: 70%

La pregunta 2 de la segunda prueba se considera parcial porque utiliza un JOIN valido, pero potencialmente excluye proveedores sin coincidencia, aunque v_facturas ya contiene el nombre del proveedor.

La pregunta 4 presenta riesgo de division entera al calcular la tasa de conciliacion.

La pregunta 8 omite la conversion de USD a MXN con el tipo de cambio de 18.50.

## 4. Interpretacion

La incorporacion del esquema de las vistas y las reglas semanticas
mejoro el desempeno del modelo.

La precision semantica paso de 0% a 70%, mientras que la validez
estructural completa paso de 90% a 100%.

Los resultados sugieren que proporcionar contexto explicito sobre
las columnas disponibles y las reglas de negocio reduce los errores
de generacion SQL.

## 5. Limitaciones

- Se evaluaron solamente diez preguntas.
- La evaluacion semantica fue estatica.
- No se ejecutaron las consultas contra PostgreSQL.
- No se verificaron los resultados numericos sobre datos reales.
- La prueba no mide generalizacion a preguntas diferentes.

## 6. Conclusion

El modelo qwen2.5-coder:7b puede generar consultas PostgreSQL
sintacticamente validas, pero su precision semantica depende
considerablemente del contexto proporcionado.

La segunda prueba demuestra una mejora importante al incorporar
el esquema de las vistas y las reglas semanticas del proyecto.

Para una implementacion real, se recomienda complementar la
generacion con validacion de columnas, restricciones de seguridad,
validacion semantica y pruebas de ejecucion controladas.
