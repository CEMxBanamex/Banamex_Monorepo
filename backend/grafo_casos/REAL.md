# Grafo real del piloto (S3-11)

`FlujoCasosReal` procesa una imagen PNG/JPEG con `gemma3:4b` en Ollama y devuelve una
pausa para revisión humana. Al recibir una decisión válida, `reanudar_caso` guarda el
resultado final, el responsable y un evento de confirmación en PostgreSQL.
La demo original `FlujoCasos` se conserva para pruebas sin servicios.

## Recorrido

1. Crear un caso nuevo de tipo factura, ligado al analista del llamador.
2. Llamar a `/api/generate` de Ollama con la imagen, el esquema de `FacturaExtraida`,
   temperatura 0 y semilla 42. No se usan los JSON de verdad del piloto como entrada.
3. Ejecutar la herramienta real `validar_reglas`, que consulta padrón y antecedentes.
4. Ejecutar `preparar_para_redactor` con `buscar_politicas` real, filtrando por regla e historia.
5. Redactar en código con el resultado, los hallazgos y sus citas. No se recalculan importes con un LLM.
6. Guardar extracción, resultado y hallazgos en una transacción con `guardar_resultado`.
   Este último reutiliza `registrar_hallazgo`, con la misma sesión; no hay escrituras duplicadas.
7. Pausar con `interrupt` para revisar imagen, campos y evidencia. Validar la decisión antes de reanudar.
8. Cerrar el caso y guardar la decisión humana por separado de la recomendación.

Las herramientas de Datos se llaman directamente desde el backend, con una sesión compartida;
este recorrido no usa el servidor MCP ni necesita esperar la fusión del PR #19.

## Evidencia de extracción y límites

El prompt pide valores y etiquetas literales. Un filtro descarta valores sin etiqueta y transcripción
coincidentes; en impuestos exige etiqueta de impuesto y rechaza descuentos/retenciones; en total
rechaza etiquetas de subtotal. La confianza y las coordenadas se guardan como null.
La transcripción también proviene de Gemma: la consistencia textual no prueba que la imagen se haya
leído correctamente. Todos los casos se pausan, incluso cuando las reglas sugieren aceptación.
No usar esta salida como aprobación automática ni atribuirle la precisión de S1-26: el esquema es distinto.

Esta versión admite imágenes de una página. No sube el original a S3 ni crea un `Documento` con una
ubicación ficticia; la imagen se conserva en su ruta local y debe mantenerse para la revisión.
El SHA-256 se pasa al validador para contrastarlo con documentos ya registrados en la base.
El alta del documento en S3 y su incorporación al historial de duplicados quedan para el flujo de carga de la API.

El estado del grafo y el mapa de threads son locales al proceso (`InMemorySaver`), aunque la extracción,
hallazgos y decisión sí se guardan en la base. Reanudar antes de cerrar el proceso. Un fallo de extracción,
reglas o políticas marca el caso como `error`, sin inventar una clasificación final. El piloto rechaza
reutilizar un identificador existente; usar otro para un nuevo intento.
El CLI es solo de desarrollo: `--usuario` no es autenticación. Para la API, proporcionar la identidad
validada y sustituir el almacenamiento en memoria por checkpoints persistentes antes de usar varias instancias.

## Preparar el entorno local en Windows

Desde la raíz del monorepo, con Docker Desktop y Ollama iniciados:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose -f docker-compose.dev.yml up -d postgres
docker compose -f docker-compose.dev.yml run --rm migraciones
```

Si es la primera carga sobre esa base, ejecutar también:

```powershell
docker compose -f docker-compose.dev.yml run --rm carga
```

Si dice que ya hay casos, conservarlos: no ejecutar `reset-db`. El piloto requiere las migraciones,
catálogo de reglas y políticas cargados. Por defecto, Compose carga embeddings de prueba `falso-hash`;
eso permite probar conexión y citas, pero no evaluar recuperación semántica real. Usar el mismo
proveedor de embeddings al cargar y consultar. La evaluación con `embeddinggemma:300m` corresponde
a la preparación del RAG y requiere un índice generado con ese modelo.

Instalar dependencias de Python en el entorno virtual del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\datos\requirements.txt -r .\backend\grafo_casos\requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .\datos
```

Para conectar Python de Windows al PostgreSQL de Compose, usar `localhost`, no el nombre
interno `postgres`. Esta cadena solo corresponde a los valores predeterminados locales de `.env.example`;
si los cambiaste, adaptar usuario, clave, puerto y base:

```powershell
$env:AUTH_MODE = "dev"
$env:DATABASE_URL = "postgresql+psycopg://steward_backend:local-backend@localhost:5432/dsa_local"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
$env:OLLAMA_URL = "http://localhost:11434"
$env:VISION_MODELO = "gemma3:4b"
$env:EMBEDDING_PROVEEDOR = "falso"
```

Comprobar `ollama list`: debe incluir `gemma3:4b`. No es necesario descargar otro modelo de visión.
Usar un identificador de caso nuevo y una carpeta de evidencia nueva, fuera del repo:

```powershell
.\.venv\Scripts\python.exe -m backend.grafo_casos.piloto `
  .\db\semillas\sinteticos\facturas\evaluacion\piloto_001.png `
  --caso F-9001 --usuario dev-ana `
  --salida "..\evaluacion_grafo_F-9001"
```

Antes de responder, abrir la imagen original y contrastar especialmente RFC, folio e importes.
El programa guarda `pausa.json`, muestra el resultado y espera la decisión y el motivo.
Tras reanudar, guarda `final.json`. Escribir `salir` deja el resultado en revisión en la base,
pero termina la pausa en memoria y no permite reanudar ese thread desde otra ejecución del CLI.

## Validación

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s backend/grafo_casos/tests -v
.\.venv\Scripts\python.exe -m pytest datos/tests -q
```

Las pruebas sin servicios controlan HTTP de Ollama y la persistencia; usan el motor de reglas real.
Cubren nulos, descuento/impuesto, subtotal/total, archivos inválidos, respuestas truncadas,
errores de extracción, pausa antes de decidir, decisión inválida y aislamiento de casos.
Estas pruebas no demuestran disponibilidad de Ollama/PostgreSQL ni precisión sobre imágenes.

La prueba opcional `test_integracion_bd.py` requiere una base **de pruebas** ya migrada y con semillas
y embeddings `falso-hash`. No borra el esquema; deja un caso con identificador aleatorio para inspección.
Definir `GRAFO_DATABASE_URL_PRUEBAS` solo para esa base antes de ejecutar `unittest`.
Usa extracción controlada y herramientas/guardado reales; verifica un hallazgo/evento por regla,
pausa sin resultado final y cierre idempotente con un solo evento de confirmación.

Para cerrar S3-11 todavía se necesita evidencia de una ejecución local completa con Gemma,
revisión humana y PostgreSQL, y después verificar el recorrido en dev con el equipo.
Guardar la fecha, el commit, las versiones, el proveedor de embeddings y los archivos de evidencia.
Medir precisión de extracción y clasificación por lote corresponde a S3-13.
