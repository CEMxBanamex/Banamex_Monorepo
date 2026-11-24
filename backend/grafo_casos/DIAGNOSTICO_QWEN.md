# Diagnóstico del filtro con Qwen — 2026-11-24

Se revisaron las respuestas guardadas antes y después de `_filtrar_evidencia`
para `piloto_001.png` y `piloto_012.png`. Esta revisión reutiliza respuestas
existentes; no constituye otra ejecución del modelo ni una evaluación del corpus.

En `piloto_012`, el RFC del receptor aparece como línea completa sin etiqueta,
inmediatamente después de `RECEPTOR` y del nombre completo del receptor.
El filtro anterior lo descartaba por faltar la etiqueta. La excepción nueva
conserva únicamente un RFC ya entregado en ese campo si tiene estructura de RFC,
aparece una sola vez como línea completa y sigue exactamente esa secuencia.
No inventa una etiqueta ni completa caracteres. Solo cubre el encabezado RECEPTOR;
otros diseños siguen sujetos al criterio anterior. No verifica inscripción fiscal,
autenticidad del documento ni exactitud visual de la transcripción.

En `piloto_001`, los valores de folio y fecha sí llegan en los campos del modelo,
pero están ausentes de su propia transcripción. Continúan descartándose: no se
relaja el control para conservar valores sin respaldo en esa transcripción.
Esto muestra una inconsistencia de la respuesta que requiere revisar el original.

En ambos documentos `conceptos` ya está vacío antes del filtro. Esta corrección
no resuelve esa omisión ni acredita confiabilidad del extractor. No cambia prompt,
modelo predeterminado, contrato, configuración de Ollama ni resultados históricos.

Validación local: 30 pruebas aprobadas y una integración de base de datos omitida
(31 en total). Incluye rechazo de roles, nombres, líneas parciales, repeticiones
y RFC ausentes; también conserva el descarte de folio y fecha sin transcripción.
Al reproducir ambos JSON guardados, el único cambio frente a las salidas anteriores
es conservar `receptor_rfc=GFD960701AB4` en `piloto_012`, con etiqueta nula.
Las pruebas verifican comportamiento del código, no precisión del modelo.

## Experimento posterior: conceptos estructurados

Ante una nueva extracción de `piloto_012` que conserva el RFC pero sigue devolviendo
`conceptos=[]`, se explicita en el prompt que transcribir las partidas no sustituye
llenar la lista. El esquema de generación requiere la lista y las cuatro claves
de cada partida, con descripciones específicas. Las celdas numéricas admiten null
y la lista admite cero elementos: no se impone una cantidad de partidas ni se
calculan importes. No se cambia el contrato compartido ni el modelo predeterminado.
También se pide incluir folio y fecha en la transcripción completa.

Este cambio de prompt/esquema inicia una configuración experimental distinta;
los resultados anteriores permanecen como evidencia de la configuración anterior.
Validación local: 32 pruebas aprobadas y una integración de base de datos omitida
(33 en total). La salida simulada conserva incluso un importe inconsistente y
celdas nulas sin corregirlos; se admite lista vacía. Está pendiente ejecutar Qwen
en la laptop y contrastar todas las filas contra el documento original. No se
afirma mejora de precisión a partir de las pruebas de código.
