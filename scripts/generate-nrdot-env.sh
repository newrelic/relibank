#!/usr/bin/env bash
# Generates k8s/base/infrastructure/newrelic/nrdot-mssql.env from skaffold.env.
#
# Invoked automatically by the build.artifacts[0].hooks.before hook in
# skaffold.yaml so the file exists before kustomize render. Can also be run
# manually if you need to force-regenerate (e.g., the build cache hit and the
# hook was skipped, or you deleted the file). The generated file holds real
# credentials and is gitignored — never commit it.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ENV_FILE="skaffold.env"
NRDOT_ENV="k8s/base/infrastructure/newrelic/nrdot-mssql.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "error: ${ENV_FILE} not found at repo root — see README 'Credentials Setup'" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "./${ENV_FILE}"
set +a

: "${MSSQL_NEWRELIC_PASSWORD:?must be set in skaffold.env — see README 'Credentials Setup'}"
: "${NEW_RELIC_LICENSE_KEY:?must be set in skaffold.env — see README 'Credentials Setup'}"

mkdir -p "$(dirname "${NRDOT_ENV}")"
new_content="$(printf 'MSSQL_NEWRELIC_PASSWORD=%s\nNEW_RELIC_LICENSE_KEY=%s\nNEW_RELIC_OTLP_ENDPOINT=%s\n' \
  "${MSSQL_NEWRELIC_PASSWORD}" \
  "${NEW_RELIC_LICENSE_KEY}" \
  "${NEW_RELIC_OTLP_ENDPOINT:-https://otlp.nr-data.net}")"

# Avoid bumping mtime when content is unchanged — skaffold dev watches
# manifest paths and would otherwise trigger a redeploy loop.
if [[ -f "${NRDOT_ENV}" ]] && [[ "${new_content}" == "$(cat "${NRDOT_ENV}")" ]]; then
  echo "${NRDOT_ENV} already up to date"
else
  printf '%s' "${new_content}" > "${NRDOT_ENV}"
  echo "generated ${NRDOT_ENV}"
fi
