---
id: P-003
nombre: Facturas que requieren revisión adicional
version: "1.2"
historia: 1
area_responsable: Cuentas por Pagar · Supervisión
vigente_desde: 2026-04-01
vigente_hasta: null
estado: vigente
---

# P-003 · Facturas que requieren revisión adicional

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Identificar las situaciones en que una factura, aunque sea aritméticamente correcta, debe revisarla una persona antes de continuar su trámite.

## 2. Duplicados

Antes de tramitar una factura se busca si ya fue registrada (regla **R-015 v1.0**):

- Si el archivo es idéntico a uno ya registrado (mismo contenido), se trata de una factura duplicada y se sugiere el resultado Rechazado.
- Si coinciden el RFC del emisor y el folio con una factura registrada, pero el archivo es distinto, puede ser una reexpedición o un error del proveedor. El caso pasa a revisión humana y se indica el caso anterior con el que coincide.

## 3. Padrón de proveedores

El RFC del emisor debe estar activo en el padrón de proveedores autorizados (regla **R-017 v1.0**). Si no aparece o está inactivo, el caso pasa a revisión humana para que el área de Compras confirme el alta del proveedor. No se rechaza automáticamente.

## 4. Montos altos

Las facturas con un total igual o mayor a 250,000.00 MXN requieren la revisión de una persona de supervisión (regla **R-021 v1.2**). Para facturas en USD se usa, durante el piloto, un tipo de cambio fijo de 18.50 MXN por dólar. El agente marca el caso como Requiere revisión humana y lo indica en la explicación; el analista decide si lo escala.

## 5. Escalamiento

Cualquier analista puede escalar un caso a supervisión aunque el agente no lo sugiera. El escalamiento queda registrado en la bitácora con la persona que lo hizo y el motivo.
