```sql
SELECT c.centro_costo_id, c.nombre, c.presupuesto_anual, c.comprometido_mxn, (c.comprometido_mxn / c.presupuesto_anual) * 100 AS porcentaje_comprometido
FROM v_centros_costo c
ORDER BY c.comprometido_mxn DESC
LIMIT 100;
```

