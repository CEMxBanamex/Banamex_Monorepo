---
id: P-001
nombre: Recepción y validación de facturas de proveedores
tipo: facturas
version: "4.0"
historia: 1
area_responsable: Cuentas por Pagar
vigente_desde: 2026-11-01
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

Estos datos son los que el piloto revisa de los requisitos del artículo 29-A del Código Fiscal de la Federación (fracciones I, II, III, IV y VII). Los demás requisitos de ese artículo, como el régimen fiscal del emisor, el código postal y el uso fiscal del receptor o el sello digital, no los revisa el piloto.

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

## 8. Fundamento

- Código Fiscal de la Federación, artículo 29-A: requisitos que debe contener una factura electrónica (CFDI), entre ellos el RFC, nombre y régimen fiscal del emisor (fracción I), el folio y los sellos digitales (fracción II), el lugar y la fecha de expedición (fracción III), el RFC, nombre, código postal y uso fiscal del receptor (fracción IV) y el importe total con sus impuestos y la forma de pago (fracción VII). Desde la reforma publicada en el DOF el 7 de noviembre de 2025, la fracción IX exige además que la factura ampare operaciones reales (ver P-005).
- Anexo 20 de la Resolución Miscelánea Fiscal, versión 4.0 del CFDI: estándar técnico que define los campos del comprobante (Folio, Fecha, Emisor, Receptor, SubTotal, Total, Moneda) y los catálogos que deben usarse, como el de monedas.

## 9. Cambios respecto a la versión 3.0

- Se agrega el fundamento: artículo 29-A del Código Fiscal de la Federación y Anexo 20 (CFDI 4.0).
- La sección 3 indica qué requisitos del artículo 29-A revisa el piloto y cuáles no.
- Las reglas y los datos obligatorios no cambian.
