---
id: P-002
nombre: Cálculo de importes e impuestos en facturas
tipo: facturas
version: "1.0"
historia: 1
area_responsable: Contraloría Fiscal
vigente_desde: 2025-01-01
vigente_hasta: 2025-12-31
estado: reemplazada
---

# P-002 · Cálculo de importes e impuestos en facturas (versión anterior)

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. Esta versión fue reemplazada por la 2.0 y se conserva para probar que el RAG respeta la vigencia.

## 1. Objetivo

Definir cómo se comprueba que los importes de una factura son consistentes.

## 2. Tolerancia

Se admite una diferencia de hasta 1.00 unidad de la moneda de la factura en cada comprobación.

## 3. Tasa de IVA

Los impuestos deben ser iguales al subtotal multiplicado por 16 %. No se admite otra tasa.

## 4. Total de la factura

El total debe ser igual al subtotal más los impuestos. Las retenciones no se consideran en esta versión.
