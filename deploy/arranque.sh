#!/usr/bin/env bash
# Corre en cada encendido de la EC2 (servicio de systemd dsa-arranque, lo instala user-data.sh):
#   1. Une la instancia a Tailscale si todavía no lo está y ya existe la llave en SSM.
#   2. Regenera /opt/dsa/.env desde SSM.
#   3. Levanta los contenedores con la versión vigente (/dsa/<env>/image_tag).
# Si todavía no hay versión desplegada, solo deja todo listo y termina sin error.
set -euo pipefail

DSA_DIR="${DSA_DIR:-/opt/dsa}"
# shellcheck source=/dev/null
. "$DSA_DIR/ambiente"
: "${DSA_ENV:?Falta DSA_ENV en $DSA_DIR/ambiente}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"

log() { echo "dsa-arranque: $*" >&2; }

# Al encender el lab la red puede tardar unos segundos; SSM es lo primero que se necesita.
reintentar() {
  local intento
  for intento in 1 2 3 4 5 6 7 8 9 10; do
    if "$@"; then return 0; fi
    log "reintento $intento de 10: $*"
    sleep 6
  done
  return 1
}

# --- 1. Tailscale --------------------------------------------------------------------------------------------------
if command -v tailscale > /dev/null; then
  if tailscale status > /dev/null 2>&1; then
    log "Tailscale ya está conectado."
  else
    llave="$(reintentar aws ssm get-parameter --with-decryption --name /dsa/shared/tailscale_authkey \
      --query Parameter.Value --output text || true)"
    if [ -n "$llave" ] && [ "$llave" != "CAMBIAR" ]; then
      # La etiqueta tag:aws viene en la llave. Llave no efímera: la instancia sigue en la tailnet tras apagarse.
      tailscale up --auth-key="$llave" --hostname="dsa-$DSA_ENV" && log "Unida a Tailscale como dsa-$DSA_ENV."
    else
      log "Sin llave de Tailscale en SSM todavía; la app no llegará a Ollama hasta que exista."
    fi
    unset llave
  fi
fi

# --- 2. Configuración ------------------------------------------------------------------------------------------------
reintentar "$DSA_DIR/generar-env.sh"

# --- 3. Contenedores -------------------------------------------------------------------------------------------------
tag="$(sed -n 's/^IMAGE_TAG=//p' "$DSA_DIR/.env")"
if [ -z "$tag" ]; then
  log "Todavía no hay versión desplegada (/dsa/$DSA_ENV/image_tag); nada que levantar."
  exit 0
fi

cd "$DSA_DIR"
log "Levantando la versión $tag."
docker compose up -d --remove-orphans
