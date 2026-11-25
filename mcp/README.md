# Servidor MCP local (S1-27)

Ejemplo de desarrollo con el SDK MCP de Python 1.x y transporte stdio. El cliente inicia el servidor como subproceso. No se abre un puerto; no se necesita Ollama, base de datos, AWS ni una factura real.

> **Estructura (2026-11-11):** este código estaba en `agentes/`. El paquete del servidor es `mcp/steward_mcp/` y sus pruebas están en `mcp/tests/`. La carpeta `mcp/` no lleva `__init__.py` ni se importa, para no chocar con el SDK `mcp`; el servidor se ejecuta desde la raíz con `mcp/` en `PYTHONPATH` (`python -m steward_mcp.servidor`). Las pruebas ya lo configuran solas.

## Prueba local en Windows

Desde la raíz del monorepo, con el entorno virtual y las dependencias de Datos ya instalados:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\mcp\requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .\datos
.\.venv\Scripts\python.exe -m unittest discover -s mcp/tests -v
```

`pip install -e .\datos` instala `steward_datos` en modo editable: el servidor lo importa como `steward_datos`, igual que el resto del repo. Con Docker no hace falta: `make test` (o `docker compose -f docker-compose.dev.yml run --rm pruebas-mcp`) corre estas mismas pruebas.

Las pruebas arrancan el servidor, negocian la sesión MCP, listan las herramientas y hacen llamadas reales por stdio. El resultado esperado es `Ran 2 tests` y `OK`.

## Convención para copiar

- Una herramienta por archivo en `mcp/steward_mcp/tools/`; registrar cada una en `mcp/steward_mcp/servidor.py`.
- Tipar entrada y salida con Pydantic. La demo acepta `entrada.documento_id` y devuelve el contrato compartido `FacturaExtraida` para `DEMO-001`. Los campos sin datos se omiten.
- Obtener el rol del contexto proporcionado por el servidor. En este ejemplo local, el proceso requiere `AUTH_MODE=dev` y `MCP_DEV_ROL=analista` o `administrador`. La demo permite solo `analista` para demostrar la verificación. Esta configuración no autentica usuarios; al conectar un servidor de red habrá que validar el JWT y establecer el contexto por solicitud.
- Comunicar errores esperados con `ToolError` y un código estable. La demo usa `ROL_NO_AUTORIZADO` y `DOCUMENTO_NO_ENCONTRADO`; el cliente recibe `isError=true`.
- Emitir pasos breves mediante `ctx.report_progress`. El cliente debe solicitar progreso y luego puede mostrar los mensajes en el chat. La demo no implementa todavía el puente al frontend.

El nombre `extraer_campos_factura_demo` distingue la respuesta fija del extractor real. La firma definitiva y el transporte de integración quedan sujetos a la revisión S1-06.

## En contenedor (entorno local y AWS)

`mcp/Dockerfile` arranca el mismo servidor con `MCP_TRANSPORT=streamable-http`: escucha en el puerto 8001, ruta `/mcp`, solo dentro de la red de Docker (en local también en `127.0.0.1:8001`). Sin `MCP_TRANSPORT` sigue siendo stdio, como en las pruebas. `MCP_ALLOWED_HOSTS` limita los encabezados `Host` aceptados (protección contra DNS rebinding). El backend lo encuentra en `MCP_URL`.
