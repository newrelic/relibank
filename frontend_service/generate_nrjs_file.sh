#!/bin/sh

# File to modify
TARGET_FILE="app/nr.js"

# --- Validation ---
if [ ! -f "$TARGET_FILE" ]; then
    echo "Error: Target file '$TARGET_FILE' not found."
    exit 1
fi

# Check if required environment variables are set
if [ -z "$NEW_RELIC_BROWSER_APPLICATION_ID" ] || \
   [ -z "$NEW_RELIC_LICENSE_KEY" ] || \
   [ -z "$NEW_RELIC_ACCOUNT_ID" ] || \
   [ -z "$NEW_RELIC_TRUST_KEY" ]; then
    echo "Error: One or more required environment variables are missing."
    echo "Required: NEW_RELIC_BROWSER_APPLICATION_ID, NEW_RELIC_LICENSE_KEY, NEW_RELIC_ACCOUNT_ID, NEW_RELIC_TRUST_KEY"
    exit 1
fi

# --- Replacement ---

# 1. Replace __APPLICATION_ID__
# Use a different delimiter (e.g., '#') for sed to avoid issues if the variable content contains '/'
# The 'g' flag ensures all occurrences on a line are replaced
sed -i "s#__APPLICATION_ID__#$NEW_RELIC_BROWSER_APPLICATION_ID#g" "$TARGET_FILE"

# 2. Replace __LICENSE_KEY__
sed -i "s#__LICENSE_KEY__#$NEW_RELIC_LICENSE_KEY#g" "$TARGET_FILE"

# 3. Replace __ACCOUNT_ID__
sed -i "s#__ACCOUNT_ID__#$NEW_RELIC_ACCOUNT_ID#g" "$TARGET_FILE"

# 4. Replace __TRUST_KEY__
sed -i "s#__TRUST_KEY__#$NEW_RELIC_TRUST_KEY#g" "$TARGET_FILE"

echo "Placeholders in $TARGET_FILE successfully replaced with environment variables."
