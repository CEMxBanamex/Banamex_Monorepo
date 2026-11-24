# S3-13: evaluación del grafo

Corpus: 39; con pausa: 30; errores: 9; pendientes: 0.

Exactitud de clasificación sobre todo el corpus: 46.15%.

Precisión de valores emitidos: 79.65%; recall de valores sobre todo el corpus: 36.44%.

Errores y pendientes permanecen en los denominadores del corpus. No son aprobaciones humanas.

Se evalúan 14 campos; conceptos, bbox y confianza no se califican como precisión de extracción. El grafo llega a la pausa con herramientas reales; sus escrituras se revierten al terminar cada caso. La verdad no se envía a Gemma ni se usa para decidir. Los PDF se rasterizan completos; no se inspecciona texto oculto. Los embeddings falso-hash no miden calidad semántica del RAG.

La tabla por campo y la matriz de confusión están en resumen.json; el detalle, en campos.csv y casos.csv.

## Clasificación: filas esperadas, columnas predichas

| Esperado | aceptado | rechazado | humana | sin salida |
| --- | --- | --- | --- | --- |
| aceptado | 0 | 7 | 1 | 3 |
| rechazado | 0 | 13 | 1 | 3 |
| humana | 0 | 3 | 5 | 3 |

## Extracción por campo

| Campo | Coincidencias / corpus | Exactitud normalizada |
| --- | --- | --- |
| folio | 10/39 | 25.64% |
| fecha | 17/39 | 43.59% |
| emisor_nombre | 22/39 | 56.41% |
| emisor_rfc | 8/39 | 20.51% |
| emisor_direccion | 12/39 | 30.77% |
| receptor_nombre | 12/39 | 30.77% |
| receptor_rfc | 8/39 | 20.51% |
| moneda | 17/39 | 43.59% |
| subtotal | 19/39 | 48.72% |
| impuestos | 16/39 | 41.03% |
| tasa_iva | 13/39 | 33.33% |
| retenciones | 29/39 | 74.36% |
| total | 19/39 | 48.72% |
| condiciones_pago | 13/39 | 33.33% |

El piloto_001 se usó durante el ajuste del extractor: el corpus no constituye una prueba independiente de generalización. La referencia de clasificación se mantiene incluso en escenarios con confianza simulada o texto oculto que el extractor visual no reproduce.
