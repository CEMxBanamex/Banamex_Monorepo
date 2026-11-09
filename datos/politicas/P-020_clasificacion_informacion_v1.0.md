---
id: P-020
nombre: Clasificación de la información
tipo: gobernanza
version: "1.0"
historia: null
area_responsable: Oficina de Gobierno de Datos
vigente_desde: 2026-02-01
vigente_hasta: null
estado: vigente
---

# P-020 · Clasificación de la información

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Definir los niveles de sensibilidad de los datos y cómo se protege cada uno. Toda tabla y columna del catálogo de datos tiene un nivel asignado.

## 2. Niveles de sensibilidad

| Nivel | Qué incluye | Quién lo ve |
|---|---|---|
| Público | Datos que pueden publicarse sin daño: monedas, nombres de entidades del grupo. | Cualquier usuario. |
| Interno | Datos de operación sin datos personales: facturas, proveedores (personas morales), órdenes de compra, casos y hallazgos. | Personal autorizado según su rol y sus entidades. |
| Confidencial | Datos personales y datos financieros sensibles: nombre, RFC y correo de clientes personas físicas; pagos; presupuestos. | Solo roles autorizados. Para el resto se enmascaran. |
| Restringido | Registros de auditoría y permisos de acceso. | Solo administración y auditoría. |

## 3. Datos personales

Es dato personal cualquier información que identifique o haga identificable a una persona física, como su nombre, RFC, correo o teléfono. Los datos personales se clasifican al menos como confidenciales. El RFC de una persona moral (por ejemplo, un proveedor) no es dato personal y se clasifica como interno.

Respuesta corta para el chat: **el RFC es dato sensible cuando pertenece a una persona física** (clientes), y es dato interno cuando pertenece a una persona moral (proveedores).

## 4. Protección por nivel

- Los datos confidenciales se enmascaran en las vistas consultables para quien no es administrador (por ejemplo, el RFC del cliente muestra solo sus primeras cuatro letras). Ver P-023.
- Los datos restringidos no se exponen en las vistas consultables.
- Ningún dato se copia fuera del entorno del piloto. El piloto solo usa datos sintéticos.

## 5. Asignación del nivel

El data steward de cada dominio propone el nivel de cada tabla y columna y el data owner lo aprueba (P-021). El nivel queda en el catálogo de datos.
