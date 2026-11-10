# Vistas consultables y catálogo de datos

_Generado con `datos/scripts/generar_docs.py`. No lo edites a mano._

Fuente: [`datos/gobernanza/catalogo_datos.yaml`](../../datos/gobernanza/catalogo_datos.yaml). Las vistas se crean en la migración `0002`.

## Seguridad por fila

Cada transacción fija el contexto con `SET LOCAL` (`steward_datos.contexto.fijar_en_bd`):

```sql
SELECT set_config('app.rol', 'analista', true), set_config('app.usuario', '<sub de Cognito>', true);
```

- `administrador` ve todas las entidades; `analista` solo las de `usuarios_entidades`; sin contexto o con otro rol, ninguna fila.
- `v_clientes` enmascara RFC y correo para quien no es administrador.
- El usuario `steward_consultas` (lo crea Infraestructura) solo tiene `SELECT` sobre las vistas y `statement_timeout` de 5 s.

## Dueños por dominio (P-021)

| Dominio | Data owner | Data steward |
|---|---|---|
| facturas | Dirección de Cuentas por Pagar | Gobierno de Datos · Cuentas por Pagar |
| proveedores | Dirección de Compras | Datos Maestros de Compras |
| pagos | Tesorería | Gobierno de Datos · Tesorería |
| presupuesto | Dirección de Finanzas | Control Presupuestal |
| clientes | Dirección de Banca Comercial | Gobierno de Datos · Clientes |
| auditoria | Contraloría Interna | Oficina de Gobierno de Datos |
| gobernanza | Oficina de Gobierno de Datos | Oficina de Gobierno de Datos |

## `v_facturas` · Facturas de proveedores

Una fila por factura recibida, con su resultado de revisión, su orden de compra, si ya se pagó y si está conciliada.

Dominio facturas · data owner: Dirección de Cuentas por Pagar · sensibilidad: **interno** · origen: Vista sobre facturas, casos, proveedores, órdenes de compra y pagos. Los datos de la factura los extrae el modelo de visión y los revisa un analista.

| Columna | Tipo | Descripción | Sensibilidad |
|---|---|---|---|
| `caso_id` | texto | Identificador del caso de revisión (F-0001) | interno |
| `folio` | texto | Folio impreso en la factura; vacío si no aparece | interno |
| `fecha_emision` | fecha | Fecha de emisión impresa en la factura | interno |
| `mes` | fecha | Primer día del mes de emisión; sirve para agrupar por mes | interno |
| `proveedor_rfc` | texto | RFC del proveedor que emite la factura (persona moral) | interno |
| `proveedor` | texto | Razón social del proveedor según el padrón | interno |
| `entidad_rfc` | texto | RFC de la entidad del grupo que recibe la factura | interno |
| `entidad` | texto | Razón social de la entidad receptora | interno |
| `centro_costo_id` | texto | Centro de costo de la orden de compra | interno |
| `centro_costo` | texto | Nombre del centro de costo | interno |
| `orden_compra_id` | texto | Orden de compra asociada; vacía si la factura no tiene | interno |
| `moneda` | texto | Moneda de la factura (MXN o USD) | publico |
| `subtotal` | numero | Subtotal impreso | interno |
| `impuestos` | numero | IVA trasladado impreso | interno |
| `retenciones` | numero | Retenciones impresas; vacío si no hay | interno |
| `total` | numero | Total impreso | interno |
| `total_mxn` | numero | Total en pesos; USD convertido al tipo de cambio fijo del piloto (18.50) | interno |
| `estado` | texto | Estado del caso (procesando | interno |
| `resultado` | texto | Resultado vigente; la decisión del analista si existe y si no la sugerencia del agente | interno |
| `resultado_sugerido` | texto | Resultado que sugirió el agente | interno |
| `resultado_final` | texto | Decisión del analista; vacía mientras no revisa | interno |
| `origen` | texto | aplicacion (subida por un analista), semilla (demo) o negocio (historia sintética) | interno |
| `recibida_en` | fecha y hora | Cuándo se creó el caso | interno |
| `revisada_en` | fecha y hora | Cuándo el analista confirmó la decisión | interno |
| `horas_revision` | numero | Horas entre la recepción y la decisión del analista | interno |
| `pagada` | booleano | Verdadero si Tesorería ya registró un pago | interno |
| `conciliada` | booleano | Verdadero si está aceptada y su total coincide con la orden de compra y con el pago | interno |

## `v_proveedores` · Padrón de proveedores

Una fila por proveedor, con su categoría, plazo de pago y si está activo.

Dominio proveedores · data owner: Dirección de Compras · sensibilidad: **interno** · origen: Padrón de proveedores autorizados que mantiene Compras.

| Columna | Tipo | Descripción | Sensibilidad |
|---|---|---|---|
| `rfc` | texto | RFC del proveedor (persona moral) | interno |
| `razon_social` | texto | Razón social | interno |
| `categoria` | texto | Categoría de gasto del proveedor | interno |
| `activo` | booleano | Si está activo en el padrón | interno |
| `alta` | fecha | Fecha de alta en el padrón | interno |
| `plazo_pago_dias` | numero | Días de crédito acordados | interno |
| `correo_contacto` | texto | Correo de facturación del proveedor (dato de empresa | interno |

## `v_casos` · Casos de revisión

Una fila por caso (factura o validación de registros) con su estado, resultado y responsable.

Dominio facturas · data owner: Dirección de Cuentas por Pagar · sensibilidad: **interno** · origen: Casos creados al subir una factura o un archivo de registros.

| Columna | Tipo | Descripción | Sensibilidad |
|---|---|---|---|
| `caso_id` | texto | Identificador del caso (F-1042 | interno |
| `tipo` | texto | factura o validacion | interno |
| `estado` | texto | Estado del caso | interno |
| `resultado_sugerido` | texto | Resultado que sugirió el agente | interno |
| `resultado_final` | texto | Decisión del analista | interno |
| `resultado` | texto | Decisión del analista si existe; si no | interno |
| `responsable` | texto | Analista que subió el caso | interno |
| `revisado_por` | texto | Analista que confirmó la decisión | interno |
| `origen` | texto | aplicacion | interno |
| `entidad_rfc` | texto | Entidad receptora (solo facturas) | interno |
| `creado_en` | fecha y hora | Creación del caso | interno |
| `revisado_en` | fecha y hora | Decisión del analista | interno |
| `horas_revision` | numero | Horas entre creación y decisión | interno |

## `v_hallazgos` · Hallazgos de revisión

Una fila por hallazgo, con la regla y versión que lo generó.

Dominio facturas · data owner: Dirección de Cuentas por Pagar · sensibilidad: **interno** · origen: Hallazgos que registra el agente al aplicar el catálogo de reglas.

| Columna | Tipo | Descripción | Sensibilidad |
|---|---|---|---|
| `hallazgo_id` | numero | Identificador del hallazgo | interno |
| `caso_id` | texto | Caso al que pertenece | interno |
| `regla_id` | texto | Regla del catálogo | interno |
| `regla_version` | texto | Versión de la regla | interno |
| `regla` | texto | Nombre de la regla | interno |
| `politica_id` | texto | Política que sustenta la regla | interno |
| `efecto` | texto | rechazo | interno |
| `severidad` | texto | error | interno |
| `titulo` | texto | Título del hallazgo | interno |
| `origen` | texto | codigo | interno |
| `creado_en` | fecha y hora | Cuándo se registró | interno |

## `v_ordenes_compra` · Órdenes de compra

Una fila por orden de compra, con su proveedor, centro de costo y monto.

Dominio proveedores · data owner: Dirección de Compras · sensibilidad: **interno** · origen: Sistema de compras (sintético en el piloto).

| Columna | Tipo | Descripción | Sensibilidad |
|---|---|---|---|
| `orden_compra_id` | texto | Identificador de la orden | interno |
| `proveedor_rfc` | texto | RFC del proveedor | interno |
| `proveedor` | texto | Razón social del proveedor | interno |
| `entidad_rfc` | texto | Entidad que compra | interno |
| `centro_costo_id` | texto | Centro de costo | interno |
| `centro_costo` | texto | Nombre del centro de costo | interno |
| `fecha` | fecha | Fecha de la orden | interno |
| `mes` | fecha | Primer día del mes de la orden | interno |
| `descripcion` | texto | Qué se compró | interno |
| `moneda` | texto | MXN o USD | publico |
| `monto` | numero | Monto con impuestos en la moneda de la orden | interno |
| `estado` | texto | abierta | interno |

## `v_pagos` · Pagos a proveedores

Una fila por pago programado o realizado de una factura aceptada.

Dominio pagos · data owner: Tesorería · sensibilidad: **confidencial** · origen: Registro de Tesorería. El sistema solo los lee; ninguna tool crea ni libera pagos.

| Columna | Tipo | Descripción | Sensibilidad |
|---|---|---|---|
| `pago_id` | numero | Identificador del pago | interno |
| `caso_id` | texto | Caso de la factura pagada | interno |
| `folio` | texto | Folio de la factura | interno |
| `proveedor_rfc` | texto | RFC del proveedor | interno |
| `proveedor` | texto | Razón social del proveedor | interno |
| `entidad_rfc` | texto | Entidad que paga | interno |
| `fecha_programada` | fecha | Fecha de vencimiento según el plazo del proveedor | interno |
| `fecha_pago` | fecha | Fecha en que se pagó; vacía si sigue programado | confidencial |
| `dias_atraso` | numero | Días entre la fecha programada y el pago (0 si fue a tiempo) | interno |
| `moneda` | texto | MXN o USD | publico |
| `monto` | numero | Monto pagado o por pagar | confidencial |
| `estado` | texto | programado | interno |

## `v_centros_costo` · Centros de costo

Una fila por centro de costo, con su presupuesto y lo comprometido en órdenes de compra.

Dominio presupuesto · data owner: Dirección de Finanzas · sensibilidad: **interno** · origen: Catálogo de Finanzas con el presupuesto anual del piloto.

| Columna | Tipo | Descripción | Sensibilidad |
|---|---|---|---|
| `centro_costo_id` | texto | Identificador | interno |
| `nombre` | texto | Nombre del centro de costo | interno |
| `area` | texto | Dirección a la que pertenece | interno |
| `entidad_rfc` | texto | Entidad del grupo | interno |
| `responsable` | texto | Responsable del presupuesto | interno |
| `presupuesto_anual` | numero | Presupuesto anual en MXN | confidencial |
| `comprometido_mxn` | numero | Suma de órdenes de compra no canceladas | interno |

## `v_clientes` · Clientes

Una fila por cliente. El RFC y el correo se enmascaran para quien no es administrador.

Dominio clientes · data owner: Dirección de Banca Comercial · sensibilidad: **confidencial** · origen: Clientes ya dados de alta (las altas nuevas se validan en la Historia 2 antes de entrar aquí).

| Columna | Tipo | Descripción | Sensibilidad |
|---|---|---|---|
| `id_cliente` | texto | Identificador interno del cliente | interno |
| `nombre` | texto | Nombre o razón social | confidencial |
| `tipo_persona` | texto | fisica o moral | interno |
| `rfc` | texto | RFC del cliente; dato personal en personas físicas | confidencial (enmascarada) |
| `correo_contacto` | texto | Correo de contacto | confidencial (enmascarada) |
| `segmento` | texto | Segmento comercial | interno |
| `entidad_rfc` | texto | Entidad del grupo que lo atiende | interno |
| `alta` | fecha | Fecha de alta | interno |
| `mes_alta` | fecha | Primer día del mes de alta | interno |
| `activo` | booleano | Si el cliente sigue activo | interno |

## Tablas internas (no consultables)

| Tabla | Nombre | Dominio | Sensibilidad |
|---|---|---|---|
| `casos` | Casos | facturas | interno |
| `documentos` | Documentos originales | facturas | confidencial |
| `facturas` | Datos de factura | facturas | interno |
| `conceptos_factura` | Conceptos de factura | facturas | interno |
| `campos_extraidos` | Campos extraídos | facturas | interno |
| `hallazgos` | Hallazgos | facturas | interno |
| `bitacora` | Bitácora de auditoría | auditoria | restringido |
| `proveedores` | Padrón de proveedores | proveedores | interno |
| `entidades_receptoras` | Entidades del grupo | proveedores | publico |
| `centros_costo` | Centros de costo | presupuesto | confidencial |
| `ordenes_compra` | Órdenes de compra | proveedores | interno |
| `pagos` | Pagos | pagos | confidencial |
| `clientes` | Clientes | clientes | confidencial |
| `usuarios_entidades` | Permisos por entidad | gobernanza | restringido |
| `politicas` | Políticas | gobernanza | interno |
| `politica_fragmentos` | Fragmentos del RAG | gobernanza | interno |
| `reglas` | Catálogo de reglas | gobernanza | interno |
| `catalogo_tablas` | Catálogo de datos (tablas) | gobernanza | interno |
| `catalogo_columnas` | Catálogo de datos (columnas) | gobernanza | interno |
| `glosario_terminos` | Glosario de negocio | gobernanza | publico |
| `reglas_calidad` | Reglas de calidad | gobernanza | interno |
| `resultados_calidad` | Resultados de calidad | gobernanza | interno |
| `metricas` | Métricas de la capa semántica | gobernanza | interno |
| `consultas_libres` | Consultas libres | auditoria | restringido |
| `conversaciones` | Conversaciones del chat | auditoria | confidencial |
| `mensajes` | Mensajes del chat | auditoria | confidencial |
