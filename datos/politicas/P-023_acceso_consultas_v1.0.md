---
id: P-023
nombre: Acceso a datos desde el chat
tipo: gobernanza
version: "1.0"
historia: null
area_responsable: Oficina de Gobierno de Datos
vigente_desde: 2026-03-01
vigente_hasta: null
estado: vigente
---

# P-023 · Acceso a datos desde el chat

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Definir qué datos puede consultar una persona desde el chat y con qué controles.

## 2. Solo vistas consultables

Las consultas del chat leen únicamente vistas consultables (por ejemplo, facturas, proveedores, casos, hallazgos, órdenes de compra, pagos, centros de costo y clientes). Las tablas internas, la bitácora y los permisos no se consultan desde el chat.

## 3. Seguridad por fila

- El rol y el usuario salen del inicio de sesión, nunca del texto de la pregunta.
- El administrador ve todas las entidades del grupo.
- Un analista ve solo las entidades que tiene asignadas. Si no tiene ninguna, no ve datos.
- Los casos de validación de registros los ve su responsable y el administrador.

## 4. Enmascaramiento

Para quien no es administrador, el RFC y el correo de los clientes se muestran enmascarados (P-020). Las métricas agregadas no exponen datos personales.

## 5. Orden de las consultas

1. Si la pregunta corresponde a una métrica oficial, se usa la métrica.
2. Si pide registros puntuales, se usa la búsqueda de facturas.
3. Solo si no encaja, se permite una consulta libre validada: una sola sentencia SELECT, solo sobre vistas consultables, con límite de filas y tiempo máximo. Cada consulta libre queda registrada.

## 6. Prohibiciones

El chat no modifica datos, no libera pagos ni cambia el resultado de un caso.
