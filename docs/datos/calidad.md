# Reglas de calidad de datos

_Generado con `datos/scripts/generar_docs.py`. No lo edites a mano._

Fuente: [`datos/gobernanza/calidad.yaml`](../../datos/gobernanza/calidad.yaml) · política P-022.

| Regla | Tabla | Columna | Dimensión | Umbral | Descripción |
|---|---|---|---|---:|---|
| RC-001 | facturas | emisor_rfc | completitud | 99.0 % | Toda factura tiene RFC del emisor. |
| RC-002 | facturas | folio | completitud | 99.0 % | Toda factura tiene folio. |
| RC-003 | facturas | folio | unicidad | 99.5 % | No hay dos facturas del mismo emisor con el mismo folio. |
| RC-004 | facturas | total | consistencia | 98.0 % | El total es subtotal + impuestos − retenciones (tolerancia 0.05). |
| RC-005 | facturas | — | oportunidad | 90.0 % | Las facturas se revisan en 48 horas o menos desde que se reciben. |
| RC-006 | proveedores | rfc | validez | 100.0 % | El RFC del proveedor tiene la estructura de P-011. |
| RC-007 | clientes | correo_contacto | completitud | 99.0 % | Todo cliente tiene correo de contacto. |
| RC-008 | clientes | correo_contacto | validez | 99.5 % | El correo de contacto tiene la forma usuario@dominio.ext. |
| RC-009 | clientes | rfc | validez | 99.5 % | El RFC del cliente tiene la estructura de P-011. |
| RC-010 | clientes | id_cliente | unicidad | 100.0 % | Ningún id_cliente se repite. |
| RC-011 | clientes | alta | completitud | 99.5 % | Todo cliente tiene fecha de alta. |
| RC-012 | ordenes_compra | centro_costo_id | completitud | 100.0 % | Toda orden de compra tiene centro de costo. |
| RC-013 | pagos | fecha_pago | oportunidad | 90.0 % | Los pagos se hacen a más tardar en la fecha programada. |
