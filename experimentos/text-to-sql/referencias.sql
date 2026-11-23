-- S1-31: Consultas SQL de referencia
-- Modelo evaluado: qwen2.5-coder:7b
-- Basadas en datos/semantica/metricas.yaml

-- 01. Cantidad de facturas por resultado
SELECT
    resultado,
    COUNT(*) AS cantidad_facturas
FROM v_facturas
GROUP BY resultado
ORDER BY cantidad_facturas DESC
LIMIT 100;

-- 02. Monto total facturado por proveedor
SELECT
    proveedor,
    SUM(total_mxn) AS monto_total_facturado_mxn
FROM v_facturas
WHERE resultado IS DISTINCT FROM 'rechazado'
GROUP BY proveedor
ORDER BY monto_total_facturado_mxn DESC
LIMIT 100;

-- 03. Cantidad de facturas rechazadas
SELECT
    COUNT(*) AS facturas_rechazadas
FROM v_facturas
WHERE resultado = 'rechazado'
LIMIT 100;

-- 04. Tasa de conciliacion
SELECT
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE conciliada)
        / NULLIF(COUNT(*), 0),
        2
    ) AS tasa_conciliacion
FROM v_facturas
WHERE resultado = 'aceptado'
LIMIT 100;

-- 05. Tiempo promedio de revision
SELECT
    ROUND(AVG(horas_revision), 2) AS tiempo_promedio_revision
FROM v_facturas
WHERE revisada_en IS NOT NULL
LIMIT 100;

-- 06. Cinco reglas con mas facturas que presentan hallazgos
SELECT
    regla_id,
    regla,
    COUNT(DISTINCT caso_id) AS casos_con_hallazgo
FROM v_hallazgos
GROUP BY regla_id, regla
ORDER BY casos_con_hallazgo DESC
LIMIT 5;

-- 07. Casos pendientes por responsable
SELECT
    responsable,
    COUNT(*) AS casos_pendientes
FROM v_casos
WHERE estado IN ('procesando', 'revision')
GROUP BY responsable
ORDER BY casos_pendientes DESC
LIMIT 100;

-- 08. Monto pagado por proveedor
SELECT
    proveedor,
    SUM(
        monto * CASE
            WHEN moneda = 'USD' THEN 18.50
            ELSE 1
        END
    ) AS monto_pagado_mxn
FROM v_pagos
WHERE estado = 'pagado'
GROUP BY proveedor
ORDER BY monto_pagado_mxn DESC
LIMIT 100;

-- 09. Monto comprometido por centro de costo
SELECT
    centro_costo_id,
    nombre,
    comprometido_mxn
FROM v_centros_costo
ORDER BY comprometido_mxn DESC
LIMIT 100;

-- 10. Clientes activos por segmento
SELECT
    segmento,
    COUNT(*) AS clientes_activos
FROM v_clientes
WHERE activo
GROUP BY segmento
ORDER BY clientes_activos DESC
LIMIT 100;

