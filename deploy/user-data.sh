#!/bin/bash
# Prepara una EC2 de Amazon Linux 2023 la PRIMERA vez que arranca (user data de EC2). No vuelve a correr.
# Terraform le antepone las variables DSA_ENV, AWS_REGION, GITHUB_REPO y DEPLOY_REF (envs/<env>/main.tf).
#
#   1. Instala Docker, el plugin de Compose y Tailscale.
#   2. Deja en /opt/dsa los archivos de despliegue del repo (rama DEPLOY_REF).
#   3. Instala el servicio dsa-arranque, que en cada encendido une la instancia a Tailscale, regenera .env desde SSM
#      y levanta la versión vigente. Lo arranca ahora.
# Bitácora: /var/log/dsa-user-data.log
set -euo pipefail
exec > >(tee -a /var/log/dsa-user-data.log) 2>&1

: "${DSA_ENV:?}" "${AWS_REGION:?}" "${GITHUB_REPO:?}" "${DEPLOY_REF:?}"
COMPOSE_VERSION="v2.40.3"
DSA_DIR=/opt/dsa

echo "== dsa user-data: $DSA_ENV, $(date -Is)"

# --- 1. Docker, Compose y Tailscale --------------------------------------------------------------------------------
dnf install -y docker
systemctl enable --now docker

mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL --retry 5 -o /usr/local/lib/docker/cli-plugins/docker-compose \
  "https://github.com/docker/compose/releases/download/$COMPOSE_VERSION/docker-compose-linux-x86_64"
chmod 755 /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version

curl -fsSL --retry 5 https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled

# --- 2. Archivos de despliegue ---------------------------------------------------------------------------------------
mkdir -p "$DSA_DIR"
chmod 750 "$DSA_DIR"
for archivo in docker-compose.yml Caddyfile generar-env.sh arranque.sh deploy.sh; do
  curl -fsSL --retry 5 -o "$DSA_DIR/$archivo" \
    "https://raw.githubusercontent.com/$GITHUB_REPO/$DEPLOY_REF/deploy/$archivo"
done
chmod 755 "$DSA_DIR"/*.sh

cat > "$DSA_DIR/ambiente" <<EOF
DSA_ENV=$DSA_ENV
AWS_REGION=$AWS_REGION
GITHUB_REPO=$GITHUB_REPO
EOF

# --- 3. Servicio de arranque ------------------------------------------------------------------------------------------
cat > /etc/systemd/system/dsa-arranque.service <<EOF
[Unit]
Description=Data Steward: Tailscale, .env desde SSM y contenedores
Wants=network-online.target
After=network-online.target docker.service tailscaled.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$DSA_DIR/arranque.sh
TimeoutStartSec=15min

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable dsa-arranque.service
# --no-block: si todavía no hay llave o versión en SSM, no detiene el resto del user data.
systemctl start --no-block dsa-arranque.service

echo "== dsa user-data: terminado $(date -Is)"
