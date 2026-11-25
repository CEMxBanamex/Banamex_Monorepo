# API local: F-1100

Ejecución real del usuario el 24 de noviembre de 2026 (hora de México), sobre la
rama de integración local. La consola confirma VISION_MODELO=qwen3-vl:4b-instruct.
La API generó la subida, recibió piloto_012.png desde S3, procesó el caso y devolvió
su detalle y siete eventos de bitácora mediante peticiones posteriores.

- Estado: revision; sugerencia: humana; resultado final: null.
- Se recuperan cinco conceptos y el informe de evidencia que exige revisión humana
  y deshabilita la decisión automática.
- R-014 detecta total 185,884.64 frente a subtotal 159,900.55 + impuestos 25,584.09
  = 185,484.64: diferencia de 400.00, consistente con el escenario sintético.
- R-003 indica confianza desconocida; R-015 advierte antecedente local F-9502.
- La primera exportación con Invoke-RestMethod en PowerShell 5.1 presenta
  caracteres como `RevisiÃ³n`. La descarga HTTP directa del detalle cerrado,
  leída con UTF-8 explícito, devuelve correctamente `Bermúdez` y `revisión`.
  Se preservan las exportaciones iniciales sin corregir; la diferencia se
  localiza en la decodificación del cliente, no en la lectura visual.

El cierre explícito de prueba como dev-ana devuelve revisado/rechazado y evento
EV-5268. Las consultas posteriores de detalle y bitácora confirman el mismo
resultado y ocho eventos, incluido confirmacion con el motivo R-014 y diferencia
de 400.00. El código HTTP no se registró por separado; las respuestas están
exportadas en los JSON adjuntos. No se ejercitó el cierre tras reinicio.

Esta evidencia confirma creación, consulta, revisión, cierre explícito y auditoría
por API. No incluye navegador, despliegue compartido ni validación semántica del RAG.
Los filtros globales de bitácora forman parte de la respuesta original local.
