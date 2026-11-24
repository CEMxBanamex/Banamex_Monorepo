```sql
SELECT regla, COUNT(DISTINCT caso_id) AS num_hallazgos
FROM v_hallazgos
GROUP BY regla
ORDER BY num_hallazgos DESC
LIMIT 5;
```

