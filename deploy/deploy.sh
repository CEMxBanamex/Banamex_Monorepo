#!/usr/bin/env bash
# Despliega una versión de las imágenes en esta EC2 y, si algo falla, deja corriendo la anterior.
#
#   deploy.sh <tag> <dev|prod> [--ref <git-ref>] [--sin-migraciones]
#
#   <tag>             tag de las imágenes en GHCR (el SHA del commit en dev, vX.Y.Z en prod).
#   --ref <git-ref>   antes de desplegar, actualiza los archivos de /opt/dsa (este script, el Compose, el Caddyfile...)
#                     con los del repo en ese commit, para que coincidan con la versión.
#   --sin-migraciones no corre las migraciones (por ejemplo, para regresar a una versión anterior).
#
# Pasos: regenera .env desde SSM, baja las imágenes, corre las migraciones como steward_migraciones, levanta los
# contenedores y revisa /api/health. Si funciona, guarda el tag en /dsa/<env>/image_tag; si no, regresa al anterior.
# Las migraciones no se deshacen al regresar: deben ser compatibles con la versión anterior.
set -euo pipefail

DSA_DIR="${DSA_DIR:-/opt/dsa}"
ARCHIVOS=(docker-compose.yml Caddyfile generar-env.sh arranque.sh deploy.sh)

uso() { echo "Uso: $0 <tag> <dev|prod> [--ref <git-ref>] [--sin-migraciones]" >&2; exit 2; }
log() { echo "deploy [$(date '+%H:%M:%S')]: $*" >&2; }

[ $# -ge 2 ] || uso
TAG="$1" ENV_DESTINO="$2"
shift 2
REF="" MIGRAR=true
while [ $# -gt 0 ]; do
  case "$1" in
    --ref) [ $# -ge 2 ] || uso; REF="$2"; shift 2 ;;
    --sin-migraciones) MIGRAR=false; shift ;;
    *) uso ;;
  esac
done
case "$ENV_DESTINO" in dev|prod) ;; *) uso ;; esac
[[ "$TAG" =~ ^[A-Za-z0-9._-]+$ ]] || { log "tag inválido: $TAG"; exit 2; }

# shellcheck source=/dev/null
. "$DSA_DIR/ambiente"
if [ "$DSA_ENV" != "$ENV_DESTINO" ]; then
  log "esta instancia es $DSA_ENV, no $ENV_DESTINO."
  exit 2
fi
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"

# Un solo despliegue a la vez en esta instancia.
exec 9> "$DSA_DIR/.deploy.lock"
flock -n 9 || { log "ya hay un despliegue en curso."; exit 1; }

cd "$DSA_DIR"

# --- 1. Archivos de despliegue de esa versión ----------------------------------------------------------------------
if [ -n "$REF" ]; then
  : "${GITHUB_REPO:?Falta GITHUB_REPO en $DSA_DIR/ambiente}"
  log "actualizando los archivos de despliegue desde $GITHUB_REPO@$REF."
  nuevos="$(mktemp -d)"
  for archivo in "${ARCHIVOS[@]}"; do
    curl -fsSL --retry 3 -o "$nuevos/$archivo" \
      "https://raw.githubusercontent.com/$GITHUB_REPO/$REF/deploy/$archivo"
  done
  chmod 755 "$nuevos"/*.sh
  # mv reemplaza cada archivo de golpe; bash sigue leyendo esta copia de deploy.sh sin problema.
  for archivo in "${ARCHIVOS[@]}"; do mv -f "$nuevos/$archivo" "$DSA_DIR/$archivo"; done
  rmdir "$nuevos"
fi

# --- 2. Configuración y versión anterior ---------------------------------------------------------------------------
"$DSA_DIR/generar-env.sh"
ANTERIOR="$(sed -n 's/^IMAGE_TAG=//p' .env)"
# generar-env.sh omite los valores CAMBIAR: si todavía no hay versión desplegada, ANTERIOR queda vacío.
log "versión actual: ${ANTERIOR:-ninguna}; nueva: $TAG."

# IMAGE_TAG del ambiente tiene prioridad sobre el de .env al interpolar el Compose.
compose() { IMAGE_TAG="$1" docker compose "${@:2}"; }

# --- 3. Bajar imágenes: si el tag no existe, no se toca nada de lo que está corriendo -------------------------------
if ! compose "$TAG" --profile tareas pull --quiet backend mcp migraciones; then
  log "no se pudieron bajar las imágenes de $TAG. Sigue corriendo ${ANTERIOR:-nada}."
  exit 1
fi

# --- 4. Migraciones --------------------------------------------------------------------------------------------------
if $MIGRAR; then
  log "corriendo migraciones."
  if ! compose "$TAG" --profile tareas run --rm migraciones; then
    log "fallaron las migraciones de $TAG. Sigue corriendo ${ANTERIOR:-nada}."
    exit 1
  fi
fi

# --- 5. Levantar y revisar la salud ---------------------------------------------------------------------------------
salud() {
  local intento
  for intento in $(seq 1 30); do
    if curl -fsS -o /dev/null --max-time 3 "http://127.0.0.1:${BACKEND_PUERTO:-8000}/api/health"; then
      return 0
    fi
    sleep 2
  done
  log "el backend no respondió /api/health en 60 s (intento $intento)."
  return 1
}

log "levantando $TAG."
if compose "$TAG" up -d --remove-orphans && salud; then
  aws ssm put-parameter --overwrite --type String --name "/dsa/$DSA_ENV/image_tag" --value "$TAG" > /dev/null
  # .env queda con la versión nueva, para que `docker compose ...` a mano y el próximo arranque usen la misma.
  "$DSA_DIR/generar-env.sh"
  docker image prune -f > /dev/null || true
  log "listo: $DSA_ENV corre $TAG."
  exit 0
fi

# --- 6. Regresar a la versión anterior ------------------------------------------------------------------------------
compose "$TAG" logs --tail=50 backend mcp >&2 || true
if [ -n "$ANTERIOR" ]; then
  log "regresando a $ANTERIOR."
  if compose "$ANTERIOR" up -d --remove-orphans && salud; then
    log "se regresó a $ANTERIOR. El despliegue de $TAG falló."
  else
    log "tampoco respondió $ANTERIOR. Revisa: docker compose logs"
  fi
else
  log "no hay versión anterior a la cual regresar; se detienen los contenedores."
  compose "$TAG" down || true
fi
exit 1
