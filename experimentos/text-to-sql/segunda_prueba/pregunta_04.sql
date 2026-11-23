```sql
SELECT 
    (SUM(CASE WHEN conciliada = TRUE THEN 1 ELSE 0 END) / COUNT(*)) * 100 AS tasa_conciliacion
FROM 
    v_facturas
WHERE 
    resultado = 'aceptado'
LIMIT 100;
```

