# Frente de Datos · Data Steward Agéntico

Responsables: Iris Balderas y Mario Oropeza. Esquema de la base, datos sintéticos del piloto, políticas, catálogo de reglas, RAG y tools de datos del servidor MCP.

## Inicio rápido

```bash
cd datos
pip install -r requirements.txt

# PostgreSQL 16 con pgvector (el docker-compose.dev.yml de 0.1.2 lo levanta; o bien):
docker run -d --name steward-db -e POSTGRES_PASSWORD=steward -p 5432:5432 pgvector/pgvector:pg16
export DATABASE_URL=postgresql+psycopg://postgres:steward@localhost:5432/postgres

alembic upgrade head                                   # crea el esquema (1.4.1)
python scripts/cargar_semilla.py --embeddings          # catálogos, reglas, políticas, histórico y casos demo (1.4.4)
pytest                                                 # pruebas unitarias; las de integración necesitan DATABASE_URL_PRUEBAS
```

Sin GPU, usa `EMBEDDING_PROVEEDOR=falso` para generar vectores de prueba. Con Ollama, configura `OLLAMA_URL`, `EMBEDDING_MODELO` y `EMBEDDING_DIM` según lo que se elija en 0.5.5 (por defecto `bge-m3`, 1024 dimensiones, multilingüe). **Cambiar la dimensión requiere una migración nueva.**

Los datos sintéticos ya están generados en `sinteticos/`. Para regenerarlos (son deterministas con la semilla 2026):

```bash
python scripts/generar_facturas.py && python scripts/generar_registros.py
```

## Qué hay aquí y a qué tarea corresponde

| Tarea | Entregable |
|---|---|
| 0.3.1–0.3.4 Esquema | `steward_datos/db/models.py` |
| 0.3.5 Diagrama ER | [`docs/datos/esquema.md`](../docs/datos/esquema.md) |
| 0.4.1–0.4.2 FATURA | `scripts/fatura_piloto.py` (revisar y seleccionar; ver abajo) |
| 0.7.2 Firmas de las tools | `steward_datos/contratos.py` y [`docs/datos/contratos_tools.md`](../docs/datos/contratos_tools.md) |
| 1.4.1 Migración | `alembic/versions/0001_esquema_inicial.py` |
| 1.4.2 Casos con errores | `sinteticos/facturas/`, `sinteticos/registros/` (generadores en `scripts/`) |
| 1.4.3 Verdad de referencia | Un `.json` junto a cada archivo, más `sinteticos/casos_referencia_*.json` |
| 1.4.4 Carga semilla | `scripts/cargar_semilla.py` |
| 1.5.1–1.5.2 Políticas | `politicas/*.md` |
| 1.5.3 Catálogo de reglas | `reglas/catalogo.yaml` y [`docs/datos/catalogo_reglas.md`](../docs/datos/catalogo_reglas.md) |
| 2.1.1 Fragmentación | `steward_datos/rag/fragmentar.py` |
| 2.1.2 Embeddings a pgvector | `steward_datos/rag/ingesta.py`, `rag/embeddings.py` |
| 2.2.1 `validar_reglas` + pruebas | `steward_datos/reglas/motor.py`, `tools/validar_reglas.py`, `tests/test_motor.py` |
| 2.2.2 `buscar_politicas` | `steward_datos/tools/buscar_politicas.py` |
| 2.2.3 `registrar_hallazgo` | `steward_datos/tools/registrar_hallazgo.py` |
| 3.1.1–3.1.2 `consultar_caso`, `buscar_facturas` | `steward_datos/tools/consultas_chat.py` |
| 3.1.3 Prueba de calidad del RAG | `evaluacion/preguntas_rag.yaml`, `scripts/evaluar_rag.py` |
| 3.2.1 `POST /politicas` | `steward_datos/api/politicas.py` (router para montar en el backend) |
| 4.3.1–4.3.3 Evaluación | `scripts/evaluar.py`, plantilla `evaluacion/linea_base_manual.csv` |
| 4.5.1 Inyección en factura | Escenarios `inyeccion_visible` e `inyeccion_oculta`, regla R-030 |
| 4.7.1 Casos de la demo | `sinteticos/facturas/demo/` y la semilla (ver guion abajo) |

## Datos sintéticos

### Facturas (Historia 1)

74 facturas en 4 diseños (clásica, banda de color, compacta y moderna) y 4 formatos (PNG, JPG, PDF con texto y PDF escaneado con ruido y rotación):

| Grupo | Casos | Para qué |
|---|---:|---|
| `historico` | 30 | Se cargan como casos ya revisados (F-1000 a F-1029). Sirven de antecedentes para duplicados y de datos para el chat. |
| `evaluacion` | 39 | Se suben por la aplicación y se comparan contra la verdad de referencia: 11 aceptados, 17 rechazados y 11 de revisión humana. |
| `demo` | 5 | F-1040, F-1041 y F-1042 (mismos IDs y montos que el mock del frontend), más dos archivos para subir en vivo. |

Los escenarios de evaluación cubren las 14 reglas de facturas: total que no cuadra, IVA mal calculado o con tasa no admitida, conceptos que no suman, campos faltantes, RFC inválidos, fecha futura o extemporánea, receptor ajeno, duplicado exacto y por folio, montos altos en MXN y USD, proveedor fuera del padrón, moneda EUR, escaneos degradados, instrucciones inyectadas (visibles y en texto casi blanco) y una nota de crédito.

Cada archivo tiene un `.json` con:

- `verdad.campos`: lo que está impreso, tal cual (lo que debería leer el modelo de visión).
- `verdad.normalizados`: montos y fecha normalizados.
- `confianza_simulada` y `lectura_simulada`: lo que usa la semilla para simular la salida del modelo (p. ej., F-1042 lee la fecha como 12/03/2026 con 62 %).
- `anotacion_fatura`: cajas por clase con los nombres de FATURA (`SELLER_NAME`, `DATE`, `TOTAL`...) en píxeles a 150 dpi; en los escaneos las cajas siguen la rotación.
- `texto_completo`: la capa de texto del documento.
- `esperado`: resultado y reglas que deben dispararse.

### Registros de clientes (Historia 2)

10 archivos `.xlsx`/`.csv`. `clientes_octubre.xlsx` es el caso V-0207 del frontend (8 de 120 sin correo, mismas filas) y `registros_prueba.csv` es V-0206 (archivo ilegible → estado `error`). Los demás cubren RFC inválidos, fechas imposibles o futuras, IDs repetidos, correos mal formados, columna faltante, alias de columnas y un archivo con varios errores.

> Las políticas y reglas de la Historia 2 son una propuesta sintética: el README general indica que los documentos reales están **por acordar con Banamex**.

### FATURA

El entorno donde se generó esto no tenía acceso a Zenodo, así que FATURA no viene incluido. Para 0.4.1 y 0.4.2:

```bash
# Descargar FATURA.zip de https://zenodo.org/records/10371464 y descomprimir
python scripts/fatura_piloto.py revisar --fatura ~/Descargas/FATURA
python scripts/fatura_piloto.py seleccionar --fatura ~/Descargas/FATURA --por-plantilla 2   # 100 facturas, 2 por plantilla
```

La selección queda en `sinteticos/fatura_piloto/` (ignorada por git) con la anotación convertida a nuestro formato. Las facturas de FATURA no son CFDI (no traen RFC del receptor ni moneda), así que sirven para medir la extracción por campo; las reglas se miden con nuestras facturas.

## Evaluación

```bash
python scripts/evaluar.py --referencia                      # prueba de cordura: debe dar 100 %
python scripts/evaluar.py --predicciones pred.jsonl --linea-base evaluacion/linea_base_manual.csv --salida reporte.md
EMBEDDING_PROVEEDOR=ollama python scripts/evaluar_rag.py    # acierto@1, acierto@5 y MRR del RAG
```

Con los embeddings falsos (sin GPU) el RAG da acierto@1 de 70 % y acierto@5 de 95 %; hay que repetirlo con el modelo real y usarlo para calibrar `RAG_UMBRAL_SIMILITUD`.

`linea_base_manual.csv` es la plantilla para medir la línea base (4.3.3): un analista revisa los mismos casos a mano y anota segundos y errores encontrados.

## Guion de la demo (4.7.1)

1. **Bandeja**: F-1040, F-1041, F-1042, V-0206 y V-0207 ya cargados por la semilla.
2. **F-1042** (Historia 1): diferencia de 400.00 en el total (R-014) y fecha leída con 62 % (R-003) → Requiere revisión humana. La bitácora muestra la corrección de la fecha a 12/08/2026.
3. **V-0207** (Historia 2): 8 clientes sin correo (R-101, política P-007) → Rechazado.
4. **En vivo**: subir `sinteticos/facturas/demo/demo_inyeccion.pdf`. El agente no obedece la instrucción y reporta R-030.
5. **En vivo**: subir `demo_nota_credito.pdf` → "No se encontró una regla aplicable" (R-031).
6. **Chat**: "¿Qué facturas no cuadran en el total?" (`buscar_facturas` con R-014) y "¿Qué tolerancia permite la política?" (`buscar_politicas`, cita P-002 v2.0 §5).

## Integración con los otros frentes

- **Infraestructura**: el `requirements.txt` va en las imágenes de `backend` y `mcp`; ambas necesitan el paquete `steward_datos`. El usuario de base `steward_mcp` solo necesita lectura más `INSERT` en `hallazgos` y `bitacora`. Los archivos se suben a S3 en `casos/<caso_id>/<archivo>` y `politicas/<archivo>`.
- **Agentes**: ver [`docs/datos/contratos_tools.md`](../docs/datos/contratos_tools.md). El grafo llama a `validar_reglas` y guarda con `persistencia.guardar_extraccion` y `guardar_resultado`. `registrar_tools_datos(mcp)` registra las cinco tools.
- **Frontend**: los hallazgos ya tienen la forma de `HALLAZGOS_FACTURA` en `data.js` (`titulo`, `texto`, `cifras`, `regla`, `version`, `evidencia`). En la semilla, los RFC son válidos y distintos del `XAXX010101000` del mock.
