```sql
SELECT AVG(horas_revision) AS tiempo_promedio_revision
FROM v_facturas
WHERE revisada_en IS NOT NULL
LIMIT 100;
```

