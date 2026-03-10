"""
Centralized New Relic Change Tracking Marker utility.

Sends a changeTrackingCreateEvent mutation to NerdGraph with support for all
categories, validated type mappings, category-specific fields, and custom attributes.

Entity resolution uses NerdGraph entitySearch (domain + name substring match).
If multiple entities are returned the script prints a table and exits — no marker
is created for ambiguous results.

Usage (DEPLOYMENT via APM entity):
    python utils/scripts/new_relic/send_change_tracking_marker.py \
        --api-key $NR_USER_API_KEY \
        --account-id $NR_ACCOUNT_ID \
        --app-name "My Service" \
        --entity-domain APM \
        --category DEPLOYMENT \
        --type ROLLING \
        --version v1.2.3 \
        --user devops_automation \
        --short-description "Deploy new image" \
        --custom-attribute environment=production \
        --custom-attribute team=payments

Usage (FEATURE_FLAG via BROWSER entity):
    python utils/scripts/new_relic/send_change_tracking_marker.py \
        --api-key $NR_USER_API_KEY \
        --account-id $NR_ACCOUNT_ID \
        --app-name "Customer Portal" \
        --entity-domain BROWSER \
        --category FEATURE_FLAG \
        --type BASIC \
        --feature-flag-id my.feature.flag \
        --user devops_automation \
        --short-description "Enable feature flag" \
        --custom-attribute environment=production
"""

import argparse
import json
import os
import secrets
import sys

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENDPOINTS = {
    "staging": "https://nerd-graph.staging-service.nr-ops.net/graphql",
    "production": "https://api.newrelic.com/graphql",
}

# Maps each category to its allowed types and any required extra fields.
CATEGORY_TYPE_MAP = {
    "DEPLOYMENT": {
        "types": {"BASIC", "BLUE_GREEN", "CANARY", "ROLLING", "SHADOW"},
        "required_fields": ["version"],
    },
    "DEPLOYMENT_LIFECYCLE": {
        "types": {
            "ARTIFACT_COPY",
            "ARTIFACT_DELETION",
            "ARTIFACT_DEPLOYMENT",
            "ARTIFACT_MOVE",
            "BUILD_DELETION",
            "BUILD_PROMOTION",
            "BUILD_UPLOAD",
            "IMAGE_DELETION",
            "IMAGE_PROMOTION",
            "IMAGE_PUSH",
            "RELEASE_BUNDLE_CREATION",
            "RELEASE_BUNDLE_DELETION",
            "RELEASE_BUNDLE_SIGN",
        },
        "required_fields": [],
    },
    "FEATURE_FLAG": {
        "types": {"BASIC"},
        "required_fields": ["feature_flag_id"],
    },
    "BUSINESS_EVENT": {
        "types": {"CONVENTION", "MARKETING_CAMPAIGN", "OTHER"},
        "required_fields": [],
    },
    "OPERATIONAL": {
        "types": {"CRASH", "OTHER", "SCHEDULED_MAINTENANCE_PERIOD", "SERVER_REBOOT"},
        "required_fields": [],
    },
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    category_help_lines = []
    for cat, meta in CATEGORY_TYPE_MAP.items():
        types_str = ", ".join(sorted(meta["types"]))
        req_flags = " ".join(f"--{field.replace('_', '-')}" for field in meta["required_fields"])
        req = f" [requires: {req_flags}]" if req_flags else ""
        category_help_lines.append(f"  {cat}: {types_str}{req}")
    category_help = "\n".join(category_help_lines)

    parser = argparse.ArgumentParser(
        description="Send a New Relic change tracking marker via NerdGraph.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"Category → allowed types:\n{category_help}",
    )

    # Authentication
    auth = parser.add_argument_group("Authentication")
    auth.add_argument(
        "--api-key",
        default=os.environ.get("NR_USER_API_KEY"),
        help="New Relic User API key (env: NR_USER_API_KEY)",
    )
    auth.add_argument(
        "--account-id",
        default=os.environ.get("NR_ACCOUNT_ID"),
        help="New Relic account ID (env: NR_ACCOUNT_ID)",
    )
    auth.add_argument(
        "--environment",
        choices=["staging", "production"],
        default="production",
        help="NerdGraph endpoint environment (default: production)",
    )

    # Entity resolution
    entity = parser.add_argument_group("Entity resolution (one required)")
    entity_group = entity.add_mutually_exclusive_group(required=True)
    entity_group.add_argument(
        "--entity-guid",
        help="Entity GUID directly (skips entity search)",
    )
    entity_group.add_argument(
        "--app-name",
        help="App name substring for entity search: name LIKE '%%<name>'",
    )
    # Valid entity domains. Extend this list as new domain types are onboarded.
    # Current supported values: APM, BROWSER
    entity.add_argument(
        "--entity-domain",
        choices=["APM", "BROWSER"],
        default="APM",
        help="Entity domain to filter search results (default: APM)",
    )

    # Core event fields
    event = parser.add_argument_group("Event core fields")
    event.add_argument(
        "--category",
        required=True,
        choices=list(CATEGORY_TYPE_MAP.keys()),
        help="Change tracking category",
    )
    event.add_argument(
        "--type",
        required=True,
        dest="event_type",
        help="Change tracking type (must be valid for the chosen category)",
    )
    event.add_argument("--user", required=True, help="User or automation identity")
    event.add_argument(
        "--short-description", required=True, help="Short description of the event"
    )
    event.add_argument("--description", default="", help="Detailed description")
    event.add_argument("--group-id", default="", help="Group/ticket identifier")
    event.add_argument(
        "--timestamp",
        default="",
        help="ISO8601 or epoch ms timestamp (defaults to now)",
    )

    # DEPLOYMENT fields
    deployment = parser.add_argument_group("DEPLOYMENT category fields")
    deployment.add_argument(
        "--version",
        help="Version string (required when --category DEPLOYMENT)",
    )
    deployment.add_argument(
        "--commit",
        default="",
        help="Commit hash (auto-generated if omitted)",
    )
    deployment.add_argument("--changelog", default="", help="Changelog text")
    deployment.add_argument("--deep-link", default="", help="Deep link URL")

    # FEATURE_FLAG fields
    ff = parser.add_argument_group("FEATURE_FLAG category fields")
    ff.add_argument(
        "--feature-flag-id",
        dest="feature_flag_id",
        help="Feature flag ID (required when --category FEATURE_FLAG)",
    )
    ff.add_argument("--provider", default="", help="Feature flag provider name")

    # Custom attributes
    parser.add_argument(
        "--custom-attribute",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        dest="custom_attributes",
        help="Custom attribute in KEY=VALUE format; repeatable",
    )

    return parser


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_args(args: argparse.Namespace) -> None:
    """Enforce category/type compatibility and required field rules."""
    meta = CATEGORY_TYPE_MAP[args.category]

    if args.event_type not in meta["types"]:
        valid = ", ".join(sorted(meta["types"]))
        print(
            f"Error: --type '{args.event_type}' is not valid for --category '{args.category}'.\n"
            f"Valid types for {args.category}: {valid}",
            file=sys.stderr,
        )
        sys.exit(1)

    for field in meta["required_fields"]:
        if not getattr(args, field, None):
            flag = f"--{field.replace('_', '-')}"
            print(
                f"Error: {flag} is required when --category is '{args.category}'.",
                file=sys.stderr,
            )
            sys.exit(1)

    if not args.api_key:
        print(
            "Error: --api-key is required (or set NR_USER_API_KEY env var).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.account_id and args.app_name:
        print(
            "Error: --account-id is required when using --app-name (or set NR_ACCOUNT_ID env var).",
            file=sys.stderr,
        )
        sys.exit(1)



# ---------------------------------------------------------------------------
# Entity GUID lookup
# ---------------------------------------------------------------------------


def get_entity_guid(api_key: str, account_id: str, app_name: str, entity_domain: str, environment: str) -> str:
    """Entity search query to resolve entity GUID by account, domain, and app name substring."""
    print(f"Looking up entity GUID for app name containing '{app_name}' (domain: {entity_domain})...")

    search_query = f"accountId={account_id} AND domain='{entity_domain}' AND name LIKE '%{app_name}%'"

    query = f"""
    {{
        actor {{
            entitySearch(query: "{search_query}") {{
                results {{
                    entities {{
                        entityType
                        name
                        guid
                    }}
                }}
            }}
        }}
    }}
    """

    endpoint = ENDPOINTS[environment]
    headers = {"Content-Type": "application/json", "API-Key": api_key}
    response = requests.post(endpoint, headers=headers, json={"query": query})

    if response.status_code != 200:
        raise RuntimeError(f"NerdGraph entity search failed with status {response.status_code}: {response.text}")

    data = response.json()
    entities = data["data"]["actor"]["entitySearch"]["results"]["entities"]

    if not entities:
        raise RuntimeError(f"No entity found matching: {search_query}")

    if len(entities) > 1:
        print("Error: entity search returned multiple results. Narrow --app-name to match exactly one entity.", file=sys.stderr)
        print(f"{'NAME':<50} {'TYPE':<20} {'GUID'}", file=sys.stderr)
        print("-" * 90, file=sys.stderr)
        for e in entities:
            print(f"{e['name']:<50} {e['entityType']:<20} {e['guid']}", file=sys.stderr)
        sys.exit(1)

    guid = entities[0]["guid"]
    print(f"Resolved entity GUID: {guid}  ({entities[0]['name']})")
    return guid


# ---------------------------------------------------------------------------
# Mutation builders
# ---------------------------------------------------------------------------


def _fake_commit() -> str:
    return secrets.token_hex(20)


def build_deployment_fields(args: argparse.Namespace) -> str:
    """Returns the categoryFields block for DEPLOYMENT mutations."""
    commit = args.commit or _fake_commit()
    lines = [f'commit: "{commit}"', f'version: "{args.version}"']
    if args.changelog:
        lines.append(f'changelog: "{args.changelog}"')
    if args.deep_link:
        lines.append(f'deepLink: "{args.deep_link}"')
    inner = ", ".join(lines)
    return f"deployment: {{ {inner} }}"


def build_feature_flag_fields(args: argparse.Namespace) -> str:
    """Returns the categoryFields block for FEATURE_FLAG mutations."""
    lines = [f'featureFlagId: "{args.feature_flag_id}"']
    if args.provider:
        lines.append(f'provider: "{args.provider}"')
    inner = ", ".join(lines)
    return f"featureFlag: {{ {inner} }}"


def _build_custom_attributes_block(custom_attributes: list[str]) -> str:
    """Parse KEY=VALUE pairs and render as a GraphQL inline object."""
    if not custom_attributes:
        return ""
    pairs = []
    for item in custom_attributes:
        if "=" not in item:
            print(f"Warning: skipping malformed --custom-attribute '{item}' (expected KEY=VALUE)", file=sys.stderr)
            continue
        key, _, value = item.partition("=")
        pairs.append(f'{key.strip()}: "{value.strip()}"')
    if not pairs:
        return ""
    return "customAttributes: { " + ", ".join(pairs) + " }"


def build_mutation_payload(guid: str, args: argparse.Namespace) -> str:
    """Assembles the full changeTrackingCreateEvent mutation string."""
    # category fields block
    if args.category == "DEPLOYMENT":
        category_fields_block = f"categoryFields: {{ {build_deployment_fields(args)} }}"
    elif args.category == "FEATURE_FLAG":
        category_fields_block = f"categoryFields: {{ {build_feature_flag_fields(args)} }}"
    else:
        category_fields_block = ""

    # optional top-level fields
    optional_lines = []
    if args.description:
        optional_lines.append(f'description: "{args.description}"')
    if args.group_id:
        optional_lines.append(f'groupId: "{args.group_id}"')
    if args.timestamp:
        optional_lines.append(f'timestamp: "{args.timestamp}"')

    custom_attr_block = _build_custom_attributes_block(args.custom_attributes)
    if custom_attr_block:
        optional_lines.append(custom_attr_block)

    optional_str = "\n          ".join(optional_lines)

    mutation = f"""
    mutation {{
      changeTrackingCreateEvent(
        changeTrackingEvent: {{
          categoryAndTypeData: {{
            kind: {{ category: "{args.category}", type: "{args.event_type}" }}
            {category_fields_block}
          }}
          user: "{args.user}"
          shortDescription: "{args.short_description}"
          {optional_str}
          entitySearch: {{ query: "id = '{guid}'" }}
        }}
      ) {{
        changeTrackingEvent {{
          changeTrackingId
        }}
      }}
    }}
    """
    return mutation


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def send_change_tracking_event(api_key: str, environment: str, payload: str) -> dict:
    """POSTs the mutation to NerdGraph; raises on non-200."""
    endpoint = ENDPOINTS[environment]
    headers = {"Content-Type": "application/json", "API-Key": api_key}
    print(f"Sending change tracking event to {endpoint}...")
    response = requests.post(endpoint, headers=headers, json={"query": payload})

    if response.status_code != 200:
        raise RuntimeError(
            f"NerdGraph mutation failed with status {response.status_code}: {response.text}"
        )

    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)

    # Resolve entity GUID
    if args.entity_guid:
        guid = args.entity_guid
        print(f"Using provided entity GUID: {guid}")
    else:
        guid = get_entity_guid(args.api_key, args.account_id, args.app_name, args.entity_domain, args.environment)

    payload = build_mutation_payload(guid, args)
    print(f"\nMutation payload:\n{payload}")

    result = send_change_tracking_event(args.api_key, args.environment, payload)

    tracking_id = (
        result.get("data", {})
        .get("changeTrackingCreateEvent", {})
        .get("changeTrackingEvent", {})
        .get("changeTrackingId", "unknown")
    )
    print(f"\nChange tracking event created. ID: {tracking_id}")


if __name__ == "__main__":
    main()
