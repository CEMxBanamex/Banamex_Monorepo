\# Integración inicial del grafo de chat: S3-33



POST /api/chat/stream utiliza FlujoChat.stream\_chat del trabajo S1-33.



\## Incluido



\- Eventos paso y respuesta conforme a contratos.eventos\_sse.

\- Usuario de desarrollo configurado en el servidor.

\- Rol analista fijo durante esta integración de desarrollo.

\- Rechazo de usuario\_id y rol enviados en el cuerpo.

\- Fallos del flujo representados como pasos de error.

\- Pruebas del contrato, identidad, errores y registro único de la ruta.



\## Configuración



AUTH\_MODE=dev habilita esta integración.

CHAT\_DEV\_USUARIO permite indicar el usuario de desarrollo.

Si no se especifica, se utiliza dev-ana.



Fuera de AUTH\_MODE=dev, el endpoint devuelve 503 hasta que se

integre la dependencia de autenticación real.



\## Pendientes



El grafo de S1-33 todavía usa herramientas simuladas y devuelve

simulado=true. No acredita consultas reales de casos ni políticas.



No se guardan mensajes ni pasos. El historial y la lista de

conversaciones existentes siguen siendo ejemplos fijos.



Faltan la persistencia de S3-33, las herramientas reales de S3-15,

la integración con la pantalla de S3-34 y las pruebas reales de

gobernanza y casos de S3-36.



La ruta /api/chat/consulta conserva su respuesta fija anterior.

