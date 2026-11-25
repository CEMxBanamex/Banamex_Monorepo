# Qwen en la aplicación local

Esta rama integra el trabajo de casos de `frontend/semana-3-casos-yael` (2fbfacb),
dev (5133844), soporte PDF, comparación de modelos y revisión de evidencia.
No modifica las ramas de otras personas ni despliega a AWS automáticamente.

## Comportamiento

- Qwen3-VL 4B Instruct es el modelo visual predeterminado; VISION_MODELO permite
  elegir otro modelo instalado. Los embeddings permanecen independientes.
- La API real recibe PNG/JPEG/PDF, conserva el archivo original y su hash. El
  extractor admite hasta 15 MiB, cuatro páginas PDF y 40 millones de píxeles.
- Los valores y conceptos leídos se conservan; los avisos de evidencia se guardan
  en bitácora y aparecen en la explicación y detalle. No se inventan confianzas.
- El resultado publicado requiere revisión humana. Los hallazgos de las reglas
  y su sugerencia original quedan separados del resultado final del analista.
- La pantalla muestra imagen o PDF, campos con evidencia pendiente y conceptos.
  Solo una confirmación explícita con motivo cierra el caso. Se conserva el flujo
  de autenticación y autorización de la integración de Yael, incluido el cierre
  de casos persistidos tras un reinicio del backend.

Los cinco casos que las reglas sugerían aceptar contra la referencia del corpus
no se convierten en aceptaciones automáticas. El piloto CLI también revisa lecturas
por defecto; --no-revisar-lecturas queda como opción explícita de comparación.

## Arranque local desde la nueva copia de trabajo

Requisitos: Docker Desktop, Ollama con qwen3-vl:4b-instruct y Node/npm para la
interfaz. Reutilizar la base y S3 locales existentes: no ejecutar down -v ni
recargar semillas sobre la base actual. Esta configuración usa AUTH_MODE=dev;
la identidad fija del frontend es solo para la demostración local.

Copiar `.env` desde la copia principal si la nueva copia aún no lo tiene:

```powershell
if (-not (Test-Path .env)) { Copy-Item "..\Banamex_Monorepo\.env" .env }
```

El contenedor debe alcanzar Ollama por host.docker.internal, no por localhost.
Si la sesión anterior tiene DATABASE_URL apuntando a localhost para Python en
Windows, sustituirla para los contenedores. Valores de desarrollo del proyecto:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://steward_backend:local-backend@postgres:5432/dsa_local"
$env:AUTH_MODE = "dev"
$env:VISION_MODELO = "qwen3-vl:4b-instruct"
$env:OLLAMA_BASE_URL = "http://host.docker.internal:11434"
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
```

La integración de chat exige CLAVE_IDENTIDAD_MCP para backend y MCP. Si falta en
el .env local, generar una clave exclusivamente de desarrollo sin imprimirla:

```powershell
if (-not (Select-String -Path .env -Pattern '^CLAVE_IDENTIDAD_MCP=.+' -Quiet)) {
    Add-Content -Path .env -Value ("`nCLAVE_IDENTIDAD_MCP=" + [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N'))
}
docker compose -f docker-compose.dev.yml up -d --build backend mcp
if ($LASTEXITCODE -ne 0) { throw "No se inició el backend integrado." }
Invoke-RestMethod http://localhost:8000/api/health
```

El proyecto Compose conserva el nombre dsa: este comando actualiza los servicios
locales existentes con el código de esta rama; no elimina sus volúmenes. No es
un despliegue al servidor compartido. Cambiar la rama original no activa esta
versión hasta reconstruir los servicios desde la copia deseada.

En otra terminal, dentro del frontend de esta copia:

```powershell
$env:VITE_API_URL = "http://localhost:8000"
$env:VITE_API_DEV_USUARIO = "dev-ana"
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Abrir http://127.0.0.1:5173. Con VITE_API_URL y VITE_API_DEV_USUARIO se usan los
endpoints reales; no las respuestas MSW. Subir un documento, comprobar los valores
contra el original y registrar una decisión con motivo. Una factura ya procesada
puede generar un aviso legítimo de duplicado debido al historial local.

## Alcance de la validación

Las pruebas HTTP nuevas ejercitan creación de un caso PDF, conservación de valores,
pausa humana, decisión explícita, bloqueo de decisión por otro usuario y respuesta
de detalle con avisos y conceptos. S3, extracción y sesiones están controlados en
esas pruebas; no se presentan como ejecuciones de Ollama o PostgreSQL reales.
El frontend compila con Vite. La validación real anterior es de CLI, no de navegador.

La reproducción de reglas sobre el corpus usó contexto sintético del repositorio;
los datos actuales de la base pueden producir hallazgos adicionales. No cambiar
el corpus ni interpretar la sugerencia humana obligatoria como exactitud de
clasificación. La prueba completa en navegador con S3, Ollama y PostgreSQL debe
realizarse en la laptop antes de grabar la demo.

Comprobaciones ejecutadas en esta integración: Datos 235 aprobadas/66 omitidas;
grafo de casos 58/1; API 16/0; backend 9/1; MCP 2/0. Total: 320 aprobadas y
68 omitidas. Ruff de datos/backend/MCP y compilación Vite aprobados. Las pruebas
omitidas requieren principalmente una base PostgreSQL de pruebas disponible.
No hubo una prueba de navegador ni un despliegue real desde este entorno.
