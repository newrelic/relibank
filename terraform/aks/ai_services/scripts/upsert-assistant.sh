#!/usr/bin/env bash
# upsert-assistant.sh
# Idempotently create-or-update an Azure OpenAI Assistant via the dataplane API.
# Looks up an existing assistant by name; updates it if found, creates it otherwise.
# Writes the resulting assistant id to $OUTPUT_FILE so Terraform can read it back.
#
# Required env:
#   AOAI_ENDPOINT  — e.g. https://relibank-sandbox-openai.openai.azure.com/
#   AOAI_API_KEY   — primary key on the AOAI account
#   ASSISTANT_BODY — full request JSON (name, instructions, model, temperature, top_p, tools, metadata)
#   OUTPUT_FILE    — where to write the assistant id

set -euo pipefail

API_VERSION="2024-05-01-preview"

: "${AOAI_ENDPOINT:?AOAI_ENDPOINT required}"
: "${AOAI_API_KEY:?AOAI_API_KEY required}"
: "${ASSISTANT_BODY:?ASSISTANT_BODY required}"
: "${OUTPUT_FILE:?OUTPUT_FILE required}"

ENDPOINT="${AOAI_ENDPOINT%/}"
NAME="$(echo "$ASSISTANT_BODY" | jq -r '.name')"

mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "[upsert-assistant] looking up '$NAME' at $ENDPOINT"

EXISTING_ID=$(curl -fsS \
  -H "api-key: $AOAI_API_KEY" \
  "$ENDPOINT/openai/assistants?api-version=$API_VERSION&limit=100" \
  | jq -r --arg name "$NAME" '.data[] | select(.name == $name) | .id' \
  | head -n 1)

if [[ -n "$EXISTING_ID" && "$EXISTING_ID" != "null" ]]; then
  echo "[upsert-assistant] found existing id=$EXISTING_ID — updating"
  RESULT=$(curl -fsS \
    -X POST \
    -H "api-key: $AOAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$ASSISTANT_BODY" \
    "$ENDPOINT/openai/assistants/$EXISTING_ID?api-version=$API_VERSION")
else
  echo "[upsert-assistant] no existing assistant — creating"
  RESULT=$(curl -fsS \
    -X POST \
    -H "api-key: $AOAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$ASSISTANT_BODY" \
    "$ENDPOINT/openai/assistants?api-version=$API_VERSION")
fi

NEW_ID=$(echo "$RESULT" | jq -r '.id')

if [[ -z "$NEW_ID" || "$NEW_ID" == "null" ]]; then
  echo "[upsert-assistant] ERROR: response did not contain id"
  echo "$RESULT" >&2
  exit 1
fi

echo -n "$NEW_ID" > "$OUTPUT_FILE"
echo "[upsert-assistant] wrote $NEW_ID -> $OUTPUT_FILE"
