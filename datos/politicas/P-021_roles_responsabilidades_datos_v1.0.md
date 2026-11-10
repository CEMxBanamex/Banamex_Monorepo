---
id: P-021
nombre: Roles y responsabilidades sobre los datos
tipo: gobernanza
version: "1.0"
historia: null
area_responsable: Oficina de Gobierno de Datos
vigente_desde: 2026-02-01
vigente_hasta: null
estado: vigente
---

# P-021 · Roles y responsabilidades sobre los datos

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Definir quién es dueño de cada dominio de datos y quién lo cuida en el día a día.

## 2. Roles

- **Data owner (dueño de los datos):** dirección que responde por un dominio. Decide quién puede usar sus datos, aprueba su clasificación (P-020) y sus reglas de calidad (P-022).
- **Data steward (responsable de datos):** persona o equipo que mantiene el catálogo y las definiciones del dominio, revisa los resultados de calidad y atiende los incidentes.
- **Oficina de Gobierno de Datos:** mantiene esta política, el glosario y las métricas oficiales, y coordina a los data stewards.

## 3. Dueños por dominio

| Dominio | Tablas principales | Data owner | Data steward |
|---|---|---|---|
| Facturas | facturas, casos, hallazgos | Dirección de Cuentas por Pagar | Gobierno de Datos · Cuentas por Pagar |
| Proveedores | proveedores, órdenes de compra, entidades | Dirección de Compras | Datos Maestros de Compras |
| Pagos | pagos | Tesorería | Gobierno de Datos · Tesorería |
| Presupuesto | centros de costo | Dirección de Finanzas | Control Presupuestal |
| Clientes | clientes | Dirección de Banca Comercial | Gobierno de Datos · Clientes |
| Auditoría | bitácora, consultas libres, conversaciones | Contraloría Interna | Oficina de Gobierno de Datos |
| Gobernanza | políticas, reglas, catálogo, glosario, métricas | Oficina de Gobierno de Datos | Oficina de Gobierno de Datos |

Respuesta corta para el chat: **el dueño de los datos de proveedores es la Dirección de Compras**, y su responsable operativo es Datos Maestros de Compras.

## 4. Responsabilidades del data steward

- Mantener al día las fichas del catálogo de su dominio (descripción, sensibilidad, origen).
- Definir los términos de su dominio en el glosario.
- Revisar cada semana los resultados de calidad y abrir un incidente cuando una regla no alcanza su umbral.

## 5. Métricas oficiales

Las métricas de la capa semántica (monto facturado, tasa de rechazo, tiempo de revisión, entre otras) son definiciones oficiales. Solo la Oficina de Gobierno de Datos las cambia, con nueva versión.
