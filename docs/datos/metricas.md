# Capa semántica: métricas oficiales

_Generado con `datos/scripts/generar_docs.py`. No lo edites a mano._

Fuente: [`datos/semantica/metricas.yaml`](../../datos/semantica/metricas.yaml) · versión 1.0 · dueño: Oficina de Gobierno de Datos.

`obtener_metrica` arma el SQL con estas piezas; el modelo solo elige métrica, dimensiones (hasta 2), filtros y fechas.

| Métrica | Definición | Unidad | Vista | Dimensiones | Filtros |
|---|---|---|---|---|---|
| `monto_facturado` | Suma del total de las facturas no rechazadas, en pesos (USD al tipo de cambio fijo de 18.50). | MXN | `v_facturas` | proveedor, mes, entidad, centro_costo, moneda, resultado | proveedor, entidad, centro_costo, moneda, resultado |
| `numero_facturas` | Cantidad de facturas recibidas, sin importar su resultado. | facturas | `v_facturas` | proveedor, mes, entidad, centro_costo, moneda, resultado | proveedor, entidad, centro_costo, moneda, resultado |
| `facturas_rechazadas` | Cantidad de facturas cuyo resultado vigente es Rechazado (decisión del analista o, si no hay, sugerencia del agente). | facturas | `v_facturas` | proveedor, mes, entidad, centro_costo, moneda, resultado | proveedor, entidad, centro_costo, moneda, resultado |
| `tasa_rechazo` | Porcentaje de facturas con resultado Rechazado sobre el total de facturas. | % | `v_facturas` | proveedor, mes, entidad, centro_costo, moneda, resultado | proveedor, entidad, centro_costo, moneda, resultado |
| `tasa_conciliacion` | Porcentaje de facturas aceptadas que están conciliadas (total igual a la orden de compra y al pago). | % | `v_facturas` | proveedor, mes, entidad, centro_costo, moneda, resultado | proveedor, entidad, centro_costo, moneda, resultado |
| `tiempo_promedio_revision` | Promedio de horas entre la recepción de una factura y la decisión del analista. | horas | `v_facturas` | proveedor, mes, entidad, centro_costo, moneda, resultado | proveedor, entidad, centro_costo, moneda, resultado |
| `facturas_por_regla` | Cantidad de casos distintos con al menos un hallazgo de cada regla del catálogo. | facturas | `v_hallazgos` | regla, efecto, mes | regla, efecto |
| `casos_pendientes` | Casos que siguen procesándose o esperan la decisión de un analista. | casos | `v_casos` | tipo, responsable, estado | tipo, responsable |
| `monto_pagado` | Suma de los pagos realizados por Tesorería, en pesos (USD a 18.50). | MXN | `v_pagos` | proveedor, mes, entidad | proveedor, entidad |
| `pagos_a_tiempo` | Porcentaje de pagos realizados a más tardar en su fecha programada. | % | `v_pagos` | proveedor, mes, entidad | proveedor, entidad |
| `monto_comprometido` | Suma de órdenes de compra no canceladas, en pesos (USD a 18.50). | MXN | `v_ordenes_compra` | proveedor, centro_costo, mes, entidad | proveedor, centro_costo, entidad |
| `clientes_activos` | Cantidad de clientes dados de alta que siguen activos. | clientes | `v_clientes` | segmento, entidad, tipo_persona, mes_alta | segmento, entidad, tipo_persona |
