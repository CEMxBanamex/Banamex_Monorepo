---
id: P-001
nombre: Recepción y validación de facturas de proveedores
tipo: facturas
version: "3.0"
historia: 1
area_responsable: Cuentas por Pagar
vigente_desde: 2026-01-15
vigente_hasta: null
estado: vigente
---

# P-001 · Recepción y validación de facturas de proveedores

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Establecer los requisitos mínimos que debe cumplir una factura de proveedor antes de que el área de Cuentas por Pagar la considere para su trámite. Esta política no autoriza pagos: solo define cuándo una factura cumple las reglas de recepción. La decisión final siempre la toma una persona autorizada.

## 2. Alcance

Aplica a facturas emitidas por proveedores a cualquiera de las entidades receptoras del grupo. No cubre notas de crédito, recibos de honorarios, recibos simples, estados de cuenta ni otros documentos. Cuando se reciba un documento que no sea una factura de proveedor, no existe regla aplicable y el caso debe pasar a revisión humana (regla **R-031 v1.0**).

## 3. Datos obligatorios

Toda factura debe mostrar de forma legible los siguientes datos (regla **R-001 v1.2**):

- Folio de la factura.
- Fecha de emisión.
- Nombre o razón social del emisor y su RFC.
- Nombre o razón social del receptor y su RFC.
- Subtotal, impuestos trasladados y total.
- Moneda.

Si falta cualquiera de estos datos, la factura no cumple la política y se sugiere el resultado Rechazado. El RFC del emisor y del receptor se valida además contra la estructura definida en la política P-011 (regla **R-002 v2.0**).

## 4. Fecha de emisión

La fecha de emisión no puede ser posterior a la fecha en que se recibe la factura, ni tener más de 365 días naturales de antigüedad respecto a esa fecha (regla **R-004 v1.1**). Las facturas con fecha futura o extemporánea no cumplen la política.

## 5. Moneda

Solo se procesan facturas en pesos mexicanos (MXN) o dólares estadounidenses (USD) (regla **R-005 v1.0**). Las facturas en cualquier otra moneda no se rechazan automáticamente: se turnan a Tesorería para revisión humana, porque requieren un tipo de cambio autorizado.

## 6. Receptor

El RFC del receptor debe corresponder a una de las entidades receptoras autorizadas del grupo (regla **R-018 v1.0**). Una factura emitida a un tercero no se puede tramitar y se sugiere el resultado Rechazado.

## 7. Relación con otras políticas

- El cálculo de subtotal, impuestos y total se rige por P-002.
- Los casos que requieren revisión adicional (duplicados, proveedores fuera del padrón y montos altos) se rigen por P-003.
- Los umbrales de lectura automatizada y el tratamiento de contenido sospechoso se rigen por P-004.
