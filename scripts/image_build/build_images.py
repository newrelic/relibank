"""
build_images.py
Content-addressed image builder for Azure Container Registry.

Mirrors the logic in demogorgon/applications/microservices-demo/utils/image_build/build_images.py
but targets ACR instead of ECR, and uses :{color} as the deployment tag instead of :latest.

Cache strategy:
  - SHA256 hash of the source directory → used as a stable cache tag in ACR
  - On each build:
      1. Hash the hash_dir for this service
      2. Check ACR for :{sha} tag
         a. SHA exists AND :{color} already points to the same digest → SKIP (no change)
         b. SHA exists but :{color} is stale                          → RETAG only (no build)
         c. SHA not found                                             → full build + push both tags
  - --force-rebuild bypasses the cache check entirely

Usage:
  python build_images.py \\
    --build-context ./frontend_service \\
    --hash-dir ./frontend_service \\
    --service frontend-service \\
    --target-color blue \\
    --acr-server relibanksandbox.azurecr.io \\
    --nr-user-key ... --nr-license-key ... --nr-account-id ... \\
    --agent-type newrelic --nr-region US \\
    --app-name ReliBank
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Directory hashing
# ---------------------------------------------------------------------------

def calculate_directory_sha256(directory_path: str, block_size: int = 65536) -> str:
    """SHA-256 hash of an entire directory, deterministic (sorted file order)."""
    path = Path(directory_path)
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: '{directory_path}'")

    print(f"\n--- Hashing {directory_path} ---", flush=True)
    sha256 = hashlib.sha256()

    all_files = sorted([p for p in path.rglob("*") if p.is_file()])
    relative_files = [p.relative_to(path) for p in all_files]

    for i, rel_path in enumerate(relative_files):
        print(f"  [{i + 1}/{len(relative_files)}] {rel_path}", flush=True)
        sha256.update(str(rel_path).encode("utf-8"))
        try:
            with open(path / rel_path, "rb") as f:
                while chunk := f.read(block_size):
                    sha256.update(chunk)
        except OSError as e:
            print(f"  Warning: could not read '{rel_path}': {e}", file=sys.stderr, flush=True)

    digest = sha256.hexdigest()
    print(f"  Digest: {digest}", flush=True)
    return digest


# ---------------------------------------------------------------------------
# ACR helpers
# ---------------------------------------------------------------------------

def acr_name_from_server(acr_server: str) -> str:
    """relibanksandbox.azurecr.io → relibanksandbox"""
    return acr_server.split(".")[0]


def check_acr_tag_exists(acr_name: str, repo: str, tag: str) -> bool:
    """Returns True if the tag exists in ACR."""
    print(f"\n--- Checking ACR for tag '{tag}' in {acr_name}/{repo} ---", flush=True)
    cmd = [
        "az", "acr", "repository", "show-tags",
        "--name", acr_name,
        "--repository", repo,
        "--output", "json",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        tags = json.loads(result.stdout)
        if tag in tags:
            print(f"  MATCH: tag '{tag}' exists.", flush=True)
            return True
        print(f"  NO MATCH: tag '{tag}' not found.", flush=True)
        return False
    except subprocess.CalledProcessError as e:
        if "RepositoryNotFound" in e.stderr or "not found" in e.stderr.lower():
            print(f"  Repository not found — will build.", flush=True)
            return False
        raise


def get_image_digest(acr_name: str, repo: str, tag: str) -> Optional[str]:
    """Returns the manifest digest (sha256:...) for a given tag, or None."""
    cmd = [
        "az", "acr", "repository", "show",
        "--name", acr_name,
        "--image", f"{repo}:{tag}",
        "--query", "digest",
        "--output", "tsv",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        digest = result.stdout.strip()
        return digest if digest and digest != "None" else None
    except subprocess.CalledProcessError:
        return None


def retag_in_acr(acr_server: str, acr_name: str, repo: str, source_tag: str, target_tag: str):
    """
    Re-tag an existing image in ACR without re-uploading layers.
    Uses 'az acr import' with the same source/dest registry — ACR performs
    a manifest copy with no data transfer when source == destination.
    """
    print(f"\n--- Retagging {repo}:{source_tag} → :{target_tag} ---", flush=True)
    cmd = [
        "az", "acr", "import",
        "--name", acr_name,
        "--source", f"{acr_server}/{repo}:{source_tag}",
        "--image", f"{repo}:{target_tag}",
        "--force",
    ]
    subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)
    print(f"  Retag successful.", flush=True)


# ---------------------------------------------------------------------------
# Docker build + push
# ---------------------------------------------------------------------------

def build_and_push_image(
    build_context: str,
    dockerfile: Optional[str],
    image_sha: str,
    acr_server: str,
    acr_name: str,
    repo: str,
    target_color: str,
    build_args: dict,
):
    full_uri = f"{acr_server}/{repo}"
    tag_color = f"{full_uri}:{target_color}"
    tag_sha = f"{full_uri}:{image_sha}"

    print(f"\n--- Building {repo} ---", flush=True)

    build_cmd = ["docker", "build", "-t", tag_color, build_context, "--no-cache"]
    if dockerfile:
        build_cmd += ["--file", dockerfile]
    for k, v in build_args.items():
        if v:
            build_cmd += ["--build-arg", f"{k}={v}"]

    subprocess.run(build_cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)

    print(f"\n--- Tagging as SHA: {tag_sha} ---", flush=True)
    subprocess.run(["docker", "tag", tag_color, tag_sha], check=True)

    for tag in [tag_color, tag_sha]:
        print(f"Pushing {tag}...", flush=True)
        subprocess.run(["docker", "push", tag], check=True, stdout=sys.stdout, stderr=sys.stderr)

    print(f"\nSuccessfully pushed {repo} ({target_color} + {image_sha[:12]}...).", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build and push Docker images to ACR with content-based caching.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required
    parser.add_argument("--build-context", dest="build_context", required=True,
                        help="Docker build context path (same as 'context:' in skaffold.yaml)")
    parser.add_argument("--service",       dest="service_name",  required=True,
                        help="ACR repository / image name (e.g. frontend-service)")
    parser.add_argument("--target-color",  dest="target_color",  required=True,
                        help="Deployment color — blue or green")
    parser.add_argument("--acr-server",    dest="acr_server",    required=True,
                        help="ACR login server (e.g. relibanksandbox.azurecr.io)")

    # Optional build path
    parser.add_argument("--dockerfile", dest="dockerfile", default=None,
                        help="Path to Dockerfile when it is NOT at the root of build-context")
    parser.add_argument("--hash-dir",   dest="hash_dir",   default=None,
                        help="Directory to hash for the cache key. Defaults to --build-context. "
                             "Use the service source dir when build-context is the repo root ('.').")

    # New Relic / agent
    parser.add_argument("--nr-user-key",       dest="nr_user_key",       default="")
    parser.add_argument("--nr-license-key",    dest="nr_license_key",    default="")
    parser.add_argument("--nr-account-id",     dest="nr_account_id",     default="")
    parser.add_argument("--nr-browser-app-id", dest="nr_browser_app_id", default="")
    parser.add_argument("--nr-trust-key",      dest="nr_trust_key",      default="")
    parser.add_argument("--agent-type",        dest="agent_type",        default="newrelic")
    parser.add_argument("--nr-region",         dest="nr_region",         default="US")

    # App
    parser.add_argument("--app-name", dest="app_name", default="ReliBank")

    # Stripe (consumed by bill-pay-service Dockerfile ARGs; harmless for other services)
    parser.add_argument("--stripe-secret-key",      dest="stripe_secret_key",      default="")
    parser.add_argument("--stripe-publishable-key", dest="stripe_publishable_key", default="")

    # Cache control
    parser.add_argument("--force-rebuild", action="store_true",
                        help="Ignore cached SHA tag and always do a full build.")

    args = parser.parse_args()

    acr_name = acr_name_from_server(args.acr_server)
    hash_dir = args.hash_dir if args.hash_dir else args.build_context

    # Normalize paths: strip leading './' (relative) but leave absolute paths intact
    if hash_dir.startswith("./"):
        hash_dir = hash_dir[2:] or "."

    try:
        # 1. Hash the source directory
        directory_sha = calculate_directory_sha256(hash_dir)

        # 2. Cache check (skip if --force-rebuild)
        if not args.force_rebuild:
            sha_exists = check_acr_tag_exists(acr_name, args.service_name, directory_sha)

            if sha_exists:
                color_digest = get_image_digest(acr_name, args.service_name, args.target_color)
                sha_digest   = get_image_digest(acr_name, args.service_name, directory_sha)

                if color_digest and color_digest == sha_digest:
                    print(
                        f"\nCode unchanged. '{args.target_color}' already points to current SHA. Skipping build.",
                        flush=True,
                    )
                    sys.exit(0)
                else:
                    print(
                        f"\nSHA found in ACR but '{args.target_color}' is stale. Retagging only — no rebuild.",
                        flush=True,
                    )
                    retag_in_acr(args.acr_server, acr_name, args.service_name, directory_sha, args.target_color)
                    sys.exit(0)
            else:
                print("\nNo cached SHA found. Performing full build.", flush=True)
        else:
            print("\n--- Force Rebuild: skipping cache check ---", flush=True)

        # 3. Full build + push
        build_args = {
            "NEW_RELIC_USER_API_KEY":          args.nr_user_key,
            "NEW_RELIC_LICENSE_KEY":           args.nr_license_key,
            "NEW_RELIC_ACCOUNT_ID":            args.nr_account_id,
            "NEW_RELIC_BROWSER_APPLICATION_ID": args.nr_browser_app_id,
            "NEW_RELIC_TRUST_KEY":             args.nr_trust_key,
            "AGENT_TYPE":                      args.agent_type,
            "NEW_RELIC_REGION":                args.nr_region,
            "APP_NAME":                        args.app_name,
            "STRIPE_SECRET_KEY":               args.stripe_secret_key,
            "STRIPE_PUBLISHABLE_KEY":          args.stripe_publishable_key,
        }

        build_and_push_image(
            build_context=args.build_context,
            dockerfile=args.dockerfile,
            image_sha=directory_sha,
            acr_server=args.acr_server,
            acr_name=acr_name,
            repo=args.service_name,
            target_color=args.target_color,
            build_args=build_args,
        )

    except FileNotFoundError as e:
        print(e, file=sys.stderr, flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
