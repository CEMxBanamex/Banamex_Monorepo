```sql
SELECT c.responsable, COUNT(c.id) AS casos_pendientes
FROM v_casos c
WHERE c.estado = 'pendiente'
GROUP BY c.responsable
ORDER BY c.responsable
LIMIT 100;
```

