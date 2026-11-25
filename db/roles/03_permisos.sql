-- Permisos de la carga de datos y de los grupos del equipo en una base.
--
-- Ejecutar como steward_migraciones (dueño de las tablas), conectado a la base:
--   psql -v ON_ERROR_STOP=1 -v equipo_datos_escribe=true  -d dsa_dev  -f db/roles/03_permisos.sql
--   psql -v ON_ERROR_STOP=1 -v equipo_datos_escribe=false -d dsa_prod -f db/roles/03_permisos.sql
--
-- Idempotente. Puede correr antes o después de las migraciones:
--   - ALTER DEFAULT PRIVILEGES cubre las tablas que creen las migraciones futuras;
--   - los GRANT ... ON ALL cubren las tablas que ya existen.
-- Los permisos de steward_backend, steward_mcp y steward_consultas los dan las migraciones.

\set ON_ERROR_STOP on
\if :{?equipo_datos_escribe}
\else
\set equipo_datos_escribe false
\endif

-- steward_carga: carga de semillas (make datos). No puede cambiar la estructura ni vaciar tablas.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO steward_carga;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO steward_carga;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO steward_carga;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO steward_carga;

-- equipo_lectura: leer todo (tablas y vistas).
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO equipo_lectura;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO equipo_lectura;

-- equipo_datos: leer en todas las bases; escribir datos solo donde equipo_datos_escribe=true (local y dev).
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO equipo_datos;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO equipo_datos;
\if :equipo_datos_escribe
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT INSERT, UPDATE, DELETE ON TABLES TO equipo_datos;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO equipo_datos;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO equipo_datos;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO equipo_datos;
\else
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE INSERT, UPDATE, DELETE ON TABLES FROM equipo_datos;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT, UPDATE ON SEQUENCES FROM equipo_datos;
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM equipo_datos;
REVOKE USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public FROM equipo_datos;
\endif
