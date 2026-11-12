#!/usr/bin/env bash
# Configura las reglas del repo en GitHub: rama dev, reglas de dev y main, environments y aprobación de workflows
# de colaboradores externos. Lo ejecuta quien administra el repo, una vez, después de que ci.yml esté en dev.
#
#   scripts/github/configurar-repo.sh             # solo muestra lo que haría (no cambia nada)
#   scripts/github/configurar-repo.sh --aplicar   # aplica los cambios
#
# Requisitos: gh con sesión de un administrador del repo (no necesita jq). Es idempotente: se puede correr varias veces.
# El repo se toma del remoto de la carpeta actual; para otro, exporta GH_REPO=<ORG>/<REPO>.
set -euo pipefail

APLICAR=false
case "${1:-}" in
  --aplicar) APLICAR=true ;;
  "") ;;
  *) echo "Uso: $0 [--aplicar]" >&2; exit 2 ;;
esac

command -v gh > /dev/null || { echo "Falta gh (GitHub CLI)." >&2; exit 1; }

REPO="${GH_REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
CHECK="ci-ok"

if [ "$(gh api "repos/$REPO" --jq .permissions.admin)" != "true" ]; then
  echo "Tu sesión de gh no es administradora de $REPO." >&2
  exit 1
fi

echo "Repositorio: $REPO"
if $APLICAR; then echo "Modo: APLICAR"; else echo "Modo: solo mostrar (agrega --aplicar para hacer los cambios)"; fi
echo

# Ejecuta gh api solo con --aplicar; si no, muestra la llamada y, si lo hay, el cuerpo JSON.
llamar() {
  local descripcion="$1" metodo="$2" ruta="$3" cuerpo="${4:-}"
  echo "-> $descripcion"
  echo "   $metodo $ruta"
  if ! $APLICAR; then
    # shellcheck disable=SC2001
    if [ -n "$cuerpo" ]; then echo "$cuerpo" | sed 's/^/   /'; fi
    return 0
  fi
  if [ -n "$cuerpo" ]; then
    echo "$cuerpo" | gh api -X "$metodo" "$ruta" --input - > /dev/null
  else
    gh api -X "$metodo" "$ruta" > /dev/null
  fi
  echo "   listo"
}

# --- 1. Rama dev --------------------------------------------------------------------------------------------------
if gh api "repos/$REPO/branches/dev" > /dev/null 2>&1; then
  echo "-> La rama dev ya existe."
else
  sha_main="$(gh api "repos/$REPO/git/ref/heads/main" --jq .object.sha)"
  llamar "Crear dev desde main" POST "repos/$REPO/git/refs" \
    "{\"ref\": \"refs/heads/dev\", \"sha\": \"$sha_main\"}"
fi
echo

# --- 2. Métodos de merge del repo ---------------------------------------------------------------------------------
# dev se fusiona con squash y main con merge commit (para conservar el SHA de dev), así que ambos deben existir.
llamar "Permitir squash y merge commit; desactivar rebase" PATCH "repos/$REPO" \
  '{"allow_squash_merge": true, "allow_merge_commit": true, "allow_rebase_merge": false}'
echo

# --- 3. Reglas de las ramas (rulesets) ----------------------------------------------------------------------------
# Crea el ruleset o lo reemplaza si ya existe uno con el mismo nombre.
ruleset() {
  local nombre="$1" cuerpo="$2" id
  id="$(gh api "repos/$REPO/rulesets" --jq ".[] | select(.name == \"$nombre\") | .id" | head -n 1)"
  if [ -n "$id" ]; then
    llamar "Actualizar las reglas '$nombre'" PUT "repos/$REPO/rulesets/$id" "$cuerpo"
  else
    llamar "Crear las reglas '$nombre'" POST "repos/$REPO/rulesets" "$cuerpo"
  fi
}

# dev: PR obligatorio sin aprobaciones, CI obligatorio, rama al día, solo squash, sin force push ni borrado.
ruleset "dev" "$(cat <<JSON
{
  "name": "dev",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/heads/dev"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 0,
      "dismiss_stale_reviews_on_push": false,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_review_thread_resolution": false,
      "allowed_merge_methods": ["squash"]
    }},
    {"type": "required_status_checks", "parameters": {
      "strict_required_status_checks_policy": true,
      "required_status_checks": [{"context": "$CHECK"}]
    }}
  ]
}
JSON
)"

# main: PR obligatorio con 1 aprobación de cualquier integrante, se descartan aprobaciones viejas, CI obligatorio,
# solo merge commit, sin force push ni borrado. Que el PR venga de dev lo revisa el job origen-main del CI.
# La revisión obligatoria de code owners queda apagada para no frenar al equipo: CODEOWNERS solo sugiere a quién
# pedirle revisión. Para exigirla, cambia require_code_owner_review a true y vuelve a correr el script.
ruleset "main" "$(cat <<JSON
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews_on_push": true,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_review_thread_resolution": false,
      "allowed_merge_methods": ["merge"]
    }},
    {"type": "required_status_checks", "parameters": {
      "strict_required_status_checks_policy": false,
      "required_status_checks": [{"context": "$CHECK"}]
    }}
  ]
}
JSON
)"
echo

# --- 4. Environments ----------------------------------------------------------------------------------------------
# Sin aprobación: el PR a main ya es el punto de control. Sirven para registrar qué SHA se desplegó en cada uno.
for ambiente in dev prod; do
  llamar "Environment '$ambiente'" PUT "repos/$REPO/environments/$ambiente"
done
echo

# --- 5. Workflows de colaboradores externos -----------------------------------------------------------------------
# El repo es público y tendrá un runner self-hosted: nadie de fuera debe poder correr workflows sin aprobación.
echo "-> Exigir aprobación para los workflows de todos los colaboradores externos"
echo "   PUT repos/$REPO/actions/permissions/fork-pr-contributor-approval"
if $APLICAR; then
  if echo '{"approval_policy": "all_external_contributors"}' \
    | gh api -X PUT "repos/$REPO/actions/permissions/fork-pr-contributor-approval" --input - > /dev/null 2>&1; then
    echo "   listo"
  else
    echo "   No se pudo por la API. Hazlo a mano: Settings > Actions > General > Approval for running fork pull"
    echo "   request workflows from contributors > Require approval for all external contributors."
  fi
fi
echo

if $APLICAR; then
  echo "Terminado. Revisa Settings > Rules > Rulesets y Settings > Environments."
else
  echo "No se cambió nada. Para aplicar: $0 --aplicar"
fi
