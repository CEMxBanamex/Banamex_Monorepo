---
id: P-005
nombre: Proveedores publicados en la lista 69-B del SAT
tipo: facturas
version: "1.0"
historia: 1
area_responsable: Cuentas por Pagar · Fiscal
vigente_desde: 2026-10-01
vigente_hasta: null
estado: vigente
---

# P-005 · Proveedores publicados en la lista 69-B del SAT

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Evitar que se tramiten facturas de proveedores que el SAT publicó por emitir comprobantes que amparan operaciones inexistentes, conforme al artículo 69-B del Código Fiscal de la Federación.

## 2. Lista que se consulta

El SAT publica la relación de contribuyentes del artículo 69-B con su situación: presunto, desvirtuado, definitivo o sentencia favorable. Antes de tramitar una factura se busca el RFC del emisor en la versión vigente de esa lista (regla **R-019 v1.0**). En el piloto se usa una lista de prueba con RFC sintéticos.

## 3. Qué se hace según la situación

- **Definitivo:** el SAT confirmó que el contribuyente emitió comprobantes de operaciones inexistentes. Sus facturas no producen efectos fiscales, así que se sugiere el resultado Rechazado y se avisa a Fiscal.
- **Presunto:** el SAT presume operaciones inexistentes, pero el contribuyente aún puede desvirtuarlo. El caso pasa a revisión humana; Compras y Fiscal deciden si la operación continúa.
- **Desvirtuado o sentencia favorable:** el contribuyente demostró que sus operaciones existen. La factura sigue su trámite normal.

## 4. Responsables

Fiscal actualiza la lista al menos una vez al mes con la publicación del SAT. Cuentas por Pagar no libera pagos a un proveedor con situación definitiva.
