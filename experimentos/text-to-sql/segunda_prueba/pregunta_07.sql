```sql
SELECT responsable, COUNT(*) AS casos_pendientes
FROM v_casos
WHERE estado IN ('procesando', 'revision')
GROUP BY responsable
LIMIT 100;
```

