# Decisión local: continuar con Qwen y revisión humana

La comparación completó 39 intentos por modelo en Windows, con la misma solicitud,
documentos y configuración. Los resultados justifican seleccionar Qwen como
candidato para el prototipo local. No acreditan uso autónomo ni un despliegue de
producción. Gemma no se sustituye silenciosamente en configuraciones compartidas.
El modelo de embeddings no cambia.

## Lectura antes del filtro

| Medida | Qwen3-VL 4B Instruct | Gemma3 4B |
| --- | --- | --- |
| Precisión de valores emitidos | 461/481 = 95.84% | 301/441 = 68.25% |
| Recuperación correcta de valores esperados | 461/505 = 91.29% | 301/505 = 59.60% |
| Documentos con 14 campos correctos | 24/39 | 0/39 |
| Filas de conceptos correctas en orden | 79/102 | 57/102 |
| Documentos con tabla exacta | 27/39 | 20/39 |
| Errores de ejecución | 2 | 7 |
| Tiempo total acumulado | 752.382 s | 949.565 s |
| Mediana por intento (incluye fallos) | 18.675 s | 17.116 s |

Los 36 documentos no usados en el ajuste de Qwen mantienen la ventaja: precisión
95.48% y recuperación 90.56%, frente a 67.07% y 59.44% de Gemma. La configuración
común actual se ajustó con Qwen, y el corpus es sintético y conocido: no es una
comparación de la mejor configuración posible de cada modelo ni una prueba externa.

Se reprodujo exactamente resumen.json desde los 78 registros individuales y las
referencias del repositorio. También se comprobaron las 2,184 filas de campos.csv.
Los hashes de fuentes coinciden con los archivos de la ejecución tras considerar
los finales de línea Windows CRLF; las referencias e imágenes se verificaron.
Las solicitudes y hashes de imágenes enviadas son iguales por documento entre
modelos, salvo el nombre del modelo. No se recalibraron métricas después del resultado.

El filtro anterior elimina 47 lecturas correctas de Qwen y seis incorrectas: la
recuperación cae a 81.98%, aunque su precisión aumenta a 96.73%. El experimento
conserva los valores y advierte sobre evidencia incompleta; no certifica lecturas.

## Fallos y discrepancias

- Qwen 031/034: HTTP 500 con mensaje `prediction aborted, token repeat limit reached`.
  No se atribuyen a tiempo de espera ni a ausencia de campos. No se reintentaron.
- Gemma 008/012/014/017/019/021/022: respuesta HTTP 200, `done_reason=length`,
  `eval_count=4096`. La respuesta contiene repeticiones y fue rechazada como incompleta.
- Qwen tiene 13 valores críticos emitidos que no coinciden: siete son folios con
  numeral #, dos son RFC asignados a folio en documentos sin folio y cuatro están
  en el piloto 035 (folio, ambos RFC e impuestos). No se eliminaron esos errores
  del resultado ni se cambiaron las referencias para favorecer un modelo.
- Otras discrepancias incluyen signo de retenciones, acentos y puntuación, además
  de omisiones/errores de conceptos. El detalle está en CSV y en la respuesta original.

## Reglas sobre las respuestas guardadas

Se aplicó el motor real con catálogos sintéticos, antecedentes históricos, lista
69-B local y fecha/SHA anotados. No hubo llamadas a modelos, BD, RAG o escrituras
de casos durante esta reproducción. No es una prueba de herramientas con una BD real.

| Etapa | Qwen: categoría coincidente | Gemma: categoría coincidente |
| --- | --- | --- |
| Lectura sin filtro → reglas | 31/39 = 79.49% | 19/39 = 48.72% |
| Filtro anterior → reglas | 26/39 = 66.67% | 17/39 = 43.59% |

Las reglas sobre Qwen sugieren aceptar cinco casos no aceptados por la referencia:
020 (folio inventado), 029 (duplicado no detectado por numeral #), 036 (confianza
simulada no reproducida), 038 (instrucción oculta no transcrita por el extractor
visual) y 039 (nota de crédito clasificada factura). La categoría correcta tampoco
garantiza detectar todas las reglas esperadas: se informa el detalle por caso.
Gemma no presenta esas sugerencias de aceptar, pero falla o rechaza más casos.

El modo experimental exige revisión humana para toda lectura completada y conserva
por separado la sugerencia de las reglas. No se puntúa esa condición como una
mejora de clasificación ni se ocultan discrepancias. Los fallos de extracción
siguen siendo errores, no facturas aprobadas ni extracciones fabricadas.

Los escenarios de demo 003, 012 y 021 producen, con las lecturas guardadas,
aceptado/sin hallazgos de rechazo, rechazado/R-014 y rechazado/R-001 respectivamente.
El modo experimental publica sugerencia humana en los tres. La decisión final es
del analista después de revisar el documento.

## Ajustes posteriores a esta evaluación

En el piloto CLI se puede elegir `--modelo qwen3-vl:4b-instruct`, activar
`--revisar-lecturas` y usar `--sin-interaccion` para guardar una pausa sin decisión.
La revisión advierte folio con apariencia de RFC, numeral # al comprobar duplicados,
retenciones negativas y nota de crédito transcrita pero clasificada como factura.
Son avisos explícitos: no se corrigen folios, signos, tipo o RFC con la referencia.
Estos ajustes no modifican los resultados originales guardados.

Validación del código actual: 53 pruebas aprobadas y una integración PostgreSQL
omitida (54 total). Pendiente ejecutar la versión ajustada contra la base local y
probar la interfaz de la aplicación. Esta rama no conecta nuevos endpoints a la
API compartida ni cambia dev, los PR anteriores, embeddings o configuraciones de equipo.

## Archivos

`lecturas_originales.zip` conserva el adjunto completo original con las 78 respuestas
y metadatos; su hash se registra en fuentes.json. Los cuatro reportes de extracción
se copian sin cambiar. `reglas.json`, `casos_reglas.csv`, `informe_reglas.md` y
`procedencia.json` documentan la reproducción posterior. Los archivos originales
mantienen sus modelos, tiempos, errores y lecturas sin alterar.
