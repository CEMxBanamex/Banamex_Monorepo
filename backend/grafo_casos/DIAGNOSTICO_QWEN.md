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

## Prueba de revisión sin borrar valores

`revision_evidencia.py` permite reproducir los JSON `antes_filtro` guardados sin
invocar Ollama ni consultar la referencia esperada. Conserva valores, etiquetas y
conceptos como lecturas, y añade un estado por campo: coincidencia textual,
pendiente de revisión o sin valor leído. Ninguno verifica la imagen; sin valor
leído no equivale a ausencia en la factura. Se mantienen las comprobaciones del
filtro anterior sobre una copia para señalar inconsistencias, incluidos descuentos
usados como impuestos o subtotales usados como total. No se corrigen etiquetas
automáticamente ni se resuelve aún su atribución al rol o valor correcto.

Es un informe experimental separado del contrato FacturaExtraida. No sustituye
el extractor habitual ni se conecta a validar_reglas o a una decisión automática.
Integrarlo al flujo requerirá que este consuma los estados de revisión y no trate
los valores conservados como verificados. La confianza y las coordenadas del modelo
no se publican como mediciones. Los conceptos se conservan sin acreditarse exactos.

Reproducción local de los diagnósticos del 24 de noviembre, 14:28:26: se conservan
los cuatro valores descartados en `piloto_001` y los dos de `piloto_003`, todos
marcados pendientes de revisión. Además, en `piloto_001` se señalan tres etiquetas
inventadas en nombre del emisor, dirección y nombre del receptor, cuyos valores
el filtro anterior sí conservaba: siete campos pendientes en total en ese archivo,
y dos en `piloto_003`. Las filas de conceptos permanecen sin cambios.
35 pruebas de código pasan y una integración de base de datos se omite (36 total).
Un valor inventado también se conserva como lectura, pero queda pendiente; por eso
este informe no debe enviarse al validador habitual como si estuviera verificado.

Uso en PowerShell desde la raíz del repositorio (carpeta de salida nueva):

```powershell
$salida = "..\revision_evidencia_$(Get-Date -Format yyyyMMdd_HHmmss)"
.\.venv\Scripts\python.exe -m backend.grafo_casos.revision_evidencia --diagnosticos "..\diagnostico_qwen_conceptos_20261124_142826" --salida $salida
```

## Integración opcional al piloto local

La opción nueva `--revisar-lecturas` conecta este tratamiento al grafo real.
Sin esa opción se conserva el comportamiento habitual. Con ella, el extractor
conserva los valores anteriores al filtro, manteniendo rechazo de respuestas
vacías o truncadas y anulando confianza/coordenadas no verificadas. Las reglas
reales reciben esas lecturas; se conserva su salida original en `resultado_reglas`
y sus hallazgos permanecen. La sugerencia publicada en este modo es siempre
`humana`, incluso si las reglas sugerían aceptar o rechazar: sus cálculos sobre
lecturas no verificadas no certifican el documento. No se agregan reglas de
catálogo inventadas ni se asigna una confianza artificial.

El estado, el aviso al analista y los archivos pausa/final incluyen el informe.
El adaptador de base de datos guarda la explicación y un evento de extracción
con el informe y el resultado original de las reglas en la misma transacción.
Usa una acción existente de bitácora; no requiere migraciones. El cierre continúa
requiriendo una decisión explícita del analista contra el original.

Validación local de esta integración: 42 pruebas aprobadas y una integración de
PostgreSQL omitida (43 total). Incluye un caso donde las reglas sugieren aceptar,
que queda en pausa con sugerencia humana y conserva su lectura y reporte. Se
verifica con sesión simulada el envío del informe al evento de base de datos y
que repetir un guardado no duplique ese evento. No se ejecutó PostgreSQL local.

Se reprodujo el grafo con ambas respuestas guardadas y reglas reales, usando un
adaptador de pruebas para la persistencia y recuperación de políticas: conserva
todos los campos, llega a pausa humana sin cierre y no genera R-001 por los seis
descartes anteriores. Esto no constituye una nueva ejecución de Qwen, una prueba
real de PostgreSQL o una evaluación de precisión sobre el corpus.

Pendiente: ejecución en Windows con Ollama y la base local, inspección de
`pausa.json`, explicación y bitácora. No desplegar este experimento por defecto
ni comparar sus métricas con las históricas como si fueran la misma configuración.

### Manejo de entrada agotada y redacción

La ejecución Windows F-9401 con Qwen llegó a la pausa tras guardar sus lecturas,
incluidos subtotal e impuestos, y mostró los avisos de evidencia. Falló después
con EOFError porque el intérprete recibía el propio programa por la entrada estándar
(`@'…'@ | python -`), por lo que input() no podía recibir una decisión. El piloto
ahora maneja EOF sin cerrar el caso ni generar final.json, tanto al pedir decisión
como al pedir motivo. Para una decisión interactiva se debe invocar el módulo
desde la terminal, sin alimentar el código del programa por una tubería.

Se elimina de la explicación experimental la copia literal del motivo original
de las reglas: podía afirmar «buena confianza» aun cuando todos los campos tenían
confianza nula. Ese motivo original queda solo en resultado_reglas para auditoría;
la explicación publicada indica explícitamente que no hay confianza calibrada.
Validación: 43 pruebas aprobadas y una integración PostgreSQL omitida (44 total),
incluyendo EOF en ambos puntos y preservación de pausa.json sin reanudar el grafo.
