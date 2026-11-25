#!/usr/bin/env bash
# Prepara la instancia RDS: roles, grupos, un usuario por integrante y las bases dsa_dev y dsa_prod.
# Se corre UNA vez (se puede repetir sin romper nada), desde la raíz del repo, después de aplicar
# infra/terraform/envs/shared y ANTES de la primera migración.
#
#   scripts/db/crear-bases.sh
#
# Necesita: aws (credenciales del lab), docker (usa psql dentro de un contenedor) y python3.
# De dónde saca la conexión (se puede sobrescribir con variables, por ejemplo para probar contra una base local):
#   DB_HOST, DB_PORT      outputs rds_address y rds_port de infra/terraform/envs/shared
#   MASTER_USER/PASSWORD  secreto de la contraseña maestra que administra RDS (output rds_master_secret_arn)
#   DB_SSLMODE            require (RDS obliga SSL)
#
# Contraseñas: las genera, las guarda como SecureString en SSM y NUNCA las imprime.
#   /dsa/shared/db/<rol>                 usuarios de servicio (los lee generar-env.sh en las EC2)
#   /dsa/shared/db/personal/<integrante> usuarios personales; cada quien recibe la suya por mensaje privado
# Si una contraseña ya existe en SSM, la reutiliza.
set -euo pipefail

# Integrantes: un usuario de la base por persona, en su grupo (sección 3 de docs/ci-cd/guia-claude-code-v3.md).
INTEGRANTES_LECTURA=(juan_pablo carlos_delgado carlos_ramos yael mauricio)
INTEGRANTES_DATOS=(iris mario)
ROLES_SERVICIO=(steward_migraciones steward_backend steward_mcp steward_consultas steward_carga)
BASES=(dsa_dev dsa_prod)
PSQL_IMAGE="${PSQL_IMAGE:-pgvector/pgvector:0.8.1-pg16}"

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
SHARED="$RAIZ/infra/terraform/envs/shared"
log() { echo "crear-bases: $*" >&2; }

for herramienta in aws docker python3; do
  command -v "$herramienta" > /dev/null || { log "falta $herramienta."; exit 1; }
done

# --- Conexión ---------------------------------------------------------------------------------------------------------
if [ -z "${DB_HOST:-}" ]; then
  DB_HOST="$(terraform -chdir="$SHARED" output -raw rds_address)"
  DB_PORT="$(terraform -chdir="$SHARED" output -raw rds_port)"
fi
DB_PORT="${DB_PORT:-5432}"
DB_SSLMODE="${DB_SSLMODE:-require}"

if [ -z "${MASTER_PASSWORD:-}" ]; then
  secreto="$(terraform -chdir="$SHARED" output -raw rds_master_secret_arn)"
  # Sin mapfile: el bash de macOS es 3.2.
  { IFS= read -r MASTER_USER && IFS= read -r MASTER_PASSWORD; } < <(aws secretsmanager get-secret-value \
    --secret-id "$secreto" --query SecretString --output text \
    | python3 -c 'import json, sys; d = json.load(sys.stdin); print(d["username"]); print(d["password"])')
  unset secreto
fi
: "${MASTER_USER:?Falta MASTER_USER}"
log "conectando a $DB_HOST:$DB_PORT como $MASTER_USER (sslmode=$DB_SSLMODE)."

# psql dentro de un contenedor. Las contraseñas viajan por variables de entorno o por stdin, nunca como argumentos.
psql_como() {
  local usuario="$1" clave="$2" base="$3"
  shift 3
  PGPASSWORD="$clave" docker run --rm -i -e PGPASSWORD -e PGSSLMODE="$DB_SSLMODE" \
    -v "$RAIZ/db/roles:/roles:ro" "$PSQL_IMAGE" \
    psql -X -q -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$usuario" -d "$base" "$@"
}

# --- Contraseñas en SSM -----------------------------------------------------------------------------------------------
nueva_clave() {
  # Solo letras y números: así no hay que codificarlas en las cadenas de conexión.
  python3 -c 'import secrets, string; a = string.ascii_letters + string.digits; print("".join(secrets.choice(a) for _ in range(32)))'
}

# Imprime la contraseña guardada en SSM; si no existe, la crea primero.
clave_de() {
  local nombre="$1" clave
  if clave="$(aws ssm get-parameter --with-decryption --name "$nombre" --query Parameter.Value --output text 2> /dev/null)"; then
    printf '%s' "$clave"
    return
  fi
  clave="$(nueva_clave)"
  aws ssm put-parameter --type SecureString --name "$nombre" --value "$clave" > /dev/null
  log "contraseña nueva en $nombre."
  printf '%s' "$clave"
}

# Sin arreglos asociativos (el bash de macOS es 3.2): cada contraseña va en una variable CLAVE_<nombre>.
guardar_clave() { printf -v "CLAVE_$1" '%s' "$2"; }
clave() { local var="CLAVE_$1"; printf '%s' "${!var}"; }

for rol in "${ROLES_SERVICIO[@]}"; do
  guardar_clave "$rol" "$(clave_de "/dsa/shared/db/$rol")"
done
for persona in "${INTEGRANTES_LECTURA[@]}" "${INTEGRANTES_DATOS[@]}"; do
  guardar_clave "$persona" "$(clave_de "/dsa/shared/db/personal/$persona")"
done

# --- 1. Roles de servicio y grupos (de toda la instancia) ------------------------------------------------------------
log "roles de servicio y grupos (db/roles/01_roles.sql)."
{
  for rol in "${ROLES_SERVICIO[@]}"; do
    printf '\\set clave_%s %s\n' "${rol#steward_}" "$(clave "$rol")"
  done
  echo '\i /roles/01_roles.sql'
} | psql_como "$MASTER_USER" "$MASTER_PASSWORD" postgres

# --- 2. Usuarios personales -------------------------------------------------------------------------------------------
log "usuarios personales: $((${#INTEGRANTES_LECTURA[@]} + ${#INTEGRANTES_DATOS[@]}))."
{
  echo '\set ON_ERROR_STOP on'
  for persona in "${INTEGRANTES_LECTURA[@]}" "${INTEGRANTES_DATOS[@]}"; do
    grupo=equipo_lectura
    for d in "${INTEGRANTES_DATOS[@]}"; do [ "$d" = "$persona" ] && grupo=equipo_datos; done
    printf "SELECT format('CREATE ROLE %%I LOGIN', '%s') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '%s')\n\\\\gexec\n" "$persona" "$persona"
    printf "SELECT format('ALTER ROLE %%I PASSWORD %%L', '%s', '%s')\n\\\\gexec\n" "$persona" "$(clave "$persona")"
    printf "GRANT %s TO %s;\n" "$grupo" "$persona"
  done
} | psql_como "$MASTER_USER" "$MASTER_PASSWORD" postgres

# --- 3. Bases ---------------------------------------------------------------------------------------------------------
for base in "${BASES[@]}"; do
  log "base $base."
  printf "SELECT 'CREATE DATABASE %s' WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '%s')\n\\\\gexec\n" "$base" "$base" \
    | psql_como "$MASTER_USER" "$MASTER_PASSWORD" postgres
  # Extensión vector, permisos del esquema, set_config y CONNECT (db/roles/02_base.sql).
  psql_como "$MASTER_USER" "$MASTER_PASSWORD" "$base" -f /roles/02_base.sql
  # Permisos de la carga y de los grupos del equipo; equipo_datos solo escribe en dev.
  escribe=false
  [ "$base" = "dsa_dev" ] && escribe=true
  psql_como steward_migraciones "$(clave steward_migraciones)" "$base" \
    -v equipo_datos_escribe="$escribe" -f /roles/03_permisos.sql
done

unset MASTER_PASSWORD
log "listo. Bases: ${BASES[*]}. Siguiente paso: migraciones (las corre deploy.sh en cada despliegue)."
log "contraseña de un integrante: aws ssm get-parameter --with-decryption --name /dsa/shared/db/personal/<nombre> --query Parameter.Value --output text"
