# Comprobación local de S3-38

Ejecución del parser XML y motor de reglas reales en el entorno de desarrollo
(24 de noviembre de 2026, fecha de México). Los tres documentos son sintéticos
sin validez fiscal; sus SHA-256 están en cada salida.

| XML | Sugerencia del motor | Hallazgo esperado |
| --- | --- | --- |
| cfdi_correcto.xml | aceptado | ninguno |
| cfdi_total_incorrecto.xml | rechazado | R-014 |
| cfdi_rfc_faltante.xml | rechazado | R-001 |

Son sugerencias de las reglas, no decisiones automáticas ni casos ya registrados.
La API y el piloto mantienen pausa humana. Ninguna extracción llama a Ollama;
se comprobó con un cliente interceptado que no recibió llamadas. El contexto del
motor es sintético, sin padrón, historial, S3, embeddings o base PostgreSQL.

La suite incluye pruebas HTTP con S3/sesiones controlados y parser/grafo reales,
serialización del UUID y lectura de detalle. No se ha ejecutado el recorrido XML
contra la infraestructura real de la laptop ni en navegador. Esas pruebas no se
confunden con el recorrido previo de imagen F-1100.

Suite completa: 393 aprobadas, 80 omitidas, 97 subpruebas aprobadas (pruebas.txt).
Ruff y compilación Vite aprobados. Detalles de campos, alcance y referencias en
../../../XML_CFDI_LOCAL.md (desde docs, docs/XML_CFDI_LOCAL.md).
