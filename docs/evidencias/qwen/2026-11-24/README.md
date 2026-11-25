# Qwen y revisión de lecturas — 24 de noviembre de 2026

Esta evidencia documenta una corrección del procesamiento posterior a la lectura.
No demuestra que Qwen supere a Gemma en el corpus ni valida extracción autónoma.
Se mantiene Gemma como valor predeterminado; el modo nuevo se activa explícitamente
con `--revisar-lecturas` en el piloto local. Depende del soporte PDF del PR #39.

## Resultados observados

Los diagnósticos originales antes/después del filtro para `piloto_001` y
`piloto_003` se generaron en Windows con `qwen3-vl:4b-instruct`, el prompt que
solicita conceptos estructurados y las opciones temperatura 0, seed 42,
num_ctx 8192 y num_predict 4096. El digest del modelo no se registró.

Al contrastar los valores anteriores al filtro con las referencias del repositorio,
los 14 campos de ambos casos coinciden normalizando los formatos de tasa y total,
incluido el nulo de retenciones. Las dos y cuatro partidas, respectivamente,
coinciden con las referencias. Son ejemplos utilizados durante el ajuste: no son
una evaluación independiente y no se deben extrapolar sus resultados al corpus.

| Caso | Lecturas que el filtro anterior eliminó | Problema del respaldo |
| --- | --- | --- |
| piloto_001 | Folio, fecha, RFC emisor y RFC receptor | Folio y fecha faltan en la transcripción; los RFC tienen etiquetas inventadas |
| piloto_003 | Subtotal e impuestos | Los valores faltan en la transcripción |

La revisión experimental conserva estos valores y exige revisión humana; además
señala tres etiquetas inventadas adicionales en el piloto 001, sin cambiar sus
valores. La coincidencia con la transcripción no verifica la imagen ni la
asociación entre etiqueta, valor y rol. Los conceptos permanecen sin verificación
automática. No se usa la referencia esperada como entrada del extractor o filtro.

## Recorrido real F-9401

`pausa_F-9401.json` documenta el piloto 003 procesado por Ollama y las herramientas
reales de Datos, con fecha de recepción explícita 2026-11-02. Conserva subtotal,
impuestos y cuatro conceptos. Se evaluaron 15 reglas; el único hallazgo fue R-003
(confianza desconocida, informativo). Las reglas sugirieron aceptar sobre las
lecturas; el modo experimental publicó sugerencia humana y llegó a la pausa.
No contiene decisión del analista ni resultado de cierre.

La ejecución alcanzó el guardado y escribió pausa.json antes de un EOFError al
pedir una decisión: el comando alimentaba el propio programa por stdin. Se corrigió
el manejo de EOF para conservar la revisión sin cerrar. También se corrigió la
explicación experimental para no repetir «buena confianza» del motivo original de
las reglas, incompatible con las confianzas nulas. Esta evidencia histórica
conserva la frase anterior; no se reescribieron resultados para aparentar una
ejecución posterior al arreglo.

Los embeddings fueron falso-hash: este recorrido no evalúa calidad semántica de
recuperación. Falta confirmación independiente del estado y del evento en
PostgreSQL mediante consulta; no se presenta esa consulta como realizada.

## Validación y entrega

La última versión cuenta con 43 pruebas locales aprobadas y una integración
PostgreSQL omitida (44 total). Las pruebas verifican conservación de lecturas,
avisos, pausa obligatoria aunque las reglas sugieran aceptar, cierre solo tras
decisión explícita, manejo de EOF y preparación del evento de evidencia en una
sesión simulada. No miden precisión del modelo ni sustituyen una integración real.

Antes de activar este modo fuera del piloto CLI, revisar con Datos/Agentes:

- Cómo mostrar las lecturas y los avisos juntos en la interfaz y API.
- Que la sugerencia humana y el informe se conserven en todos los consumidores.
- Comparación de modelos con configuración y corpus fijos, separando lectura,
  descarte del filtro y clasificación por reglas.
- Confirmación de persistencia y decisión humana en el entorno de integración.

Los archivos se guardan sin rutas personales; `procedencia.json` registra hashes
de los adjuntos originales y las transformaciones de formato. Los valores,
hallazgos y explicaciones originales no se corrigen. Los resultados históricos
de S3-13 permanecen como evaluación de su configuración anterior, que incluía
el filtro; no se atribuyen todos sus errores exclusivamente a Gemma.
