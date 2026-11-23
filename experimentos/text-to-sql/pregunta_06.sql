```sql
SELECT h.regla, COUNT(h.id_hallazgo) AS hallazgos
FROM v_hallazgos h
GROUP BY h.regla
ORDER BY hallazgos DESC
LIMIT 5;
```

