#!/usr/bin/env bash
# Genera /opt/dsa/.env a partir de SSM Parameter Store. Lo llaman arranque.sh y deploy.sh; no guarda nada en el repo.
#
#   generar-env.sh [archivo-de-salida]      (por omisión $DSA_DIR/.env)
#
# Lee:
#   /dsa/<env>/*            configuración del ambiente (api_host, db_host, image_tag, ...). Cada nombre pasa a
#                           mayúsculas: /dsa/dev/api_host -> API_HOST.
#   /dsa/shared/db/<rol>    contraseñas de los usuarios de servicio (las crea scripts/db/crear-bases.sh).
# Y arma las cadenas de conexión de cada componente con su propio usuario de la base.
set -euo pipefail

DSA_DIR="${DSA_DIR:-/opt/dsa}"
# shellcheck source=/dev/null
[ -f "$DSA_DIR/ambiente" ] && . "$DSA_DIR/ambiente"
: "${DSA_ENV:?Falta DSA_ENV (dev o prod) en $DSA_DIR/ambiente}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
SALIDA="${1:-$DSA_DIR/.env}"

declare -A valor=()

# Lee los parámetros directos de una ruta como "nombre<TAB>valor".
leer_ruta() {
  aws ssm get-parameters-by-path --path "$1" --with-decryption \
    --query 'Parameters[].[Name,Value]' --output text
}

while IFS=$'\t' read -r nombre dato; do
  [ -n "$nombre" ] || continue
  # CAMBIAR es el valor de relleno de Terraform: se trata como "todavía no existe".
  [ "$dato" = "CAMBIAR" ] && continue
  clave="${nombre##*/}"
  valor["${clave^^}"]="$dato"
done < <(leer_ruta "/dsa/$DSA_ENV")

declare -A clave_db=()
while IFS=$'\t' read -r nombre dato; do
  [ -n "$nombre" ] || continue
  clave_db["${nombre##*/}"]="$dato"
done < <(leer_ruta "/dsa/shared/db")

for requerido in API_HOST IMAGE_REGISTRY DB_HOST DB_PORT DB_NAME; do
  if [ -z "${valor[$requerido]:-}" ]; then
    echo "generar-env: falta /dsa/$DSA_ENV/${requerido,,} en SSM (¿se aplicó Terraform de $DSA_ENV?)." >&2
    exit 1
  fi
done

url() {
  local rol="$1" clave="${clave_db[$1]:-}"
  if [ -z "$clave" ] || [ "$clave" = "CAMBIAR" ]; then
    echo "generar-env: falta la contraseña /dsa/shared/db/$rol (corre scripts/db/crear-bases.sh)." >&2
    exit 1
  fi
  # Las contraseñas son alfanuméricas (las genera crear-bases.sh), así que no hace falta codificarlas en la URL.
  printf 'postgresql+psycopg://%s:%s@%s:%s/%s?sslmode=%s' \
    "$rol" "$clave" "${valor[DB_HOST]}" "${valor[DB_PORT]}" "${valor[DB_NAME]}" "${valor[DB_SSLMODE]:-require}"
}

temporal="$(mktemp "${SALIDA}.XXXXXX")"
trap 'rm -f "$temporal"' EXIT
chmod 600 "$temporal"
{
  echo "# Generado por generar-env.sh desde SSM ($DSA_ENV). No lo edites: se sobrescribe en cada arranque."
  for clave in $(printf '%s\n' "${!valor[@]}" | sort); do
    printf '%s=%s\n' "$clave" "${valor[$clave]}"
  done
  printf 'DSA_ENV=%s\n' "$DSA_ENV"
  printf 'AWS_REGION=%s\n' "$AWS_REGION"
  printf 'DATABASE_URL=%s\n' "$(url steward_backend)"
  printf 'MCP_DATABASE_URL=%s\n' "$(url steward_mcp)"
  printf 'CONSULTAS_DATABASE_URL=%s\n' "$(url steward_consultas)"
  printf 'MIGRACIONES_DATABASE_URL=%s\n' "$(url steward_migraciones)"
  printf 'CARGA_DATABASE_URL=%s\n' "$(url steward_carga)"
} > "$temporal"
mv -f "$temporal" "$SALIDA"
trap - EXIT
echo "generar-env: $SALIDA listo (${#valor[@]} parámetros de /dsa/$DSA_ENV)."
