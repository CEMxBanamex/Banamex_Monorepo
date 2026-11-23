```sql
SELECT v_proveedores.razon_social, SUM(v_facturas.total_mxn) AS monto_total_facturado
FROM v_facturas
JOIN v_proveedores ON v_facturas.proveedor_rfc = v_proveedores.rfc
GROUP BY v_proveedores.razon_social
ORDER BY monto_total_facturado DESC
LIMIT 100;
```

