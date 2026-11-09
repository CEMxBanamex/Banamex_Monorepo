# Glosario de negocio

_Generado con `datos/scripts/generar_docs.py`. No lo edites a mano._

Fuente: [`datos/gobernanza/glosario.yaml`](../../datos/gobernanza/glosario.yaml) · actualizado 2026-11-09.

| Término | Definición | Sinónimos | Dueño | Fuente |
|---|---|---|---|---|
| **Bitácora de auditoría** | Registro oficial de quién hizo qué, sobre qué caso y cuándo. Solo admite inserciones. | bitácora, registro de auditoría | Contraloría Interna | P-021 |
| **Caso** | Unidad de trabajo del Data Steward. Se crea al subir una factura (F-) o un archivo de registros (V-) y termina con la decisión de un analista. | caso de revisión | Oficina de Gobierno de Datos | README del proyecto |
| **Centro de costo** | Unidad presupuestal a la que se carga un gasto. | CC, centro de gasto | Dirección de Finanzas | P-021 |
| **Clasificación de la información** | Nivel de sensibilidad de un dato (público, interno, confidencial o restringido) que define quién puede verlo y cómo se protege. | nivel de sensibilidad, clasificación de sensibilidad | Oficina de Gobierno de Datos | P-020 |
| **Completitud** | Dimensión de calidad que mide qué porcentaje de registros tiene un dato obligatorio. | datos completos | Oficina de Gobierno de Datos | P-022 |
| **Confianza de lectura** | Porcentaje de 0 a 100 que indica qué tan seguro está el modelo de visión de un campo leído. Debajo de 80 % el campo se marca como dudoso. | confianza, nivel de confianza | Gobierno de Datos · Cuentas por Pagar | P-004 |
| **Data owner** | Dirección que es dueña de un dominio de datos. Decide quién puede usarlos, aprueba sus reglas de calidad y responde por ellos. | dueño de los datos, propietario de datos | Oficina de Gobierno de Datos | P-021 |
| **Data steward** | Responsable operativo de un dominio de datos. Mantiene el catálogo, las definiciones y las reglas de calidad, y atiende sus incidentes. | custodio de datos, responsable de datos | Oficina de Gobierno de Datos | P-021 |
| **Dato personal** | Información que identifica o hace identificable a una persona física, como su nombre, RFC, correo o teléfono. Se clasifica al menos como confidencial. | dato sensible, información personal | Oficina de Gobierno de Datos | P-020 |
| **Enmascaramiento** | Mostrar solo parte de un dato confidencial (por ejemplo, las primeras letras del RFC) a quien no tiene permiso de verlo completo. | ofuscación | Oficina de Gobierno de Datos | P-023 |
| **Entidad receptora** | Empresa del grupo a la que va dirigida una factura. Solo se tramitan facturas dirigidas a una entidad autorizada. | receptor, entidad del grupo | Dirección de Compras | P-001 |
| **Factura conciliada** | Factura aceptada cuyo total coincide con el monto de su orden de compra y con el pago registrado por Tesorería, con una tolerancia de 0.05. | conciliación, factura cuadrada con la OC | Dirección de Cuentas por Pagar | métrica tasa_conciliacion |
| **Factura extemporánea** | Factura con más de 365 días de antigüedad al recibirse; no cumple la política P-001. | factura vencida | Dirección de Cuentas por Pagar | P-001 |
| **Hallazgo** | Incumplimiento u observación que encuentra el agente al aplicar una regla, con la regla y su versión, la evidencia y una explicación. | observación, incumplimiento | Oficina de Gobierno de Datos | catálogo de reglas |
| **Monto facturado** | Suma del total de las facturas no rechazadas, en pesos. Las facturas en USD se convierten al tipo de cambio fijo del piloto (18.50). | gasto facturado, facturación | Dirección de Cuentas por Pagar | métrica monto_facturado |
| **Oportunidad** | Dimensión de calidad que mide qué porcentaje de registros se procesó dentro del plazo esperado. | puntualidad | Oficina de Gobierno de Datos | P-022 |
| **Orden de compra** | Documento de Compras que autoriza un gasto con un proveedor, un centro de costo y un monto, antes de que llegue la factura. | OC, pedido | Dirección de Compras | P-021 |
| **Padrón de proveedores** | Lista oficial de proveedores autorizados que mantiene Compras. | catálogo de proveedores | Dirección de Compras | P-003 |
| **Pago** | Desembolso que registra Tesorería por una factura aceptada. El sistema solo lo consulta; ninguna tool lo crea ni lo libera. | desembolso | Tesorería | P-021 |
| **Política vigente** | Versión de una política cuya fecha de vigencia incluye el día de la consulta. El agente solo cita políticas vigentes, salvo que se pida otra versión. | versión vigente | Oficina de Gobierno de Datos | P-004 |
| **Proveedor** | Persona moral o física que emite facturas a una entidad del grupo. | emisor, vendedor | Dirección de Compras | P-003 |
| **Proveedor activo** | Proveedor que aparece activo en el padrón; solo a ellos se les tramitan facturas sin revisión adicional. | proveedor autorizado | Dirección de Compras | P-003 |
| **Regla de calidad** | Medición periódica de una dimensión de calidad sobre una tabla, con un umbral mínimo de cumplimiento. | control de calidad | Oficina de Gobierno de Datos | P-022 |
| **Regla de negocio** | Comprobación determinista del catálogo de reglas (R-001 a R-106) con identificador, versión y política que la sustenta. La evalúa código, no el modelo. | regla, regla del catálogo | Oficina de Gobierno de Datos | reglas/catalogo.yaml |
| **Resultado sugerido** | Lo que recomienda el agente para un caso (Aceptado, Rechazado o Requiere revisión humana). La decisión final siempre la toma un analista. | recomendación del agente, sugerencia | Oficina de Gobierno de Datos | P-001 |
| **Revisión humana** | Resultado que sugiere el agente cuando hay incertidumbre (baja confianza de lectura, monto alto, posible duplicado, falta de política) y una persona debe decidir. | requiere revisión humana, escalamiento | Oficina de Gobierno de Datos | P-004 |
| **RFC** | Registro Federal de Contribuyentes. 12 caracteres para persona moral y 13 para persona física. El de una persona física es un dato personal. | registro federal de contribuyentes | Oficina de Gobierno de Datos | P-011 y P-020 |
| **Tasa de conciliación** | Porcentaje de facturas aceptadas que están conciliadas. |  | Dirección de Cuentas por Pagar | métrica tasa_conciliacion |
| **Tasa de rechazo** | Porcentaje de facturas cuyo resultado vigente es Rechazado, sobre el total de facturas del periodo. | porcentaje de rechazo | Dirección de Cuentas por Pagar | métrica tasa_rechazo |
| **Tiempo de revisión** | Horas entre la creación de un caso y la decisión del analista. El objetivo del piloto es reducirlo frente a la revisión manual. | tiempo de atención, tiempo de respuesta | Dirección de Cuentas por Pagar | métrica tiempo_promedio_revision |
| **Unicidad** | Dimensión de calidad que mide qué porcentaje de registros no está duplicado según su llave de negocio. | no duplicidad | Oficina de Gobierno de Datos | P-022 |
| **Validez** | Dimensión de calidad que mide qué porcentaje de valores cumple el formato o el rango permitido. | conformidad, exactitud de formato | Oficina de Gobierno de Datos | P-022 |
