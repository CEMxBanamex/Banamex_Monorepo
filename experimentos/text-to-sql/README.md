# S1-31 - Experimento Text-to-SQL con Ollama

## Objetivo

Evaluar la capacidad del modelo local `qwen2.5-coder:7b` para convertir preguntas en lenguaje natural a consultas PostgreSQL sobre las vistas semánticas del proyecto.

Se realizaron dos pruebas de diez preguntas cada una.

## Configuración

- Modelo: qwen2.5-coder:7b
- Motor de inferencia: Ollama
- Dialecto SQL: PostgreSQL
- Validador: SQLGlot 30.33.0
- Preguntas por prueba: 10
- Vistas autorizadas: ocho vistas semánticas del proyecto.

## Experimentos

### Primera prueba: sin contexto del esquema

El modelo recibió las preguntas y las instrucciones generales para generar SQL.

Resultados:
- Sintaxis válida: 10/10.
- Validez estructural: 9/10.
- Corrección semántica completa: 0/10.

### Segunda prueba: con contexto del esquema

El modelo recibió:
- Nombres y columnas de las ocho vistas.
- Reglas semánticas de `metricas.yaml`.
- Restricciones de generación SQL.
- Instrucciones para utilizar SELECT y LIMIT 100.

Resultados:
- Sintaxis válida: 10/10.
- Validez estructural: 10/10.
- Corrección semántica completa: 7/10.
- Corrección semántica parcial: 1/10.
- Consultas incorrectas: 2/10.

## Comparación

| Indicador | Sin contexto | Con contexto |
|---|---:|---:|
| Sintaxis válida | 100% | 100% |
| Validez estructural | 90% | 100% |
| Corrección semántica completa | 0% | 70% |

La segunda prueba mejoró 70 puntos porcentuales en corrección semántica completa.

## Estructura

- `pregunta_01.sql` a `pregunta_10.sql`: respuestas originales de la primera prueba.
- `referencias.sql`: consultas SQL de referencia.
- `validar_sql.py`: valida la sintaxis de las consultas de referencia.
- `validar_generadas.py`: valida las respuestas de la primera prueba.
- `evaluacion_inicial.md`: evaluación preliminar.
- `evaluacion_semantica.md`: evaluación semántica de la primera prueba.
- `resultados_validacion.md`: resultados estructurales de la primera prueba.
- `comparacion_final.md`: comparación de los experimentos.
- `segunda_prueba/`: prompt contextualizado, respuestas originales, validador y evaluación semántica de la segunda prueba.

## Reproducción

Requiere Python y Ollama, con el modelo instalado:

```powershell
ollama pull qwen2.5-coder:7b
python -m pip install sqlglot
python .\experimentos\text-to-sql\validar_sql.py
python .\experimentos\text-to-sql\validar_generadas.py
```

## Limitaciones

- La evaluación semántica fue estática; no se ejecutaron las consultas contra PostgreSQL.
- No se verificaron resultados numéricos.
- La muestra se limita a diez preguntas por experimento.

## Conclusión

Proporcionar al modelo el esquema y las reglas semánticas mejoró considerablemente la generación de SQL. La corrección semántica completa pasó de 0% a 70%, aunque todavía se requiere validación de ejecución para confirmar el comportamiento de las consultas.

