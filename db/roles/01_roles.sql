-- Roles y grupos de toda la instancia de PostgreSQL. Es el mismo script en local y en RDS.
--
-- Ejecutar como superusuario (local) o como usuario maestro (RDS), conectado a cualquier base:
--   psql -v ON_ERROR_STOP=1 -v clave_backend=... -v clave_mcp=... -f db/roles/01_roles.sql
--
-- Idempotente: crea lo que falta y no toca lo que ya existe. Las contraseñas son opcionales: solo se cambian
-- las que se pasan con -v (clave_migraciones, clave_backend, clave_mcp, clave_consultas, clave_carga).
-- Las migraciones nunca crean roles; solo otorgan permisos a los que ya existen.

\set ON_ERROR_STOP on

-- Usuarios de servicio (pueden iniciar sesión).
SELECT format('CREATE ROLE %I LOGIN', r)
FROM unnest(ARRAY['steward_migraciones', 'steward_backend', 'steward_mcp', 'steward_consultas', 'steward_carga']) AS r
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r)
\gexec

-- Grupos del equipo (sin inicio de sesión). Cada integrante es un usuario aparte, miembro de uno de ellos.
SELECT format('CREATE ROLE %I NOLOGIN', r)
FROM unnest(ARRAY['equipo_lectura', 'equipo_datos']) AS r
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r)
\gexec

-- Consulta libre del chat: límite de tiempo por sentencia.
ALTER ROLE steward_consultas SET statement_timeout = '5s';

-- La migración 0002 repite el ALTER ROLE de arriba. Para que quien migra pueda hacerlo sin ser superusuario
-- (en PostgreSQL 16 se necesita CREATEROLE y ADMIN OPTION sobre el rol), se le da solo eso: no puede usar
-- el rol ni heredar sus permisos.
ALTER ROLE steward_migraciones CREATEROLE;
SELECT 'GRANT steward_consultas TO steward_migraciones WITH ADMIN OPTION, INHERIT FALSE, SET FALSE'
WHERE NOT EXISTS (
  SELECT 1 FROM pg_auth_members m
  WHERE m.roleid = 'steward_consultas'::regrole AND m.member = 'steward_migraciones'::regrole AND m.admin_option
)
\gexec

-- Contraseñas (solo las que se pasaron con -v).
\if :{?clave_migraciones}
SELECT format('ALTER ROLE steward_migraciones PASSWORD %L', :'clave_migraciones') \gexec
\endif
\if :{?clave_backend}
SELECT format('ALTER ROLE steward_backend PASSWORD %L', :'clave_backend') \gexec
\endif
\if :{?clave_mcp}
SELECT format('ALTER ROLE steward_mcp PASSWORD %L', :'clave_mcp') \gexec
\endif
\if :{?clave_consultas}
SELECT format('ALTER ROLE steward_consultas PASSWORD %L', :'clave_consultas') \gexec
\endif
\if :{?clave_carga}
SELECT format('ALTER ROLE steward_carga PASSWORD %L', :'clave_carga') \gexec
\endif
