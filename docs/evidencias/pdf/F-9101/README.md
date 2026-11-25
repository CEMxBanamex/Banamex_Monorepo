# Prueba PDF local F-9101

Fecha: 24 de noviembre de 2026. Código probado: `496a905` (rama
`agentes/pdf-facturas-carlos-delgado`). Windows, `pypdfium2==5.15.2`,
Ollama `gemma3:4b`, PostgreSQL local; configuración solicitada con embeddings
`falso`. No se adjuntó un manifiesto con versiones del resto del entorno.

## Recorrido observado

El usuario ejecutó el piloto con `piloto_002.pdf`, caso F-9101 y analista
`dev-ana`. El flujo real completó extracción, validación, búsqueda de políticas
y llegó a la pausa de revisión humana. La salida conserva `paginas: 2` y el
SHA-256 del PDF original:
`89c8623f3c372e56cd4e0b5cef5d9028f2c0e7b12bca1dc2057950fec9613c73`.
Se verificó ese hash contra el archivo del repositorio.

[pausa.json](pausa.json) contiene la salida proporcionada por el usuario;
solo se sustituyó la ruta absoluta personal por la ruta relativa del documento.
No contiene una decisión humana final. Se indicó escribir `salir`; no se aporta
una consulta PostgreSQL ni una confirmación posterior del estado persistido.
Esta evidencia no prueba cierre ni ejecución en dev.

## Resultado y límites

- La conversión PDF funciona en Windows y la extracción real llega a revisión;
  eso no acredita lectura correcta de los campos ni aceptación de la factura.
- Gemma devolvió `RFC` como valor de ambos identificadores, omitió folio, fecha,
  receptor e impuestos y alteró nombres, dirección y conceptos.
- Las reglas recomendaron rechazo por R-001, R-002 y R-010. Esa recomendación
  evalúa la extracción defectuosa: no demuestra incumplimiento del PDF original.
- Solo R-002 y R-003 tienen fragmentos recuperados; R-001 y R-010 muestran
  una cita de catálogo sin fragmento. No se acredita calidad semántica del RAG.
- Los campos tienen `pagina: null` porque la imagen compuesta reúne dos páginas.
  El motor de reglas todavía imprime «página 1» en los hallazgos: esa localización
  no está verificada para este PDF multipágina y no debe tomarse como evidencia
  precisa de ubicación. La confianza y bbox también quedan en null.

Las pruebas en Windows terminaron con 27 aprobadas y una prueba opcional de BD
omitida. Incluyen rasterización de los 20 PDF del corpus, preservación de la
segunda página y del original, y rechazo de documentos inválidos, cifrados o
fuera de límites. Las respuestas HTTP de esas pruebas son controladas; esta
prueba F-9101 sí utilizó el modelo real, con los errores aquí conservados.

Pendiente: probar las facturas de la demo y sus respaldos en dev, revisar la
precisión del extractor y la ubicación de evidencia en documentos multipágina.
