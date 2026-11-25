# Reproducción de reglas sobre las lecturas

Reglas reales con contexto sintético del repositorio. Sin Ollama ni base de datos.
No verifica persistencia, permisos, RAG ni decisiones del analista.

| Modelo | Etapa | Categorías coincidentes | Sugerencias de aceptar no esperadas |
| --- | --- | --- | --- |
| qwen3-vl:4b-instruct | sin_filtro | 31/39 | 5 |
| qwen3-vl:4b-instruct | filtro_anterior | 26/39 | 4 |
| gemma3:4b | sin_filtro | 19/39 | 0 |
| gemma3:4b | filtro_anterior | 17/39 | 0 |

## Límites y decisiones

El modo experimental publica sugerencia humana para toda lectura completada, independientemente de la sugerencia de las reglas; no se usa ese bloqueo para inflar la exactitud de clasificación.
Una categoría coincidente no implica que todas las reglas esperadas se detectaron: el detalle incluye reglas esperadas no detectadas.
La referencia contiene escenarios con confianza simulada y texto oculto que el extractor visual puede no reproducir. Se conservan las discrepancias en los resultados.
No se reemplazan lecturas por verdad de referencia ni se corrigen errores durante esta reproducción.
