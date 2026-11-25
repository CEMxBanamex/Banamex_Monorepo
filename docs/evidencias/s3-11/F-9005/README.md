# Prueba local S3-11: F-9005

Ejecutada por Carlos Delgado el 23 de noviembre de 2026 en Windows, con el código
`c9a4176b2407acda3cb0233bd3ac2024c55c200d`, Ollama `gemma3:4b` y PostgreSQL local de Compose.

## Evidencia observada

- `pausa.json`: extracción de la imagen sintética, 13 reglas evaluadas, hallazgos R-002/R-003,
  fragmentos de políticas recuperados y pausa antes de una decisión humana.
- `final.json`: mismo resultado sugerido y evidencia, más la decisión humana y su motivo.
- Consulta de PostgreSQL ejecutada por Carlos y comprobada en captura:

```sql
SELECT id, estado, resultado_final, revisado_por
FROM casos WHERE id = 'F-9005';
```

| id | estado | resultado_final | revisado_por |
| --- | --- | --- | --- |
| F-9005 | revisado | rechazado | dev-ana |

El archivo `final.json` se escribe después de reanudar el grafo y guardar el cierre.
Los dos JSON provienen de la ejecución del usuario; solo se sustituyó `archivo`, que
contenía su ruta personal absoluta, por la ruta relativa del mismo documento del repo.
El SHA-256 se verificó contra la imagen incluida en el repositorio.

## Límite del resultado

Gemma leyó `GSS070101186W`; la imagen muestra `GSS07010186W`. R-002 detectó el RFC
extraído inválido. El analista rechazó este intento por extracción incorrecta y dejó
explícito que eso no demuestra que la factura original sea inválida. No se modificó
el RFC automáticamente ni se afirma precisión de extracción a partir de esta prueba.

La recuperación se realizó con embeddings de prueba `falso-hash`, no con un índice
semántico de embeddinggemma. Esta evidencia comprueba el recorrido local con herramientas
y persistencia reales; no acredita calidad del RAG ni ejecución en dev.

## Pendientes

- Revisión e integración del cambio en dev y repetición del recorrido con el equipo.
- Evaluación por lote de precisión de extracción y clasificación en S3-13.
- Mantener los límites del piloto descritos en `backend/grafo_casos/REAL.md`: CLI local,
  estado del grafo en memoria, original sin alta en S3 y sin conexión a las rutas de la API.
