SELECT 
    (COUNT(DISTINCT f.id_factura) FILTER (WHERE p.pagado = 'S'))::FLOAT / COUNT(DISTINCT f.id_factura) * 100 AS tasa_conciliacion
FROM 
    v_facturas f
LEFT JOIN 
    v_pagos p ON f.id_factura = p.id_factura
LIMIT 100

