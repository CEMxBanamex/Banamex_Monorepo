# Validación local con Qwen: F-9501 a F-9503

Fuente: salida de terminal enviada por Carlos Delgado el 24 de noviembre de 2026.
Los tres procesos finalizaron, imprimieron la ruta de pausa.json y devolvieron el
prompt de PowerShell sin traceback. No registraron decisiones finales.

| Caso | Documento | Resultado observado |
| --- | --- | --- |
| F-9501 | piloto_003.png | Campos y cuatro conceptos conservados; R-003 por confianza desconocida; R-015 por antecedente F-9401 de una prueba previa |
| F-9502 | piloto_012.png | Cinco conceptos conservados y R-014 por total inconsistente |
| F-9503 | piloto_021.jpg | RFC emisor nulo y R-001 por dato obligatorio no leído; cinco conceptos conservados |

Todos mostraron la revisión de evidencia y conservaron el estado de revisión sin
decisión final. La explicación ya no afirma «buena confianza» cuando esta es nula.
El historial local afecta la detección de duplicados: F-9501 no equivale a un caso
correcto sobre una base limpia. No se borran antecedentes para cambiar el resultado.

La salida confirma que el código alcanzó el guardado y la pausa. No se presenta
como consulta independiente de PostgreSQL. Las lecturas JSON adjuntas se extraen
de la terminal; no se fabricaron los archivos pausa.json completos, que no se
adjuntaron en esta ejecución. No se probó la interfaz web durante esta corrida.

La configuración utilizó qwen3-vl:4b-instruct, revisión de lecturas y embeddings
falso-hash, con fecha explícita 2026-11-02. Esto no mide calidad semántica del RAG
ni acredita extracción autónoma. El resultado de los 39 documentos y la comparación
con Gemma se conservan por separado en docs/evidencias/comparacion_vision/2026-11-24/.
