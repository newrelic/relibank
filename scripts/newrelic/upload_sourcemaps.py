"""
upload_sourcemaps.py
Uploads JS source maps to New Relic's Browser Source Maps API, discovered entirely over HTTP
from the live public site — no Docker/ACR/Azure access needed.

Flow:
  1. GET {PUBLIC_HOST}/.vite/manifest.json (Vite build manifest) to find every currently-served
     main-app JS chunk, including lazy-loaded route chunks that wouldn't appear in a plain HTML
     scrape. (React Router's SPA build only keeps this file around when `build.manifest` is
     exactly `true` in vite.config.ts — see the comment there. It always lands at the default
     `.vite/manifest.json` path; a custom filename gets deleted after build regardless.)
     Combined with a hardcoded list of the 4 microfrontends' JS paths (MICROFRONTEND_JS_FILES)
     — these build separately via plain `vite build` (lib/UMD mode, not the react-router
     plugin), so they never appear in the manifest above. Unlike the main app's chunks, their
     filenames are fixed/non-hashed and never change across builds.
  2. For each file, GET {PUBLIC_HOST}/<file>.map (the standard co-located sourcemap convention;
     `serve` already exposes it once the Vite build has `sourcemap: true`).
  3. POST each pair to New Relic's Source Maps API, keyed by the exact public javascriptUrl.

A failure on one file is logged and does not abort the batch. Because the microfrontends' URLs
never change between builds, re-uploading a map for one that's already current is expected to
happen on every run — a 409 response (New Relic's documented conflict for a javascriptUrl/
releaseName/releaseId combination that already exists) is treated as "already up to date," not
a real failure.

Required environment variables:
  NEW_RELIC_USER_API_KEY    New Relic user key (NRAK-...), used to authenticate the upload.
  NEW_RELIC_BROWSER_APP_ID  The target Browser application's entity/app ID.
  PUBLIC_HOST               Base URL the frontend is actually served from, e.g.
                            https://sandbox.relibankdemo.com (no trailing slash).
"""

import os
import sys

import requests

SOURCEMAPS_API = "https://sourcemaps.service.newrelic.com/v2/applications/{app_id}/sourcemaps"

# Microfrontends build separately (plain `vite build`, lib/UMD mode) and are never captured in
# the main app's Vite manifest. Their output filenames are fixed — see
# frontend_service/microfrontends/*/vite.config.ts's `lib.fileName`.
MICROFRONTEND_JS_FILES = [
    "microfrontends/ad-banner/ad-banner.js",
    "microfrontends/spending-chart/spending-chart.js",
    "microfrontends/spending-categories/spending-categories.js",
    "microfrontends/account-balance-trends/account-balance-trends.js",
]


def env_or_exit(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Error: required environment variable '{name}' is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def fetch_manifest(public_host: str) -> dict:
    url = f"{public_host}/.vite/manifest.json"
    print(f"--- Fetching build manifest: {url} ---", flush=True)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def js_files_from_manifest(manifest: dict) -> list[str]:
    files = sorted({
        entry["file"]
        for entry in manifest.values()
        if isinstance(entry, dict) and entry.get("file", "").endswith(".js")
    })
    print(f"--- Found {len(files)} JS file(s) in manifest ---", flush=True)
    for f in files:
        print(f"  {f}", flush=True)
    return files


def fetch_sourcemap(public_host: str, js_file: str) -> bytes | None:
    url = f"{public_host}/{js_file}.map"
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        print(f"  SKIP {js_file}: sourcemap not reachable at {url} ({resp.status_code})",
              flush=True)
        return None
    return resp.content


def upload_sourcemap(app_id: str, user_api_key: str, public_host: str,
                      js_file: str, map_bytes: bytes) -> str:
    """Returns "uploaded", "already_current" (409 — expected for fixed-URL microfrontends), or
    "failed"."""
    js_file_url = f"{public_host}/{js_file}"
    url = SOURCEMAPS_API.format(app_id=app_id)
    headers = {"Api-Key": user_api_key}
    data = {"javascriptUrl": js_file_url}
    files = {"sourcemap": (f"{js_file}.map", map_bytes, "application/json")}

    resp = requests.post(url, headers=headers, data=data, files=files, timeout=60)
    if resp.ok:
        print(f"  OK   {js_file_url}", flush=True)
        return "uploaded"

    if resp.status_code == 409:
        print(f"  SAME {js_file_url}: already up to date (409)", flush=True)
        return "already_current"

    print(f"  FAIL {js_file_url}: {resp.status_code} {resp.text[:500]}", file=sys.stderr,
          flush=True)
    return "failed"


def main() -> int:
    user_api_key = env_or_exit("NEW_RELIC_USER_API_KEY")
    app_id = env_or_exit("NEW_RELIC_BROWSER_APP_ID")
    public_host = env_or_exit("PUBLIC_HOST").rstrip("/")

    manifest = fetch_manifest(public_host)
    js_files = js_files_from_manifest(manifest) + MICROFRONTEND_JS_FILES

    if not js_files:
        print("No JS files found — nothing to upload.", file=sys.stderr, flush=True)
        return 1

    print(f"\n--- Uploading source maps for {len(js_files)} file(s) ---", flush=True)
    uploaded, already_current, skipped, failed = 0, 0, 0, 0
    for js_file in js_files:
        map_bytes = fetch_sourcemap(public_host, js_file)
        if map_bytes is None:
            skipped += 1
            continue
        result = upload_sourcemap(app_id, user_api_key, public_host, js_file, map_bytes)
        if result == "uploaded":
            uploaded += 1
        elif result == "already_current":
            already_current += 1
        else:
            failed += 1

    print(f"\n--- Done: {uploaded} uploaded, {already_current} already current, "
          f"{skipped} skipped (no sourcemap), {failed} failed ---", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
