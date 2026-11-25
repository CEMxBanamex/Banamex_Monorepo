```sql
SELECT 
    v_proveedores.id_proveedor,
    v_proveedores.nombre_proveedor,
    SUM(v_facturas.monto_factura) AS monto_total_facturado
FROM 
    v_facturas
JOIN 
    v_proveedores ON v_facturas.id_proveedor = v_proveedores.id_proveedor
GROUP BY 
    v_proveedores.id_proveedor, v_proveedores.nombre_proveedor
ORDER BY 
    monto_total_facturado DESC
LIMIT 100;
```

