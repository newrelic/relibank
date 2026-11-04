#!/usr/bin/env python3
"""
Close open New Relic issues that belong to a scenario, before the scenario starts.

Finds open issues whose alert condition or policy name matches the given selectors
(an NRQL query on NrAiIssue, matched by name in Python), then closes each one through
NerdGraph. At least one selector is required, so the script cannot close everything
in an account.

Usage:
    python utils/scripts/new_relic/close_issues.py \
        --api-key $NEW_RELIC_USER_KEY \
        --account-id $NEW_RELIC_ACCOUNT_ID \
        --condition-name "Payment Decline Rate" \
        --policy-name "ReliBank Platform"

    --dry-run          list the issues that would be closed, close nothing
    --list-mutations   print NerdGraph mutations that mention issues or incidents

Exits 1 if the lookup fails or any issue could not be closed, so workflows should
set continue-on-error. Results are appended to $GITHUB_STEP_SUMMARY when it is set.

A selector that matches no alert condition or policy in the account (a rename or typo)
does not change the exit code. It is printed as a ::warning:: annotation and added to
the step summary, so "nothing is open" is not confused with "the name is wrong".
"""

import argparse
import os
import sys

import requests

ENDPOINTS = {
    "staging": "https://nerd-graph.staging-service.nr-ops.net/graphql",
    "production": "https://api.newrelic.com/graphql",
}

NRQL_QUERY = """
query($accountId: Int!, $nrql: Nrql!) {
  actor { account(id: $accountId) { nrql(query: $nrql) { results } } }
}
"""

# NerdGraph has no "close issue" mutation; aiIssuesResolveIssue is the issue-level close.
# Signature checked against the schema, but not yet run against a real issue.
CLOSE_MUTATION = """
mutation($accountId: Int!, $issueId: ID!) {
  aiIssuesResolveIssue(accountId: $accountId, issueId: $issueId) {
    error
    result { issueId action }
  }
}
"""

# Names of the alert conditions and policies that exist in the account, used to tell
# "nothing is open" apart from "the selector no longer matches anything" (a rename or typo).
CONDITIONS_QUERY = """
query($accountId: Int!, $cursor: String) {
  actor { account(id: $accountId) { alerts { nrqlConditionsSearch(cursor: $cursor) {
    nextCursor
    nrqlConditions { name }
  } } } }
}
"""

POLICIES_QUERY = """
query($accountId: Int!, $cursor: String) {
  actor { account(id: $accountId) { alerts { policiesSearch(cursor: $cursor) {
    nextCursor
    policies { name }
  } } } }
}
"""

MUTATIONS_QUERY = """
{
  __type(name: "RootMutationType") {
    fields {
      name
      args { name type { name kind ofType { name } } }
      type { name kind }
    }
  }
}
"""


def nerdgraph(endpoint, api_key, query, variables=None):
    """POST a GraphQL query and return its data, raising on HTTP or GraphQL errors."""
    response = requests.post(
        endpoint,
        headers={"API-Key": api_key, "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise RuntimeError("; ".join(e.get("message", str(e)) for e in body["errors"]))
    return body["data"]


def build_issues_query(since):
    return (
        "SELECT latest(event) AS event, latest(title) AS title, "
        "latest(conditionNames) AS conditionNames, latest(policyNames) AS policyNames "
        f"FROM NrAiIssue FACET issueId SINCE {since} LIMIT MAX"
    )


def name_matches(names, selectors):
    """True if any selector is a case-insensitive substring of any name."""
    if isinstance(names, str):
        names = [names]
    return any(s.lower() in str(n).lower() for s in selectors for n in names or [])


def find_open_issues(endpoint, api_key, account_id, nrql, conditions, policies):
    """NrAiIssue gets an event per change (create, activate, close); an issue is open until its latest event is close.

    NRQL cannot filter the conditionNames and policyNames arrays, so names are matched here.
    Also returns the condition and policy names seen on any issue in the window, open or closed.
    """
    data = nerdgraph(endpoint, api_key, NRQL_QUERY, {"accountId": account_id, "nrql": nrql})
    rows = data["actor"]["account"]["nrql"]["results"]
    issues = []
    seen_conditions, seen_policies = set(), set()
    for row in rows:
        seen_conditions.update(row.get("conditionNames") or [])
        seen_policies.update(row.get("policyNames") or [])
        if str(row.get("event", "")).lower() == "close":
            continue
        if not (name_matches(row.get("conditionNames"), conditions)
                or name_matches(row.get("policyNames"), policies)):
            continue
        issues.append({
            "id": row.get("issueId") or row.get("facet"),
            "title": row.get("title", ""),
            "state": row.get("event", ""),
        })
    return issues, seen_conditions, seen_policies


def fetch_alert_names(endpoint, api_key, account_id, query, search_field, items_field):
    """All names from a paginated alerts search (conditions or policies)."""
    names, cursor = [], None
    while True:
        data = nerdgraph(endpoint, api_key, query, {"accountId": account_id, "cursor": cursor})
        page = data["actor"]["account"]["alerts"][search_field]
        names += [item["name"] for item in page[items_field]]
        cursor = page.get("nextCursor")
        if not cursor:
            return names


def unmatched_selectors(selectors, names):
    """Selectors that are not a substring of any name."""
    return [s for s in selectors if not name_matches(names, [s])]


def check_selectors(endpoint, api_key, account_id, conditions, policies, seen_conditions, seen_policies):
    """Warnings for selectors that match no alert condition or policy, so a rename is not silent.

    A selector counts as known if it matches a condition or policy defined in the account, or one
    seen on an issue in the lookup window (covers condition types the search does not list).
    Never raises: if the names cannot be fetched, it says so instead of guessing.
    """
    warnings = []
    for kind, selectors, query, search_field, items_field, seen in (
        ("condition", conditions, CONDITIONS_QUERY, "nrqlConditionsSearch", "nrqlConditions", seen_conditions),
        ("policy", policies, POLICIES_QUERY, "policiesSearch", "policies", seen_policies),
    ):
        if not selectors:
            continue
        try:
            names = fetch_alert_names(endpoint, api_key, account_id, query, search_field, items_field)
        except (requests.RequestException, RuntimeError, KeyError, TypeError) as e:
            warnings.append(f"Could not check that the {kind} selector(s) exist: {e}")
            continue
        for selector in unmatched_selectors(selectors, list(names) + list(seen)):
            warnings.append(
                f"No alert {kind} matches '{selector}'. It may have been renamed, so issues from "
                "this scenario will not be closed. Update the --"
                f"{kind}-name in this workflow."
            )
    return warnings


def close_issue(endpoint, api_key, account_id, issue_id):
    data = nerdgraph(endpoint, api_key, CLOSE_MUTATION, {"accountId": account_id, "issueId": issue_id})
    error = data["aiIssuesResolveIssue"].get("error")
    if error:
        raise RuntimeError(error)


def list_mutations(endpoint, api_key):
    data = nerdgraph(endpoint, api_key, MUTATIONS_QUERY)
    for field in data["__type"]["fields"]:
        if not any(word in field["name"].lower() for word in ("issue", "incident")):
            continue
        args = ", ".join(
            f"{a['name']}: {a['type'].get('name') or (a['type'].get('ofType') or {}).get('name')}"
            for a in field["args"]
        )
        print(f"{field['name']}({args}) -> {field['type'].get('name') or field['type']['kind']}")


def write_summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Close open New Relic issues for a scenario")
    parser.add_argument("--api-key", default=os.environ.get("NEW_RELIC_USER_KEY"))
    parser.add_argument("--account-id", type=int, default=os.environ.get("NEW_RELIC_ACCOUNT_ID"))
    parser.add_argument("--endpoint", choices=ENDPOINTS, default="production")
    parser.add_argument("--condition-name", action="append", default=[],
                        help="Alert condition name to match (substring, repeatable)")
    parser.add_argument("--policy-name", action="append", default=[],
                        help="Alert policy name to match (substring, repeatable)")
    parser.add_argument("--since", default="7 days ago", help="How far back to look for issues")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-mutations", action="store_true")
    args = parser.parse_args()

    if not args.api_key:
        sys.exit("Missing --api-key (or NEW_RELIC_USER_KEY)")
    endpoint = ENDPOINTS[args.endpoint]

    if args.list_mutations:
        list_mutations(endpoint, args.api_key)
        return 0

    if not args.account_id:
        sys.exit("Missing --account-id (or NEW_RELIC_ACCOUNT_ID)")
    if not (args.condition_name or args.policy_name):
        sys.exit("Give at least one --condition-name or --policy-name")

    nrql = build_issues_query(args.since)
    print(f"Looking for open issues with query: {nrql}")
    print(f"Matching conditions {args.condition_name} or policies {args.policy_name}")

    summary = ["### Close open New Relic issues"]
    try:
        issues, seen_conditions, seen_policies = find_open_issues(
            endpoint, args.api_key, args.account_id, nrql, args.condition_name, args.policy_name)
    except (requests.RequestException, RuntimeError) as e:
        print(f"Issue lookup failed: {e}")
        write_summary(summary + [f"Issue lookup failed: `{e}`"])
        return 1

    warnings = check_selectors(endpoint, args.api_key, args.account_id, args.condition_name,
                               args.policy_name, seen_conditions, seen_policies)
    for warning in warnings:
        print(f"::warning::{warning}")
    summary += [f"Warning: {w}" for w in warnings]

    if not issues:
        print("No open issues match.")
        write_summary(summary + ["No open issues matched."])
        return 0

    verb = "Would close" if args.dry_run else "Closing"
    print(f"{verb} {len(issues)} issue(s):")
    for issue in issues:
        print(f"  {issue['id']}  [{issue['state']}]  {issue['title']}")

    if args.dry_run:
        write_summary(summary + [f"Dry run: {len(issues)} open issue(s) would be closed."])
        return 0

    closed, failed = [], []
    for issue in issues:
        try:
            close_issue(endpoint, args.api_key, args.account_id, issue["id"])
            closed.append(issue)
        except (requests.RequestException, RuntimeError) as e:
            print(f"  Failed to close {issue['id']}: {e}")
            failed.append((issue, str(e)))

    summary.append(f"Closed {len(closed)} of {len(issues)} open issue(s).")
    for issue, error in failed:
        summary.append(f"- Failed to close `{issue['id']}` ({issue['title']}): `{error}`")
    write_summary(summary)
    print(f"Closed {len(closed)}, failed {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
