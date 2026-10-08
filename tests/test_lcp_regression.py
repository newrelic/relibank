"""
Post-deployment LCP regression gate.

Fails if Largest Contentful Paint regresses on the color under test (TARGET_COLOR),
routed via the canary-ingress X-Test-Env header (see conftest.py::colored_driver) so
this can check a just-deployed, not-yet-cut-over color before traffic is switched to it.

Why this measures the browser directly instead of querying New Relic: browser RUM
events (PageView / PageViewTiming, which carry LCP) have no color/namespace dimension
- see nrql_color.py's own docstring. Once both colors are live, NRQL cannot tell which
color a given LCP sample came from, so there is no way to build a correct color-scoped
NRQL check here. Don't "fix" this into an NRQL query later; it would silently stop
testing what it claims to.

Native `largest-contentful-paint` Performance entries have been observed to come back
empty in headless Chrome even when real paint clearly happened (a known headless-mode
quirk) - unclear whether this reproduces on GitHub Actions' Linux Chrome. This test
prefers the native LCP entry when present and falls back to first-contentful-paint
otherwise, printing which one it used so the fallback is never silent.

Manual usage (test a particular color):
    TARGET_COLOR=green RELIBANK_URL=http://sandbox.relibankdemo.com \\
        python3 -m pytest tests/test_lcp_regression.py -v

TARGET_COLOR empty/unset targets whatever color is currently live.
"""
import json
import os
import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

RELIBANK_URL = os.getenv("RELIBANK_URL", "http://localhost:3000")

# Fixed, verified: LCP averages 1.3-2.7s (real RUM) / 1.5-1.9s (local) once the
# production build is served correctly; the regression this guards against measured
# 5-19s (Vite dev server running in place of the production build). 5s comfortably
# separates a real regression from ordinary network/CI jitter.
LCP_REGRESSION_THRESHOLD_MS = int(os.getenv("LCP_REGRESSION_THRESHOLD_MS", "5000"))

READ_PAINT_METRICS_JS = """
const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
const paints = performance.getEntriesByType('paint');
const nav = performance.getEntriesByType('navigation')[0] || {};
const lastLcp = lcpEntries[lcpEntries.length - 1] || null;
const fcp = paints.find(p => p.name === 'first-contentful-paint');
return JSON.stringify({
  nativeLcpMs: lastLcp ? lastLcp.startTime : null,
  firstContentfulPaintMs: fcp ? fcp.startTime : null,
  ttfbMs: nav.responseStart || null,
  domContentLoadedMs: nav.domContentLoadedEventEnd || null,
  loadEventEndMs: nav.loadEventEnd || null,
});
"""


def _read_paint_metrics(driver, label):
    data = json.loads(driver.execute_script(READ_PAINT_METRICS_JS))
    metric_ms = data["nativeLcpMs"]
    metric_name = "native LCP"
    if metric_ms is None:
        metric_ms = data["firstContentfulPaintMs"]
        metric_name = "first-contentful-paint (native LCP unavailable)"
    print(f"[{label}] {metric_name} = {metric_ms}ms | raw={data}")
    return metric_ms, metric_name


def _assert_metric_ok(label, metric_ms, metric_name):
    assert metric_ms is not None, (
        f"{label}: no LCP or first-contentful-paint entry recorded at all - "
        f"page likely failed to render, or browser instrumentation broke"
    )
    assert metric_ms < LCP_REGRESSION_THRESHOLD_MS, (
        f"{label}: {metric_name} = {metric_ms}ms, exceeds "
        f"LCP_REGRESSION_THRESHOLD_MS={LCP_REGRESSION_THRESHOLD_MS}ms"
    )


@pytest.mark.slow
def test_lcp_regression(colored_driver):
    driver = colored_driver

    # --- Login page (pre-auth) ---
    driver.get(RELIBANK_URL)
    WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "login-submit-btn")))
    time.sleep(2)  # let paint settle before reading
    login_metric_ms, login_metric_name = _read_paint_metrics(driver, "Login")

    # --- Dashboard (post-auth) ---
    driver.find_element(By.ID, "login-submit-btn").click()
    WebDriverWait(driver, 30).until(EC.url_contains("/dashboard"))
    time.sleep(2)
    dashboard_metric_ms, dashboard_metric_name = _read_paint_metrics(driver, "Dashboard (1st load)")

    # Flake-guard: reload once more (session persists, no re-login needed) and take
    # the max of the two readings - guards against one-off cold-start blips without
    # masking a real regression, since a genuine regression will be slow both times.
    driver.get(f"{RELIBANK_URL}/dashboard")
    time.sleep(2)
    dashboard_metric_ms_2, dashboard_metric_name_2 = _read_paint_metrics(driver, "Dashboard (2nd load)")
    if dashboard_metric_ms_2 is not None and (dashboard_metric_ms is None or dashboard_metric_ms_2 > dashboard_metric_ms):
        dashboard_metric_ms, dashboard_metric_name = dashboard_metric_ms_2, dashboard_metric_name_2

    _assert_metric_ok("Login", login_metric_ms, login_metric_name)
    _assert_metric_ok("Dashboard", dashboard_metric_ms, dashboard_metric_name)
