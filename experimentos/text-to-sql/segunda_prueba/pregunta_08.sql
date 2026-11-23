```sql
SELECT proveedor, SUM(monto) AS total_pagos
FROM v_pagos
WHERE estado = 'pagado'
GROUP BY proveedor
LIMIT 100;
```

