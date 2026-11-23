```sql
SELECT COUNT(*) AS cantidad_facturas_rechazadas
FROM v_facturas
WHERE estado = 'Rechazada'
LIMIT 100;
```

