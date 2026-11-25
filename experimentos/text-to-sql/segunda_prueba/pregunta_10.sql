```sql
SELECT segmento, COUNT(*) AS cantidad_clientes
FROM v_clientes
WHERE activo = TRUE
GROUP BY segmento
LIMIT 100;
```

