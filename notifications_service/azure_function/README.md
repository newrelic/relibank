# notify_user_trigger — New Relic instrumentation

This Function App reports to New Relic two ways:

- **Infra (already in place)**: Azure Monitor cloud-integration polling, giving golden signals
  (invocation count, execution time, memory) as an infra entity.
- **APM (this directory)**: the New Relic Python agent, giving an APM entity with distributed
  traces and error detail — see `function_app.py`'s `newrelic.agent.initialize()` /
  `register_application()`.

## Why the Python agent, not the alternatives

- **OpenTelemetry SDK** (the commented-out `azure-monitor-opentelemetry` line in
  `requirements.txt`): more manual instrumentation work for no clear benefit on this single
  HTTP-triggered function — left commented as a documented alternative, not picked.
- **Cloud-integration only**: already in place, but infra-only — no APM transactions, traces, or
  error detail. The Python agent is additive to this, not a replacement.
