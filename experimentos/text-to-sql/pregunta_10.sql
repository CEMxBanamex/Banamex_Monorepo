```sql
SELECT 
    v_clientes.segmento, 
    COUNT(v_clientes.id_cliente) AS cantidad_clientes_activos
FROM 
    v_clientes
JOIN 
    v_facturas ON v_clientes.id_cliente = v_facturas.id_cliente
WHERE 
    v_facturas.estado = 'activa'
GROUP BY 
    v_clientes.segmento
LIMIT 100;
```

