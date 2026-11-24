# S3-13: resultados locales del piloto

Ejecución real en Windows iniciada el 23 de noviembre de 2026 a las 18:43,
hora de Ciudad de México (2026-11-24 00:43 UTC). Código evaluado:
`eecd6c458e3c356a5e8739ce11c6210236ceb0ff`, dependiente de S3-11 / PR #30.
Modelo `gemma3:4b`, Python 3.14.5, PostgreSQL `dsa_pruebas`, embeddings de
prueba `falso`. El manifiesto conserva digest, versiones y hashes originales.

## Resultado

| Indicador | Resultado |
| --- | --- |
| Documentos intentados | 39 de 39 |
| Llegaron a revisión humana | 30 (76.92%) |
| Errores de extracción | 9 (23.08%) |
| Pendientes | 0 |
| Clasificación correcta sobre el corpus | 18/39 (46.15%) |
| Macro F1 de clasificación | 40.19% |
| Precisión de valores no vacíos emitidos | 184/231 (79.65%) |
| Recall de valores esperados sobre el corpus | 184/505 (36.44%) |
| Falsos aceptados | 0; tampoco hubo recomendaciones de aceptación |

El tiempo acumulado por documento fue 1096.385 segundos (18.27 minutos);
no incluye preparación, migraciones ni tiempo entre las dos invocaciones.
La primera invocación procesó un documento; la segunda continuó los restantes
con `--reanudar`, sin sustituir resultados ni modificar el extractor.

## Errores observados

| Documentos | Mensaje registrado | Interpretación y límite |
| --- | --- | --- |
| 005, 007, 009, 014, 019, 020, 034, 035 | Ollama no completó la extracción. | El extractor rechaza `done_reason=length` o una respuesta sin `done` verdadero. El registro no conserva cuál de ambas condiciones ocurrió; no permite asegurar agotamiento de tokens. |
| 038 | No se pudieron leer campos; requiere revisión del documento. | Ningún campo quedó con valor utilizable después del filtro de evidencia. El registro no conserva la respuesta previa al filtro. |

Los nueve fallos son `ErrorExtraccion`; estos registros no muestran fallos de
conexión con Docker/PostgreSQL. Los errores permanecen en los denominadores.

## Discrepancias y conclusiones

- R-001 aparece en 29 de los 30 casos que llegaron a pausa. Hay una pérdida
  frecuente de campos obligatorios durante la extracción o el filtrado; el
  resultado agregado no permite atribuir cada ausencia a una etapa concreta.
- De los 11 casos esperados como aceptados, siete se recomendaron rechazados,
  uno para revisión humana y tres terminaron en error. Ninguno se aceptó.
- Ocho de los 18 aciertos de categoría omiten al menos una regla esperada:
  pilotos 013, 015, 016, 022, 024, 025, 027 y 037. La exactitud de categoría
  no equivale a una explicación correcta. Las reglas están detalladas en `casos.csv`.
- Ambos RFC solo coinciden en 8/39 documentos. En piloto_001 Gemma agregó un
  carácter al RFC del proveedor y se activó R-002 aunque la referencia era aceptado.
- El sistema todavía requiere revisión humana y mejoras de extracción; esta
  ejecución no acredita que la clasificación sea fiable para uso autónomo.

## Alcance y trazabilidad

Los 39 documentos originales y sus anotaciones se identifican en `ejecucion.json`.
Se recalcularon las métricas con las 39 salidas y el evaluador del commit registrado:
`resumen.json` coincide íntegramente con ese recálculo. Los hashes del código
coinciden al reproducir los finales de línea CRLF de Windows; no se alteró el
manifiesto para adaptarlo a Linux. Se verificaron también los hashes del corpus.

Se conservan los 44 archivos del lote recibido, sin reemplazar errores por
reintentos. `documentos/` contiene salidas en pausa y registros de error;
`campos.csv`, `casos.csv`, `resumen.json` e `informe.md` contienen las mediciones.
Las escrituras por caso se revierten en la base de evaluación: estas 30 pausas
no son aprobaciones ni cierres humanos persistidos. El cierre manual se comprobó
por separado en [F-9005](../../s3-11/F-9005/README.md).

Se evalúan 14 campos; conceptos, coordenadas y confianza quedan fuera de la
métrica de extracción. Los PDF se rasterizan completos a 150 dpi; no se lee
su texto oculto. No se inyecta la confianza simulada de las anotaciones.
Los embeddings falso-hash no acreditan calidad semántica de recuperación.
Piloto_001 se usó para ajustar el extractor previamente: es un corpus de
desarrollo, no una prueba independiente de generalización.

## Revisión pendiente

Revisar con Iris las nueve extracciones fallidas, las discrepancias de reglas
y los escenarios cuya referencia depende de confianza simulada o texto oculto.
Cualquier cambio de prompt, límite de generación o preprocesamiento debe medirse
en otra carpeta como una ejecución distinta, conservando esta línea base.
La evaluación y sus limitaciones están documentadas; la revisión del equipo y
la integración de la rama siguen pendientes. No implica cierre de S3-11 en dev.
