# S1-40: consultar_caso y buscar_facturas

Implementación de Mauricio con contratos existentes y consultas de solo lectura.

## Archivos

- datos/steward_datos/tools/consultas_chat_seguras.py: consultas autorizadas.
- mcp/steward_mcp/tools/consultar_caso.py y buscar_facturas.py: registro MCP por herramienta.
- datos/tests/test_chat_seguro.py: integración con PostgreSQL y cliente MCP real.

## Permisos

El servidor fija el usuario; no se acepta rol ni usuario_id en los argumentos.
En desarrollo usa MCP_DEV_ROL y MCP_DEV_USUARIO, con dev-local por defecto (sin entidades).
Para probar manualmente datos de Ana, configurar MCP_DEV_USUARIO=dev-ana en el .env local y recrear mcp.
No es autenticación real: el servidor continúa restringido a AUTH_MODE=dev.

consultar_caso autoriza mediante v_casos y recupera los campos y evidencia con la función
existente de Mario, en la misma transacción de solo lectura. Las vistas actuales no incluyen
todo el detalle. Caso inexistente y caso prohibido devuelven CASO_NO_DISPONIBLE.

buscar_facturas consulta v_facturas y v_hallazgos; filtros parametrizados, orden por lista
cerrada y límite 1 a 100. El total cuenta solo filas visibles. Los caracteres % y _ en
búsquedas de texto se interpretan literalmente.

La referencia original consultas_chat.py y registrar_tools_datos permanecen sin cambios
por compatibilidad. El servidor de desarrollo registra las nuevas versiones seguras;
otros consumidores de la referencia antigua no adquieren estas garantías automáticamente.

## Pruebas

Desde la raíz del worktree S1-40:

docker compose -p dsa-s140 -f docker-compose.dev.yml run --rm pruebas

docker compose -p dsa-s140 -f docker-compose.dev.yml run --rm pruebas-mcp

La suite de datos utiliza la base desechable dsa_pruebas, no dsa_local.
Incluye acceso permitido/denegado, contexto obligatorio, aislamiento por entidad,
validación de filtros, conteo y orden, sesión de solo lectura y llamadas MCP con progreso.

## Ajuste de Windows

Se fija LF para las políticas y se normaliza P-015 sin cambiar su texto. Esto evita que
la carga inicial y la API calculen huellas diferentes por CRLF frente a LF.

## Limitaciones

No incluye JWT de producción, integración al grafo ni despliegue. Requiere revisión del
contrato con el equipo. Las pruebas de datos usan el usuario de pruebas de PostgreSQL;
las vistas aplican el contexto de aplicación. Verificar también los permisos del servicio
real antes de desplegar.
