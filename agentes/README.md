# Servidor MCP local (S1-27)

Ejemplo de desarrollo con el SDK MCP de Python 1.x y transporte stdio. El cliente inicia el servidor como subproceso. No se abre un puerto; no se necesita Ollama, base de datos, AWS ni una factura real.

## Prueba local en Windows

Desde la raíz del monorepo, con el entorno virtual y las dependencias de Datos ya instalados:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\agentes\requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s agentes/tests -v
```

Las pruebas arrancan el servidor, negocian la sesión MCP, listan las herramientas y hacen llamadas reales por stdio. El resultado esperado es `Ran 2 tests` y `OK`.

## Convención para copiar

- Una herramienta por archivo en `agentes/tools/`; registrar cada una en `servidor.py`.
- Tipar entrada y salida con Pydantic. La demo acepta `entrada.documento_id` y devuelve el contrato compartido `FacturaExtraida` para `DEMO-001`. Los campos sin datos se omiten.
- Obtener el rol del contexto proporcionado por el servidor. En este ejemplo local, el proceso requiere `AUTH_MODE=dev` y `MCP_DEV_ROL=analista` o `administrador`. La demo permite solo `analista` para demostrar la verificación. Esta configuración no autentica usuarios; al conectar un servidor de red habrá que validar el JWT y establecer el contexto por solicitud.
- Comunicar errores esperados con `ToolError` y un código estable. La demo usa `ROL_NO_AUTORIZADO` y `DOCUMENTO_NO_ENCONTRADO`; el cliente recibe `isError=true`.
- Emitir pasos breves mediante `ctx.report_progress`. El cliente debe solicitar progreso y luego puede mostrar los mensajes en el chat. La demo no implementa todavía el puente al frontend.

El nombre `extraer_campos_factura_demo` distingue la respuesta fija del extractor real. La firma definitiva y el transporte de integración quedan sujetos a la revisión S1-06.
