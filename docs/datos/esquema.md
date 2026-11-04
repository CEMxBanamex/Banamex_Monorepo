# Esquema de la base de datos

Tareas 0.3.1 a 0.3.5. Fuente de verdad: [`datos/steward_datos/db/models.py`](../../datos/steward_datos/db/models.py) y la migración [`0001_esquema_inicial.py`](../../datos/alembic/versions/0001_esquema_inicial.py).

## Diagrama entidad-relación

```mermaid
erDiagram
    casos ||--o{ documentos : "tiene"
    casos ||--o| facturas : "Historia 1"
    facturas ||--o{ conceptos_factura : "líneas"
    casos ||--o{ campos_extraidos : "campos leídos"
    casos ||--o{ hallazgos : "genera"
    reglas ||--o{ hallazgos : "aplica"
    casos ||--o{ bitacora : "registra"
    hallazgos |o--o{ bitacora : "referencia"
    politicas ||--o{ politica_fragmentos : "se divide en"
    casos |o--o{ conversaciones : "chat del caso"
    conversaciones ||--o{ mensajes : "contiene"

    casos {
        string id PK "F-1042, V-0207"
        string tipo "factura | validacion"
        string estado "procesando | revision | revisado | error"
        string resultado_sugerido "aceptado | rechazado | humana"
        string resultado_final "decisión del analista"
        text explicacion
        uuid thread_id UK "LangGraph"
        text responsable_id "sub de Cognito"
        timestamptz creado_en
    }
    documentos {
        bigint id PK
        string caso_id FK
        text s3_key UK
        string sha256 "duplicados exactos (R-015)"
        smallint paginas
    }
    facturas {
        string caso_id PK, FK
        text tipo_documento
        text folio
        date fecha_emision
        string emisor_rfc
        string receptor_rfc
        string moneda
        numeric subtotal
        numeric impuestos
        numeric retenciones
        numeric total
        text modelo_extraccion
        jsonb salida_cruda
    }
    conceptos_factura {
        bigint id PK
        string caso_id FK
        text descripcion
        numeric importe
    }
    campos_extraidos {
        bigint id PK
        string caso_id FK
        text campo
        text valor
        smallint confianza "0 a 100"
        jsonb bbox
        text valor_corregido
        text corregido_por
    }
    reglas {
        string id PK "R-014"
        string version PK "2.1"
        string politica_id
        string efecto "rechazo | revision | informativo"
        jsonb parametros
    }
    hallazgos {
        bigint id PK
        string caso_id FK
        string regla_id FK
        string regla_version FK
        string severidad "error | adv | info"
        text titulo
        jsonb cifras "Esperado, Encontrado, Diferencia"
        int_array filas "Historia 2"
        text evidencia "página 1, total"
        bigint_array fragmentos_ids "citas del RAG"
        string origen "codigo | llm | lstm | humano"
    }
    bitacora {
        bigint id PK "EV-3000 en adelante"
        timestamptz fecha
        string caso_id FK
        string actor_tipo "agente | usuario | sistema"
        text actor_nombre
        string accion
        string tono
        text detalle
        string regla_id
        jsonb datos "antes, despues"
    }
    politicas {
        string id PK "P-002"
        string version PK "2.0"
        smallint historia "NULL = ambas"
        date vigente_desde
        date vigente_hasta
        string estado "vigente | reemplazada | borrador"
        text fuente_s3_key
        string sha256
    }
    politica_fragmentos {
        bigint id PK
        string politica_id FK
        string politica_version FK
        text seccion
        text texto
        text_array reglas
        vector embedding "pgvector, índice HNSW coseno"
        text modelo_embedding
    }
    conversaciones {
        uuid id PK
        text usuario_id
        string caso_id FK "NULL = Asistente"
        uuid thread_id UK
    }
    mensajes {
        bigint id PK
        uuid conversacion_id FK
        string rol "usuario | asistente | sistema"
        text contenido
        jsonb pasos "línea de pasos del chat"
        jsonb citas
        int duracion_ms
    }
    proveedores {
        string rfc PK
        text razon_social
        bool activo
    }
    entidades_receptoras {
        string rfc PK
        text razon_social
    }
```

`proveedores` y `entidades_receptoras` son catálogos sin relación formal: las reglas R-017 y R-018 los consultan por RFC.

## Decisiones

| Decisión | Por qué |
|---|---|
| Catálogos de valores como texto con `CHECK`, no `ENUM` | Agregar un estado nuevo es un `ALTER ... CHECK`, no una migración de tipo. |
| `casos.id` legible (`F-1042`, `V-0207`) generado con secuencias | Es el ID que ve el analista; coincide con el frontend. Secuencias en `F-1100` y `V-0208` para no chocar con la semilla. |
| `campos_extraidos` aparte de `facturas` | La interfaz muestra confianza y correcciones por campo; `facturas` guarda los valores normalizados para consultas (`buscar_facturas`). |
| `valor` y `valor_corregido` separados | La corrección humana no borra lo que leyó el modelo; las dos versiones quedan para auditoría y evaluación. |
| Hallazgos con FK a `(regla_id, regla_version)` | Cada hallazgo apunta a una versión exacta de la regla, como exige el README. |
| Bitácora solo de inserción (trigger) | Es el registro oficial: un `UPDATE` o `DELETE` falla aunque lo intente el backend. |
| `politicas.historia` NULL = ambas | P-011 (RFC) aplica a facturas y a registros. |
| `modelo_embedding` en cada fragmento | `buscar_politicas` filtra por el modelo configurado, así nunca compara vectores de modelos distintos. |
| `mensajes.pasos` en JSONB | Guarda tal cual la línea de pasos que mostró el chat (eventos SSE), para reconstruir la conversación. |
| Checkpoints de LangGraph fuera del esquema | Los crea `PostgresSaver.setup()`; `alembic/env.py` los ignora al autogenerar. |

## Permisos (mínimo privilegio)

La migración otorga permisos si existen los usuarios que crea Infraestructura (1.3.2):

| Usuario | Permisos |
|---|---|
| `steward_backend` | Lectura y escritura en todas las tablas, excepto `UPDATE`/`DELETE` en `bitacora`. |
| `steward_mcp` | Solo lectura, más `INSERT` en `hallazgos` y `bitacora` (lo que necesita `registrar_hallazgo`). |
