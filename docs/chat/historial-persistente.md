# Historial persistente: integración de desarrollo

- POST /api/chat/conversaciones crea una conversación del usuario configurado en el servidor.
- GET /api/chat/conversaciones lista sus conversaciones, con limite y desplazamiento.
- GET /api/chat/conversaciones/{id}/mensajes devuelve mensajes ordenados por ID, pasos, citas y duración. Acepta limite y despues_de.
- POST /api/chat/stream admite conversacion_id. Con ese identificador recupera los últimos 50 mensajes y guarda el turno completado antes de emitir la respuesta final. Sin identificador conserva el modo de demostración sin almacenamiento.

Se reutilizan las tablas conversaciones y mensajes. El título se proporciona al crear la conversación. El usuario no puede escoger su identidad o rol en el cuerpo de la solicitud. La autenticación continúa siendo exclusivamente de desarrollo, mediante AUTH_MODE=dev y CHAT_DEV_USUARIO.

Las rutas de historial ficticio se sustituyeron por consultas a PostgreSQL. Las respuestas del grafo siguen siendo simuladas; persistirlas no las convierte en datos reales.

Cada turno completado guarda pregunta, respuesta, eventos de pasos, fuentes como objetos {fuente}, y duración. El esquema actual no conserva tipo y simulado como columnas del mensaje. No se debe inferir que una respuesta histórica sea real por la ausencia de esos campos.

Los errores del grafo o de escritura no emiten una respuesta exitosa. Esta entrega todavía no persiste turnos fallidos, interrumpidos o cancelados; tampoco evita dos generaciones simultáneas sobre la misma conversación. Esos puntos y la autenticación real siguen pendientes antes de cerrar S3-33.

Las consultas de conversaciones ligadas a casos verifican v_casos y fallan de forma cerrada si no existe acceso. Las pruebas de integración de esta entrega cubren conversaciones generales en una base desechable; falta validar casos y el rol SQL del despliegue con las migraciones y permisos reales.

Validación: pruebas de backend incluidas las de PostgreSQL, y Ruff 0.14.0. El workflow Historial del chat ejecuta las pruebas de integración con CHAT_DATABASE_URL_PRUEBAS; las pruebas generales las omiten si esa variable no está definida.
