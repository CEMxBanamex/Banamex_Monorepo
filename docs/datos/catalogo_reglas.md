# Catálogo de reglas del piloto

_Generado con `datos/scripts/generar_docs.py`. No lo edites a mano._

Fuente: [`datos/reglas/catalogo.yaml`](../../datos/reglas/catalogo.yaml), única para `validar_reglas`, la tabla `reglas` y la verdad de referencia.

Efecto: **rechazo** → Rechazado si no hay dudas · **revision** → Requiere revisión humana · La revisión tiene precedencia sobre el rechazo.

## Historia 1 · Facturas

| Regla | Versión | Nombre | Política | Efecto | Qué comprueba |
|---|---|---|---|---|---|
| R-001 | 1.2 | Campos obligatorios de la factura | P-001 v3.0 §3 | rechazo | La factura debe mostrar folio, fecha, nombre y RFC del emisor, nombre y RFC del receptor, subtotal, impuestos, total y moneda. |
| R-002 | 2.0 | Formato de RFC en la factura | P-011 v2.0 §2 | rechazo | El RFC del emisor y del receptor deben tener la estructura de la política P-011 (12 caracteres persona moral, 13 persona física, con fecha válida). |
| R-003 | 1.0 | Confianza mínima de lectura | P-004 v1.0 §2 | revision | Si un campo usado por las reglas se leyó con confianza menor al umbral, una persona debe verificarlo contra el documento original. |
| R-004 | 1.1 | Fecha de emisión válida | P-001 v3.0 §4 | rechazo | La fecha de emisión no puede ser posterior a la fecha de recepción ni tener más de 365 días de antigüedad. |
| R-005 | 1.0 | Moneda admitida | P-001 v3.0 §5 | revision | Solo se procesan facturas en MXN o USD. Cualquier otra moneda la revisa Tesorería. |
| R-010 | 1.0 | Los conceptos suman el subtotal | P-002 v2.0 §3 | rechazo | La suma de los importes de los conceptos debe ser igual al subtotal, con la tolerancia de la política. |
| R-011 | 2.0 | Impuestos calculados con una tasa admitida | P-002 v2.0 §4 | rechazo | Los impuestos deben ser el subtotal por una tasa admitida de IVA (16 %, 8 % o 0 %). |
| R-014 | 2.1 | El total coincide con subtotal más impuestos | P-002 v2.0 §5 | rechazo | El total debe ser subtotal + impuestos − retenciones, con la tolerancia de la política. |
| R-015 | 1.0 | Factura duplicada | P-003 v1.2 §2 | rechazo | Un archivo idéntico a uno ya registrado se rechaza. Si coincide el RFC del emisor y el folio, pero el archivo es distinto, pasa a revisión humana. |
| R-017 | 1.0 | Proveedor registrado en el padrón | P-003 v1.2 §3 | revision | El RFC del emisor debe estar activo en el padrón de proveedores. Si no está, Compras debe validarlo. |
| R-018 | 1.0 | Receptor es una entidad del grupo | P-001 v3.0 §6 | rechazo | El RFC del receptor debe pertenecer a una de las entidades receptoras autorizadas. |
| R-021 | 1.2 | Monto que requiere revisión adicional | P-003 v1.2 §4 | revision | Las facturas con total igual o mayor a 250,000.00 MXN (o su equivalente en USD) las revisa una persona de supervisión. |
| R-030 | 1.0 | Instrucciones dirigidas al sistema dentro del documento | P-004 v1.0 §4 | revision | Si el documento contiene texto que intenta dar instrucciones al sistema, no se siguen, se reporta y una persona revisa el caso. |
| R-031 | 1.0 | Tipo de documento sin política aplicable | P-001 v3.0 §2 | revision | Esta política solo cubre facturas de proveedores. Notas de crédito, recibos y otros documentos requieren revisión humana. |

## Historia 2 · Registros de clientes

| Regla | Versión | Nombre | Política | Efecto | Qué comprueba |
|---|---|---|---|---|---|
| R-101 | 1.3 | Datos mínimos del cliente | P-007 v1.3 §2 | rechazo | Todo cliente dado de alta debe tener id_cliente, nombre, rfc, correo_contacto y alta. |
| R-102 | 1.0 | Formato del correo de contacto | P-007 v1.3 §3 | rechazo | El correo de contacto debe tener la forma usuario@dominio.ext. |
| R-103 | 2.0 | Formato de RFC del cliente | P-011 v2.0 §2 | rechazo | El RFC del cliente debe tener la estructura de la política P-011. |
| R-104 | 1.1 | Fecha de alta válida | P-015 v1.1 §2 | rechazo | La fecha de alta debe estar en formato DD/MM/AAAA, no ser futura y no ser anterior al 01/01/2000. |
| R-105 | 1.0 | Identificador de cliente único | P-018 v1.0 §2 | rechazo | Ningún id_cliente puede repetirse dentro del archivo. |
| R-106 | 1.0 | Columnas esperadas del archivo | P-007 v1.3 §4 | rechazo | El archivo debe contener las columnas de la política (se aceptan los alias listados). |

Parámetros globales: umbral de confianza 80 %, tolerancia de montos 0.05, tipo de cambio fijo 18.5 MXN/USD.
