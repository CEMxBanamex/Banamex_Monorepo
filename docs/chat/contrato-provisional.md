\# Contrato provisional del chat



Estado: borrador para revisión, no aprobado.

Responsable: Mauricio Guerrero.

Tarea relacionada: S1-39.



\## Alcance



Este avance propone dos endpoints con modelos de Pydantic y

respuestas ficticias. No consulta la base de datos, no ejecuta

herramientas, no utiliza modelos de IA y no implementa autenticación.



Las rutas y los valores exactos de los estados deben revisarse

con los responsables del chat antes de considerarlos definitivos.



\## Entrada compartida



\- mensaje: texto obligatorio, entre 1 y 2000 caracteres.

\- caso\_id: texto opcional, entre 1 y 100 caracteres, o null.

\- Se eliminan espacios al principio y al final de los textos.

\- No se aceptan campos adicionales.

\- Una entrada inválida devuelve HTTP 422.



El identificador del caso se devuelve como referencia;

este borrador no verifica su existencia ni los permisos de acceso.



\## POST /api/chat/consulta



Devuelve HTTP 200 con:



\- respuesta: texto fijo de demostración.

\- caso\_id: identificador recibido, o null.

\- simulado: true.



\## POST /api/chat/consulta/stream



Devuelve eventos con Content-Type: text/event-stream.



Secuencia del ejemplo:



1\. Evento paso, id demo-1, estado en\_curso.

2\. Evento paso, mismo id demo-1, estado completado.

3\. Evento respuesta con el contenido simulado.



Cada evento paso incluye id, texto, detalle y estado.

Los estados propuestos son pendiente, en\_curso, completado y error.

El ejemplo actual solo emite en\_curso y completado.



Los pasos están identificados como simulados y no representan

ejecuciones reales de herramientas.



\## Comprobación



Comando para ejecutar las pruebas:



docker compose -f docker-compose.dev.yml exec backend python -m unittest discover -s backend/tests -v



Las pruebas cubren consultas con y sin caso, entradas inválidas,

formato de eventos, orden y conservación del identificador del paso.



\## Pendientes



\- Confirmar el alcance de pantallas y endpoints con el equipo.

\- Revisar las rutas y modelos con Carlos Ramos y Juan Pablo.

\- Acordar el formato de errores durante una transmisión SSE.

\- Acordar identificadores de conversación y mensaje.

\- Acordar persistencia, historial y duración de los pasos.

\- Integrar las operaciones en la interfaz.

\- Implementar autenticación y permisos antes de usar datos protegidos.

\- Conectar herramientas y modelos reales en las tareas correspondientes.



Este avance no completa por sí solo S1-39 ni S1-41.

