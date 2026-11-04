# Contratos de las tools del MCP (frente de Datos)

Borrador para la sesión de revisión de contratos (0.7.4). Los modelos Pydantic están en [`datos/steward_datos/contratos.py`](../../datos/steward_datos/contratos.py); este documento los resume.

## Lo que Datos necesita de Agentes

`extraer_campos_factura` debe devolver un **`FacturaExtraida`**:

```json
{
  "tipo_documento": "factura",
  "campos": {
    "folio":   {"valor": "A-1042",     "confianza": 97, "pagina": 1, "bbox": [1020, 160, 1171, 185]},
    "fecha":   {"valor": "12/03/2026", "confianza": 62, "pagina": 1, "bbox": [1000, 190, 1171, 215]},
    "total":   {"valor": "12,000.00",  "confianza": 95, "pagina": 1, "bbox": null}
  },
  "conceptos": [{"descripcion": "Servicio de consultoría", "cantidad": "1", "precio_unitario": "8,000.00", "importe": "8,000.00"}],
  "texto_completo": "Proveedor Demo SA\nRFC PDE200115AB3\n...",
  "modelo": "qwen2.5vl:7b",
  "paginas": 2
}
```

- Claves de `campos`: `folio, fecha, emisor_nombre, emisor_rfc, emisor_direccion, receptor_nombre, receptor_rfc, moneda, subtotal, impuestos, tasa_iva, retenciones, total, condiciones_pago`.
- `valor` va **tal como aparece** en el documento (texto). La normalización de montos y fechas la hace `validar_reglas`.
- Un campo que no aparece se omite o va con `valor: null`. Nunca se inventa.
- `confianza` de 0 a 100. Si el modelo no da confianza, Agentes define cómo estimarla (p. ej., logprobs o autoevaluación); la regla R-003 usa el umbral de 80.
- `texto_completo` lo usa R-030 para detectar instrucciones inyectadas.
- `bbox` en píxeles a 150 dpi, origen arriba a la izquierda (igual que nuestras anotaciones).

`leer_pdf_o_excel` para archivos tabulares debe devolver un **`TablaRegistros`**: `archivo`, `hoja`, `columnas` y `filas` (lista de diccionarios con valores en texto; la fila *n* del archivo es `filas[n-1]`). La función `leer_tabla()` de `steward_datos/sinteticos.py` es una implementación de referencia. Si el archivo no se puede leer, la tool lanza un error y el caso termina en estado `error` (caso V-0206).

## Tools de Datos

| Tool | Entrada | Salida | Escribe en la base |
|---|---|---|---|
| `validar_reglas` | `ValidarReglasEntrada`: `caso_id`, `historia` (1 o 2), `factura` o `registros`, `sha256`, `fecha_recepcion` | `ResultadoValidacion`: `reglas_evaluadas`, `hallazgos`, `resultado_sugerido`, `motivo` | No |
| `buscar_politicas` | `BuscarPoliticasEntrada`: `consulta`, `k`, `historia`, `fecha`, `reglas` | `BuscarPoliticasSalida`: `fragmentos` (con política, versión, vigencia, sección, similitud), `sin_resultados` | No |
| `registrar_hallazgo` | `RegistrarHallazgoEntrada`: `caso_id`, `hallazgo`, `origen`, `fragmentos_ids` | `hallazgo_id`, `evento_id` | `hallazgos`, `bitacora` |
| `consultar_caso` | `caso_id` | `CasoOut`: estado, resultado, campos, hallazgos y eventos | No |
| `buscar_facturas` | `BuscarFacturasEntrada`: filtros cerrados (proveedor, folio, fechas, montos, moneda, resultado, estado, regla) | `BuscarFacturasSalida` | No |

### Forma de un hallazgo (`HallazgoOut`)

Coincide con lo que dibuja el frontend en `Detalle.jsx` y `Validacion.jsx`:

```json
{
  "regla_id": "R-014", "regla_version": "2.1", "politica_id": "P-002",
  "efecto": "rechazo", "severidad": "error",
  "titulo": "El total no coincide con subtotal más impuestos",
  "texto": "La suma de subtotal e impuestos da un valor distinto al total impreso en la factura.",
  "cifras": [["Esperado", "11,600.00"], ["Encontrado", "12,000.00"], ["Diferencia", "400.00"]],
  "campos": ["total"], "filas": null,
  "evidencia": "página 1, total",
  "evidencia_detalle": {"pagina": 1, "campo": "total", "bbox": [880, 520, 1171, 545]}
}
```

`severidad` es la del ícono en la interfaz (`error`, `adv`, `info`); `efecto` es el que decide el resultado.

### Cómo se decide el resultado sugerido

1. Si algún hallazgo tiene efecto **revision** (baja confianza, monto alto, proveedor fuera del padrón, posible duplicado, moneda no admitida, instrucciones inyectadas, documento sin política) → **Requiere revisión humana**.
2. Si no, y algún hallazgo tiene efecto **rechazo** → **Rechazado**.
3. Si no hay hallazgos → **Aceptado**.

La incertidumbre gana sobre el rechazo porque un dato mal leído puede producir un incumplimiento falso (README · "si hay dudas, pide revisión humana").

### Guardar el resultado

`steward_datos.persistencia` tiene dos funciones para `procesar_caso()`:

- `guardar_extraccion(s, caso_id, factura)` llena `facturas`, `conceptos_factura`, `campos_extraidos` y registra el evento de extracción.
- `guardar_resultado(s, resultado)` guarda los hallazgos, sus eventos, el resultado sugerido y pasa el caso a `revision`.

### Registro en el servidor MCP

```python
from mcp.server.mcpserver import MCPServer   # mcp 1.x: from mcp.server.fastmcp import FastMCP
from steward_datos.mcp_registro import registrar_tools_datos

mcp = MCPServer("data-steward")
registrar_tools_datos(mcp)
```

## Pendiente de acordar en 0.7.4

- Cómo obtiene Agentes la confianza por campo del modelo de visión.
- Si `validar_reglas` debe llamar a `registrar_hallazgo` por su cuenta o si el grafo guarda todo al final con `guardar_resultado` (propuesta: lo segundo, en un solo paso, para que un caso no quede con hallazgos a medias).
- Umbral de similitud del RAG (`RAG_UMBRAL_SIMILITUD`) una vez elegido el modelo de embeddings (0.5.5).
