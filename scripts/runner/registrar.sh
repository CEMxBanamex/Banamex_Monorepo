#!/usr/bin/env bash
# Instala el runner self-hosted de GitHub Actions en la EC2 de dev, como servicio.
# Se corre UNA vez, como root, por Session Manager (sudo bash scripts/runner/registrar.sh, o copiándolo a la EC2).
#
#   registrar.sh <org>/<repo>
#
# Pide el token de registro sin mostrarlo: GitHub → repo → Settings → Actions → Runners → New self-hosted runner.
# El token caduca en una hora; si caduca, genera otro.
#
# Seguridad: el runner corre con el usuario sin privilegios "runner". Lo único que puede hacer como root es
# /opt/dsa/deploy.sh (regla de sudo). Ningún workflow que use este runner se dispara con pull_request.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Córrelo como root (sudo)." >&2; exit 1; }
[ $# -eq 1 ] || { echo "Uso: $0 <org>/<repo>" >&2; exit 2; }
REPO="$1"
DIR=/opt/actions-runner
ETIQUETAS="dsa-dev"

read -rsp "Token de registro del runner: " TOKEN
echo
[ -n "$TOKEN" ] || { echo "Token vacío." >&2; exit 1; }

# Usuario sin privilegios; deploy.sh es lo único que puede correr como root.
id runner > /dev/null 2>&1 || useradd --system --create-home --shell /bin/bash runner
echo "runner ALL=(root) NOPASSWD: /opt/dsa/deploy.sh" > /etc/sudoers.d/dsa-runner
chmod 440 /etc/sudoers.d/dsa-runner
visudo -cf /etc/sudoers.d/dsa-runner

# Dependencias del runner (.NET) en Amazon Linux 2023.
dnf install -y libicu tar gzip

# Última versión publicada del runner.
VERSION="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))')"
echo "Runner $VERSION"

mkdir -p "$DIR"
if [ ! -x "$DIR/config.sh" ]; then
  curl -fsSL --retry 5 -o /tmp/actions-runner.tar.gz \
    "https://github.com/actions/runner/releases/download/v$VERSION/actions-runner-linux-x64-$VERSION.tar.gz"
  tar -xzf /tmp/actions-runner.tar.gz -C "$DIR"
  rm -f /tmp/actions-runner.tar.gz
fi
chown -R runner:runner "$DIR"

cd "$DIR"
sudo -u runner ./config.sh --unattended --replace \
  --url "https://github.com/$REPO" --token "$TOKEN" \
  --name "dsa-dev" --labels "$ETIQUETAS" --work _work
unset TOKEN

./svc.sh install runner
./svc.sh start
./svc.sh status | head -n 5
echo "Runner registrado con las etiquetas self-hosted, linux, x64 y $ETIQUETAS."
