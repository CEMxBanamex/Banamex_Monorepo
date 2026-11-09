# Preguntas para el socio formador (frente de Datos)

Borrador para la siguiente revisión. Cada pregunta dice qué supuesto usamos mientras tanto, para que la respuesta pueda ser "sí, así está bien".

## Datos de negocio que se consultan desde el chat
1. ¿Qué información de negocio esperan consultar en el chat? Supusimos el ciclo de cuentas por pagar: proveedores, órdenes de compra, facturas, pagos y centros de costo, más clientes para la validación de registros.
2. ¿Qué preguntas típicas haría un analista? Nos sirven para definir métricas. Hoy hay 12, como monto facturado, tasa de rechazo, tiempo promedio de revisión, pagos a tiempo y tasa de conciliación.
3. ¿Hay otros dominios que quieran ver (por ejemplo, contratos o tesorería) o con estos basta para el piloto?

## Reglas de facturas (Historia 1)
4. ¿Qué reglas de revisión de facturas aplican de verdad? Tenemos 14 sintéticas, como total = subtotal + impuestos con tolerancia de 0.05, tasas de IVA de 0 %, 8 % y 16 %, RFC válido, antigüedad máxima de 365 días, duplicados, proveedor en padrón y monto alto que exige revisión.
5. ¿A partir de qué monto una factura requiere una revisión adicional? Supusimos 250,000 MXN.
6. Si el sistema no está seguro de un dato leído, ¿prefieren que el caso siempre vaya a revisión humana, aunque sean más casos? Hoy, con confianza menor a 80 %, va a revisión.

## Políticas y validación de registros (Historia 2)
7. ¿Qué documentos o registros quieren validar contra políticas? Supusimos archivos de clientes (Excel o CSV) con campos obligatorios, RFC, correo, fecha de alta y unicidad.
8. ¿Pueden compartir políticas autorizadas (aunque sea una versión pública o editada) para cargarlas al RAG en lugar de las sintéticas?

## Gobernanza
9. ¿Cómo nombran ellos los roles de gobierno de datos (data owner, data steward u otros) y los niveles de clasificación (público, interno, confidencial, restringido)?
10. ¿Qué preguntas de gobernanza les gustaría que el chat respondiera en la demo?
