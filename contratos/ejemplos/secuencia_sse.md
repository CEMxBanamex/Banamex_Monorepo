
# Ejemplo de secuencia SSE del chat

## 1. Objetivo

Esta secuencia muestra cómo el backend comunica el progreso del agente
y entrega una respuesta final mediante Server-Sent Events (SSE).

Cada evento se separa mediante una línea en blanco. El campo `event`
identifica el tipo de evento y `data` contiene un objeto JSON.

## 2. Secuencia de eventos

### 2.1 Inicio de identificación de consulta

event: paso
data: {"id":"paso-1","texto":"Identificando la consulta","detalle":"Clasificando la intención del usuario","estado":"en_curso"}

### 2.2 Identificación completada

event: paso
data: {"id":"paso-1","texto":"Identificando la consulta","detalle":"Clasificando la intención del usuario","estado":"completado"}

### 2.3 Inicio de consulta de facturas

event: paso
data: {"id":"paso-2","texto":"Consultando facturas","detalle":"Buscando registros en la base de datos","estado":"en_curso"}

### 2.4 Consulta completada

event: paso
data: {"id":"paso-2","texto":"Consultando facturas","detalle":"Se encontraron 12 registros","estado":"completado"}

### 2.5 Respuesta final

event: respuesta
data: {"respuesta":"Se encontraron 12 facturas.","caso_id":null,"simulado":false,"duracion_ms":850,"tipo":"datos","fuentes":["facturas"]}

## 3. Reglas del contrato

- Los eventos `paso` representan el progreso del agente.
- Cuando un paso cambia de estado, conserva el mismo `id`.
- Los estados permitidos son `pendiente`, `en_curso`, `completado` y `error`.
- El evento `respuesta` representa el resultado final del asistente.
- `tipo` clasifica la respuesta como `datos`, `politicas`, `informacion_general` o `mixta`.
- `fuentes` contiene identificadores de las fuentes utilizadas. Si no hay fuentes, se envía una lista vacía (`[]`).
- `caso_id` y `duracion_ms` pueden ser `null` cuando no estén disponibles.
- `simulado` indica si la respuesta es simulada.

## 4. Consideraciones para la integración

El backend debe serializar los modelos Pydantic como JSON dentro del campo `data`.

El frontend debe escuchar los eventos `paso` y `respuesta`, actualizar los pasos existentes usando su `id` y mostrar el contenido de la respuesta final.
