# Integración local del chat sin MSW

Rama de integración de S3-34, sobre S3-33 y la pantalla del PR #20. El PR #13 no está incorporado.

VITE_CHAT_REAL=true desactiva MSW y hace que la pantalla cree una conversación en el backend antes de enviar el primer mensaje. Reutiliza el identificador en los turnos siguientes de la misma pantalla y caso. VITE_API_URL determina el origen del backend.

El historial se guarda en PostgreSQL. Todavía no hay selector de conversaciones ni recuperación de una conversación al recargar la pantalla. Las respuestas siguen siendo de demostración: conectar con el backend no convierte el grafo en un agente real.

La configuración docker-compose.chat-local.yml selecciona dsa-backend:s333 para la prueba local, junto al compose principal. Ejecutar con el archivo .env del repositorio local y un contenedor separado en el puerto 8022. La pantalla de prueba usa 127.0.0.1:5189 y el backend debe permitir ese origen en CORS_ORIGINS. No subir archivos .env.

Validación realizada: siete pruebas con MSW, dos pruebas de navegador sin MSW contra FastAPI y PostgreSQL locales, y compilación. Las dos pruebas sin MSW verifican el chat global y el contextual F-1042, dos turnos en la misma conversación, pasos y mensajes persistidos. Crean conversaciones de prueba en la base local; no modifican las facturas.

Las pruebas reales se ejecutan con npx playwright test --config playwright.real.config.js, con el backend ya iniciado. Las pruebas simuladas usan npm run test:e2e y fuerzan VITE_CHAT_REAL=false.

Pendiente para cerrar S3-34: coordinar el frontend compartido, desplegar y verificar en dev. Pendientes independientes: grafo con herramientas reales, autenticación de despliegue, persistencia de fallos y cancelaciones y control de turnos concurrentes. Estas pruebas no cierran S3-35 ni S3-36.
