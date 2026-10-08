"""Color-directed NRQL helper.

relibank encodes the deploy color in the Kubernetes namespace (``relibank-<color>``), which
``nri-metadata-injection`` stamps onto APM/Log/Span telemetry — under an event-type-specific
attribute name. This is the relibank analog of demogorgon filtering NRQL on the color-bearing
pod/host name.

Usage — drop it into a ``WHERE`` so the query reads naturally:

    f"... AND db.pool_id IS NOT NULL {color_filter('Transaction')} SINCE 10 minutes ago"

It renders to ``AND `namespaceName` = 'relibank-blue'`` when a color is directed, or an empty
string when ``TARGET_COLOR`` is unset (e.g. the scheduled cron resolving to the active color
with no directive) — so the query stays env-level.

Not all telemetry carries the namespace: the mssql-collector ``Metric`` stream, browser
events (``PageView``/``BrowserInteraction``, shared browser app), and ``Log`` have no
namespace dimension, so they remain color-blind by necessity — do not use this helper for
them (``color_filter('Log')`` etc. is a safe, permanent no-op below, not just "not yet wired
up").
"""
import os

# (attribute, value-template) carrying the color, per NR event type. The value template is
# formatted with the effective color.
#   - APM Transaction/TransactionError: the ``deploy.color`` custom attribute (value = the bare
#     color, e.g. "blue"), stamped by utils/process_headers.py. nri-metadata-injection does NOT
#     put a namespace on APM events, so this custom attribute is how APM is color-scoped.
#   - Span: the k8s namespace nri-metadata-injection stamps (value = "relibank-<color>") ->
#     k8s.namespace.name.
# Log is deliberately absent: relibank services ship logs via the APM agent's own log
# forwarding (newrelic.source = "logs.APM"), not the nri-metadata-injection/Fluent Bit
# pipeline, so `namespace_name` is never stamped on Log records — a namespace filter there
# would silently zero every result. Metric (mssql collector) and browser PageView also have no
# color dimension. All three are intentionally absent -> color_filter() is a no-op for them
# (they stay env-level).
_COLOR_DIM = {
    "Transaction": ("deploy.color", "{color}"),
    "TransactionError": ("deploy.color", "{color}"),
    "Span": ("k8s.namespace.name", "relibank-{color}"),
}


def effective_color():
    """The color the run is directed at ('' = undirected / active, no filtering)."""
    return os.getenv("TARGET_COLOR", "").strip()


def color_filter(event_type):
    """NRQL ``AND`` fragment scoping to the effective color's namespace, or '' if undirected.

    Designed to sit inline after an existing predicate, e.g. ``... IS NOT NULL {color_filter('Span')}``.
    """
    color = effective_color()
    dim = _COLOR_DIM.get(event_type)
    if not color or not dim:
        return ""
    attr, value_tmpl = dim
    return f"AND `{attr}` = '{value_tmpl.format(color=color)}'"
