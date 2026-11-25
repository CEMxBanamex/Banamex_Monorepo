#!/usr/bin/env bash
# Inicialización de PostgreSQL local. La imagen oficial lo ejecuta una sola vez, cuando el volumen está vacío
# (docker-entrypoint-initdb.d). Aplica los mismos scripts de db/roles/ que se usan en RDS.
#
# Variables (las pasa docker-compose.dev.yml desde .env):
#   POSTGRES_DB             base de la aplicación (dsa_local)
#   POSTGRES_DB_PRUEBAS     base desechable para las pruebas de integración (dsa_pruebas)
#   CLAVE_MIGRACIONES, CLAVE_BACKEND, CLAVE_MCP, CLAVE_CONSULTAS, CLAVE_CARGA
set -euo pipefail

roles=/db/roles
psql_su=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --no-password)

"${psql_su[@]}" --dbname "$POSTGRES_DB" \
  -v clave_migraciones="$CLAVE_MIGRACIONES" \
  -v clave_backend="$CLAVE_BACKEND" \
  -v clave_mcp="$CLAVE_MCP" \
  -v clave_consultas="$CLAVE_CONSULTAS" \
  -v clave_carga="$CLAVE_CARGA" \
  -f "$roles/01_roles.sql"

"${psql_su[@]}" --dbname "$POSTGRES_DB" -f "$roles/02_base.sql"

# Antes de las migraciones: deja listos los privilegios por omisión para las tablas que se creen.
psql -v ON_ERROR_STOP=1 --username steward_migraciones --no-password --dbname "$POSTGRES_DB" \
  -v equipo_datos_escribe=true -f "$roles/03_permisos.sql"

# Base de pruebas: la usa datos/tests con el superusuario local (borra y recrea el esquema en cada corrida).
"${psql_su[@]}" --dbname "$POSTGRES_DB" \
  -c "CREATE DATABASE \"${POSTGRES_DB_PRUEBAS}\""
"${psql_su[@]}" --dbname "$POSTGRES_DB_PRUEBAS" -c "CREATE EXTENSION IF NOT EXISTS vector"
