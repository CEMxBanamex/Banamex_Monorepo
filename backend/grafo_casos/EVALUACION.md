# S3-13: evaluación de punta a punta del piloto

Esta evaluación mide el grafo real de S3-11, detenido en revisión humana. Cada documento pasa por
`procesar_caso`: extracción Gemma, validar_reglas, buscar_politicas, redacción y guardado de hallazgos.
No se reanuda automáticamente con la respuesta esperada: eso convertiría la verdad de referencia en
una decisión humana ficticia. El cierre humano se comprueba por separado en la evidencia F-9005 de S3-11.

## Qué se mide

- Corpus completo: 39 documentos; 19 PNG/JPEG y 20 PDF, de los cuales 4 tienen dos páginas.
- Extracción: coincidencia de los 14 campos con `verdad.campos`, con normalización de espacios/mayúsculas,
  fechas, importes, RFC y tasas. La normalización no corrige caracteres ni completa valores ausentes.
- Precisión de valores: valores no vacíos correctos / valores no vacíos emitidos. Los null correctos no
  inflan este indicador. Recall: valores correctos / valores presentes en toda la referencia.
- Exactitud por campo: coincidencias, incluyendo ausencias correctas, / total de documentos del corpus.
- Clasificación: recomendación del grafo frente a `esperado.resultado`, matriz de confusión,
  precisión/recall/F1 por clase y falsos aceptados. La recomendación se mide antes de una decisión humana.
- Errores y documentos pendientes no desaparecen del corpus ni de sus denominadores; la matriz incluye
  `sin_salida`. Un lote parcial no demuestra que S3-13 esté terminado.
- Los conceptos no se califican como métrica de extracción, pero sí llegan al motor de reglas;
  sus errores pueden afectar la clasificación. No se reportan bbox/confianza como precisión medida.

El JSON de referencia se usa exclusivamente al calificar, verificar hashes y fijar la fecha de recepción
original del escenario (2026-11-02), nunca como respuesta del extractor. No se inyecta `lectura_simulada`
ni `confianza_simulada`. Esto puede causar desacuerdos con los escenarios de baja confianza del generador;
se reportan como resultados, sin cambiar la referencia. piloto_001 se usó al ajustar el extractor: este
corpus de desarrollo no es una evaluación independiente de generalización.

## Aislamiento y PDF

Usar `dsa_pruebas` recién migrada y cargada o una base nueva `dsa_eval_*` con las mismas semillas.
El evaluador rechaza bases de aplicación y bases con casos de origen `aplicacion`. Cada documento usa
una transacción externa que se revierte al llegar a la pausa, también ante fallos; las herramientas
usan sesiones con savepoints. Así los resultados del lote no se incorporan como antecedentes del siguiente
caso y no contaminan duplicados. No se borran filas existentes. Las secuencias de PostgreSQL pueden avanzar
aunque sus filas se reviertan. No ejecutar otras pruebas sobre esa base mientras corre la evaluación.

El adaptador PDF es exclusivo de evaluación: rasteriza **todas** las páginas visibles a 150 dpi y las
une verticalmente para la llamada visual existente. El límite es de cuatro páginas/40 millones de píxeles;
los documentos fuera de límites figuran como errores. No extrae texto oculto del PDF, por lo que el
escenario de inyección oculta conserva su referencia y puede fallar. El SHA enviado al validador sigue
siendo el del archivo original, importante para duplicados. Esta conversión no agrega soporte PDF a la API.

## Preparación en Windows

En PowerShell, desde la raíz del monorepo, con Docker y Ollama abiertos:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\backend\grafo_casos\requirements-evaluacion.txt
```

Los comandos siguientes corresponden solo a las credenciales locales de `.env.example`. Si se cambiaron,
adaptar las conexiones. Preparar `dsa_pruebas` ya creada por el entorno local, sin borrar ni reiniciar bases:

```powershell
docker compose -f docker-compose.dev.yml run --rm -e DATABASE_URL=postgresql+psycopg://postgres:local-postgres@postgres:5432/dsa_pruebas migraciones
docker compose -f docker-compose.dev.yml run --rm -e DATABASE_URL=postgresql+psycopg://postgres:local-postgres@postgres:5432/dsa_pruebas carga
```

Si ya contiene datos inesperados, detenerse y usar otra base de evaluación; no usar `reset-db`,
`recarga` ni `down -v`. Esta tarea no necesita modificar `dsa_local` ni los casos F-9001 a F-9005.

```powershell
$env:AUTH_MODE = "dev"
$env:GRAFO_EVAL_DATABASE_URL = "postgresql+psycopg://postgres:local-postgres@localhost:5432/dsa_pruebas"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
$env:OLLAMA_URL = "http://localhost:11434"
$env:VISION_MODELO = "gemma3:4b"
$env:EMBEDDING_PROVEEDOR = "falso"
```

Comenzar con un documento; la carpeta debe ser nueva y estar fuera del repo:

```powershell
.\.venv\Scripts\python.exe -m backend.grafo_casos.evaluacion --salida "..\evaluacion_s3_13" --limite 1
```

Revisar el informe y el primer archivo antes de continuar. Si corresponde, retomar pendientes con el
mismo modelo, código y configuración:

```powershell
.\.venv\Scripts\python.exe -m backend.grafo_casos.evaluacion --salida "..\evaluacion_s3_13" --reanudar
```

`--reanudar` no repite documentos ya registrados como error: quedan incluidos en el resultado original.
Un nuevo intento requiere otra carpeta y se reporta como otra ejecución. No cambiar el prompt tras ver
cada factura para mezclar resultados de configuraciones distintas. El lote escribe cada resultado antes
de pasar al siguiente documento, de modo que se puede continuar después de una interrupción.

## Resultados y cierre

- `ejecucion.json`: commit, fecha UTC, modelo/digest, versiones, hashes del código y del corpus.
- `documentos/*.json`: salida completa en pausa o error, duración, archivo y SHA.
- `campos.csv`: valores esperados/leídos y coincidencias por campo.
- `casos.csv`: clasificación esperada/predicha, estado y reglas.
- `resumen.json` e `informe.md`: métricas, matriz, cobertura y límites.

Estos archivos solo contienen resultados reales cuando se ejecutan con servicios: las pruebas unitarias
usan respuestas controladas y no acreditan precisión del modelo. Antes de cerrar S3-13 hay que ejecutar el
lote completo, revisar errores/discrepancias con Iris y versionar los resultados y conclusiones. El uso
de embeddings `falso-hash` permite medir la integración del RAG; no acredita recuperación semántica real.

El PR #30 ya está integrado en dev. La rama de S3-13 incorpora dev y el PR #36 apunta a dev.
Los resultados conservados corresponden al commit histórico del manifiesto; esta actualización
no vuelve a ejecutar Gemma ni sustituye las mediciones originales.

## Ejecución local registrada

La [evidencia del 23 de noviembre de 2026](../../docs/evidencias/s3-13/ejecucion-2026-11-23/README.md)
conserva los 39 intentos: 30 pausas, 9 errores y ningún pendiente. Exactitud de clasificación
46.15%; precisión de valores 79.65%; recall sobre el corpus 36.44%. Incluye los mensajes
de error, discrepancias y límites. Requiere revisión con Iris; no acredita aceptación
autónoma ni validación del despliegue en dev.
