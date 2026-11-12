# Grafo de casos simulado (S1-28)

`FlujoCasos.procesar_caso(caso_id)` ejecuta extractor, validador y redactor
con herramientas simuladas. El ejemplo lee un subtotal de 100.00 MXN, impuestos
de 16.00 MXN y un total de 120.00 MXN. El validador calcula 116.00 MXN y sugiere
revisión humana; el redactor explica la diferencia de 4.00 MXN.

El nodo de revisión usa `interrupt()`: al volver de `procesar_caso`, hay una
explicación y una recomendación, pero no existe todavía `decision_analista`.
Con la misma instancia de `FlujoCasos`, `reanudar_caso(caso_id, decision)`
recibe el resultado del analista (`aceptado` o `rechazado`) y su motivo.
La decisión queda registrada por separado de la recomendación.

El estado vive en memoria: se pierde al cerrar el proceso. Esta versión local
no usa MCP, Ollama, Postgres ni facturas reales. El llamador de la demo simula
al analista; la identidad, los permisos y la persistencia quedan para la
integración. La comparación aritmética es una regla de demostración, no la
validación completa del proyecto.

## Ejecutar las pruebas en Windows

Desde la raíz del monorepo, con el entorno virtual ya creado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\agentes\grafo_casos\requirements.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s agentes/grafo_casos/tests -v
```

Resultado esperado: `Ran 3 tests` y `OK`. Se comprueba la pausa sin decisión,
la reanudación con una decisión válida y el aislamiento por identificador.
