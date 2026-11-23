```sql
SELECT c.nombre, SUM(f.monto_comprometido) AS monto_total
FROM v_centros_costo c
JOIN v_facturas f ON c.id = f.centro_costo_id
GROUP BY c.id, c.nombre
ORDER BY monto_total DESC
LIMIT 100;
```

