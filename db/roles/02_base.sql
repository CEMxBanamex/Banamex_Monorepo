-- Preparación de una base (dsa_local, dsa_dev o dsa_prod) antes de la primera migración.
--
-- Ejecutar como superusuario (local) o como usuario maestro (RDS), conectado a la base:
--   psql -v ON_ERROR_STOP=1 -d dsa_dev -f db/roles/02_base.sql
--
-- Idempotente. Requiere 01_roles.sql.

\set ON_ERROR_STOP on

-- La migración 0001 también lo pide (IF NOT EXISTS), pero crear la extensión necesita más permisos de los
-- que tiene quien migra.
CREATE EXTENSION IF NOT EXISTS vector;

-- Quien migra crea y cambia la estructura. Desde PostgreSQL 15, PUBLIC ya no puede crear en el esquema public.
GRANT USAGE, CREATE ON SCHEMA public TO steward_migraciones;

-- Nadie entra a la base si no tiene un rol del proyecto.
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', current_database()) \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %s', current_database(),
              'steward_migraciones, steward_backend, steward_mcp, steward_consultas, steward_carga, equipo_lectura, equipo_datos')
\gexec

-- Seguridad por fila: las vistas leen app.rol y app.usuario. Si steward_consultas pudiera ejecutar set_config,
-- un SELECT de consulta libre podría cambiarse el rol. La migración 0003 intenta quitar el permiso, pero quien
-- migra (steward_migraciones) no es dueño de la función y su REVOKE no tiene efecto; por eso se hace aquí.
-- La aplicación fija el contexto con SET LOCAL y no depende de set_config.
REVOKE EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean)
  TO steward_migraciones, steward_backend, steward_mcp, equipo_lectura, equipo_datos;

-- En RDS el usuario maestro tampoco es dueño de la función: el REVOKE puede no aplicar. Se avisa en vez de fallar.
DO $$
BEGIN
  IF has_function_privilege('steward_consultas', 'pg_catalog.set_config(text, text, boolean)', 'EXECUTE') THEN
    RAISE WARNING 'steward_consultas todavía puede ejecutar set_config en %: la seguridad por fila depende de la validación del SQL en ejecutar_consulta.', current_database();
  END IF;
END $$;
