```sql
SELECT AVG(EXTRACT(EPOCH FROM (factura.fechahora_recepcion - factura.fechahora_creacion))) / 3600 AS promedio_horas
FROM v_facturas factura;
```

