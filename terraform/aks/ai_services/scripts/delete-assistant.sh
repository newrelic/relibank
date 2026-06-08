#!/usr/bin/env bash
# delete-assistant.sh
# Best-effort delete of an Azure OpenAI Assistant via the dataplane API.
# Reads the assistant id from $OUTPUT_FILE; the AOAI account itself is destroyed
# by the surrounding `azurerm_cognitive_account` resource so a 404 here is fine.
#
# Required env:
#   AOAI_ENDPOINT — endpoint captured in triggers_replace at create time
#   OUTPUT_FILE   — path to the file holding the assistant id

set -uo pipefail

API_VERSION="2024-05-01-preview"

: "${AOAI_ENDPOINT:?AOAI_ENDPOINT required}"
: "${OUTPUT_FILE:?OUTPUT_FILE required}"

if [[ ! -f "$OUTPUT_FILE" ]]; then
  echo "[delete-assistant] $OUTPUT_FILE not found — nothing to delete"
  exit 0
fi

ASSISTANT_ID="$(tr -d '[:space:]' < "$OUTPUT_FILE")"
if [[ -z "$ASSISTANT_ID" ]]; then
  echo "[delete-assistant] empty id in $OUTPUT_FILE — skipping"
  rm -f "$OUTPUT_FILE"
  exit 0
fi

# Destroy provisioners cannot reference resource attributes, so the API key
# isn't available here. The account itself is being destroyed alongside, so
# we attempt the dataplane DELETE only if AOAI_API_KEY happens to be set
# (e.g. a manual taint+apply). Otherwise we just clean up the local id file.
ENDPOINT="${AOAI_ENDPOINT%/}"

if [[ -n "${AOAI_API_KEY:-}" ]]; then
  echo "[delete-assistant] deleting $ASSISTANT_ID at $ENDPOINT"
  curl -fsS \
    -X DELETE \
    -H "api-key: $AOAI_API_KEY" \
    "$ENDPOINT/openai/assistants/$ASSISTANT_ID?api-version=$API_VERSION" \
    || echo "[delete-assistant] WARN: delete failed (assistant may already be gone or account destroyed)"
else
  echo "[delete-assistant] no API key in env — skipping dataplane DELETE (account destroy will reap it)"
fi

rm -f "$OUTPUT_FILE"
