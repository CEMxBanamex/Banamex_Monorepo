# Solicitudes de acceso: prototipo de demostración

Activar con VITE_ACCESO_DEMO=true al iniciar Vite. Desactivado por defecto: conserva el inicio de sesión existente. Para un build de demostración debe establecerse antes de compilar.

## Recorrido
1. Solicitar acceso con nombre, correo ficticio y área.
2. El registro queda pendiente y todavía no permite entrar.
3. Pulsar «Soy administrador», escribir cualquier correo válido e iniciar sesión para entrar a Data Steward. Abrir «Administrador» en el menú izquierdo. Puede hacerse en otra pestaña del mismo navegador y origen.
4. El contador de solicitudes pendientes se actualiza automáticamente.
5. Revisar y aprobar, o rechazar indicando un motivo.
6. La pestaña del solicitante recibe el nuevo estado; si fue aprobado, permite entrar a la interfaz de demostración.

Las solicitudes persisten en localStorage, clave dsa-accesos-demo-v1. No hay red, correo, notificaciones del sistema ni comunicación entre computadoras. Se puede reiniciar desde la vista de administrador con confirmación. No introducir datos personales reales.

## Alcance
Es una simulación visual. No verifica correos, contraseñas ni identidades y no administra permisos de API. El botón «Soy administrador» abre un formulario de correo obligatorio, sin contraseña, para iniciar una sesión visual de Administrador. Solo esa sesión muestra la sección Administrador en el menú de Data Steward. Las decisiones se atribuyen al correo ingresado por el administrador. La sesión de usuario muestra su nombre registrado, sus iniciales, rol propuesto y área; al salir se limpia esa identidad visual. Esto no cambia la identidad usada por la API. El rol Analista representa la propuesta de acceso; no se modifica una cuenta real.

## Integración posterior
Implementar registro y verificación de correo con el proveedor de identidad, guardar solicitudes en el servidor, restringir las decisiones al rol administrador validado por backend, registrar quién decide y cuándo, notificar por un canal real y comprobar el estado aprobado en cada autorización. No usar localStorage como fuente de permisos.

## Comprobaciones
npm.cmd run build
npx.cmd playwright test --config playwright.acceso.config.js
npx.cmd playwright test

El panel incluye búsqueda por nombre, correo y área, contadores por estado y responsable y fecha de cada decisión.
