# Comparación de extracción visual

Misma solicitud y documentos para ambos modelos; sin base de datos ni escrituras de casos.
No evalúa clasificación, decisiones humanas ni calidad semántica del RAG.
Errores y pendientes cuentan como lecturas no recuperadas; los nulos correctos no inflan la precisión de valores.
Los tres pilotos usados para ajustar Qwen se muestran separados; los restantes tampoco acreditan generalización externa.

- qwen3-vl:4b-instruct: 37 salidas; 2 errores; 0 pendientes.
- gemma3:4b: 32 salidas; 7 errores; 0 pendientes.

| Modelo | Grupo | Etapa | Precisión valores | Recall valores | Documentos 14 campos | Recall conceptos |
| --- | --- | --- | --- | --- | --- | --- |
| qwen3-vl:4b-instruct | todos | sin_filtro | 95.84% | 91.29% | 24/39 | 77.45% |
| qwen3-vl:4b-instruct | todos | filtro_anterior | 96.73% | 81.98% | 19/39 | 77.45% |
| qwen3-vl:4b-instruct | restantes | sin_filtro | 95.48% | 90.56% | 21/36 | 74.73% |
| qwen3-vl:4b-instruct | restantes | filtro_anterior | 96.46% | 81.76% | 18/36 | 74.73% |
| gemma3:4b | todos | sin_filtro | 68.25% | 59.60% | 0/39 | 55.88% |
| gemma3:4b | todos | filtro_anterior | 77.82% | 42.38% | 0/39 | 55.88% |
| gemma3:4b | restantes | sin_filtro | 67.07% | 59.44% | 0/36 | 56.04% |
| gemma3:4b | restantes | filtro_anterior | 76.77% | 41.85% | 0/36 | 56.04% |

La etapa filtro_anterior usa la misma lectura: mide pérdidas del filtro sin otra inferencia.
Conservar valores no certifica su exactitud. Revisar errores críticos y documentos completos, además del promedio.
Las métricas históricas de S3-13 corresponden a otra configuración y no son una comparación controlada.
