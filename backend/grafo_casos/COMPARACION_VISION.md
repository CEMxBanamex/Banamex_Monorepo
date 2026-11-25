# Comparación aislada de Qwen y Gemma

Este evaluador no modifica la configuración de la aplicación, no importa el grafo
ni las herramientas de persistencia, no usa PostgreSQL y no crea casos. Solo llama
a Ollama y escribe resultados en una carpeta nueva fuera del repositorio.

## Diseño fijado antes de la ejecución completa

- Dos modelos: `qwen3-vl:4b-instruct` y `gemma3:4b`, por defecto en ese orden.
- Los mismos 39 documentos, prompt, esquema y opciones de generación actuales:
  temperature 0, seed 42, num_ctx 8192 y num_predict 4096. El prompt actual se
  ajustó con Qwen en los pilotos 001, 003 y 012; no se afirma optimización equivalente
  para cada modelo. Se compara el comportamiento con una solicitud común.
- Se procesa cada modelo en un bloque para reducir cambios repetidos de modelo
  en GPU. Los tiempos incluyen carga inicial y procesamiento: no son un benchmark
  de inferencia caliente ni una comparación de hardware controlada.
- PDFium rasteriza todas las páginas visibles con los límites del extractor.
  Se verifica que los hashes de las imágenes enviadas y las solicitudes, excepto
  el nombre del modelo, coincidan entre modelos para cada documento.
- La referencia esperada solo entra al calificador. El extractor recibe el archivo
  y la solicitud compartida, nunca los campos o resultados esperados.
- La respuesta sin filtro y el resultado del filtro anterior se califican separados.
  El segundo se obtiene de una copia de la misma respuesta, sin otra inferencia.
- Se capturan respuesta completa de Ollama (incluido done_reason), metadatos de
  solicitud, digest del modelo, hashes de código y documentos, versiones y errores.
- No se hacen reintentos selectivos ni se sustituyen errores por otro modelo.
  Reanudar conserva también los errores. Cambios de código, referencias, imágenes,
  versiones, modelos o URL impiden mezclar ejecuciones al reanudar.

## Métricas y decisión

Se informa precisión de valores emitidos y recall de valores esperados para los
14 campos. Los nulos correctos no inflan esos dos indicadores; también se informa
cuántos documentos tienen los 14 campos correctos, incluyendo nulos.
Los errores y pendientes permanecen como lecturas no recuperadas. Se distinguen
valores críticos erróneos emitidos y valores críticos esperados sin lectura.
Críticos: folio, fecha, RFC emisor/receptor, subtotal, impuestos y total.

Los conceptos se comparan completos y por fila en orden: descripción con espacios
normalizados y sin diferencia de mayúsculas; cantidades e importes normalizados
como números. Cambios de caracteres o asociaciones entre columnas no se reparan.
Filas extra penalizan precisión, y filas faltantes penalizan recall.

Se publican grupos de todos los documentos, los tres usados en el ajuste de Qwen,
los restantes 36, PDF e imágenes. El resto del corpus también es sintético y fue
usado en evaluaciones anteriores: no certifica generalización externa.

Para decidir si Qwen merece sustituir el extractor del prototipo, revisar primero
el grupo restante sin filtro: precisión, recall, documentos completos, conceptos,
errores críticos y tiempo. Si unos indicadores mejoran y otros empeoran, el informe
no declara un ganador automático. Los valores erróneos críticos deben inspeccionarse
contra el documento. Una mejora media no acredita extracción autónoma ni producción.
Después corresponde probar la integración con reglas y revisión humana en los
escenarios de demo; no se pretende resolverlo a partir de clasificación siempre humana.

No comparar estos resultados como equivalentes a S3-13: cambiaron prompt y esquema,
renderizador y tratamiento de evidencia. Gemma se vuelve a ejecutar como baseline
con la misma configuración que Qwen para esta comparación.

## Ejecución

Desde una copia aislada y con `datos` en el import path del mismo proceso:

```powershell
@'
import sys, runpy
from pathlib import Path
sys.path.insert(0, str(Path("datos").resolve()))
sys.argv = ["comparar", "--salida", r"..\comparacion_vision_20261124"]
runpy.run_module("backend.grafo_casos.comparar_vision", run_name="__main__")
'@ | & $pythonComparacion -
```

Se puede usar `--limite 1` para una prueba inicial por modelo; el informe conserva
los 39 documentos en sus denominadores. Para seguir el lote completo tras parar,
usar la misma carpeta y agregar `--reanudar` a sys.argv (sin el límite). No cambiar
los modelos ni su orden. No necesita stdin interactivo: puede ejecutarse por tubería.

Los resultados están en `informe.md`, `resumen.json`, `campos.csv`, `ejecucion.json`
y las carpetas `modelo_1`/`modelo_2`. Se guardan después de cada documento, no solo
al terminar el lote. No editar ni mezclar carpetas de resultados históricos.

Validación local del evaluador: 49 pruebas aprobadas y una integración PostgreSQL
omitida (50 total). Incluye un lote HTTP simulado de dos documentos/modelos,
reanudar sin repetir llamadas, captura de truncamientos y restauración de la variable
de modelo. Es una validación del programa: no se ejecutaron modelos reales aquí.
