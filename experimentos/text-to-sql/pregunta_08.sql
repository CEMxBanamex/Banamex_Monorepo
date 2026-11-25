```sql
SELECT v_proveedores.nombre AS nombre_proveedor, SUM(v_pagos.monto) AS monto_total_pagos
FROM v_pagos
JOIN v_proveedores ON v_pagos.id_proveedor = v_proveedores.id_proveedor
GROUP BY v_proveedores.nombre
ORDER BY monto_total_pagos DESC
LIMIT 100;
```

