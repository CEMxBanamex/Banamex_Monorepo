---
id: P-002
nombre: Cálculo de importes e impuestos en facturas
tipo: facturas
version: "3.0"
historia: 1
area_responsable: Contraloría Fiscal
vigente_desde: 2026-11-01
vigente_hasta: null
estado: vigente
---

# P-002 · Cálculo de importes e impuestos en facturas

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Definir cómo se comprueba que los importes de una factura son aritméticamente consistentes. Estas comprobaciones las realiza código determinista; el modelo de lenguaje no calcula sumas ni impuestos.

## 2. Tolerancia

Por redondeos, se admite una diferencia de hasta 0.05 unidades de la moneda de la factura en cada comprobación de esta política. Cualquier diferencia mayor se reporta con el valor esperado, el valor encontrado y la diferencia.

## 3. Conceptos y subtotal

La suma de los importes de todos los conceptos debe ser igual al subtotal de la factura (regla **R-010 v1.0**). Si la suma no coincide, la factura no cumple la política.

## 4. Tasas de IVA

Los impuestos trasladados deben ser iguales al subtotal multiplicado por una tasa admitida de IVA (regla **R-011 v2.0**). Las tasas admitidas son:

- 16 % (tasa general).
- 8 % (región fronteriza).
- 0 % (actos con tasa cero).

Si los impuestos no corresponden a ninguna tasa admitida, la factura no cumple la política.

## 5. Total de la factura

El total debe ser igual al subtotal más los impuestos trasladados, menos las retenciones si las hay (regla **R-014 v2.1**). Cuando el total impreso no coincide, se reportan el total esperado, el total encontrado y la diferencia, y se sugiere el resultado Rechazado, salvo que alguno de los datos se haya leído con baja confianza, en cuyo caso una persona debe verificarlo (ver P-004).

## 6. Fundamento

- Código Fiscal de la Federación, artículo 29-A: la factura debe señalar la cantidad, unidad y descripción de los bienes o servicios (fracción V), el valor unitario (fracción VI) y el importe total, con los impuestos trasladados desglosados por tasa y los impuestos retenidos (fracción VII).
- Anexo 20 de la Resolución Miscelánea Fiscal, versión 4.0 del CFDI: define el importe de cada concepto, el SubTotal como la suma de esos importes, el total de impuestos trasladados y retenidos, y el Total del comprobante. Las comprobaciones de las secciones 3 a 5 siguen esa misma relación entre campos.

## 7. Cambios respecto a la versión 2.0

- Se agrega el fundamento: artículo 29-A del Código Fiscal de la Federación y Anexo 20 (CFDI 4.0).
- La tolerancia, las tasas admitidas y las reglas no cambian.
