# Scenarios

**Authoring / modifying scenarios:** see **[SCENARIO_AUTHORING.md](SCENARIO_AUTHORING.md)** — the
full guide to the three control mechanisms, the config → endpoints → consumer → docs → workflow
pattern, chaos experiments, and testing. (Builder-mode / demo-engineering team.)

**Operating scenarios during a demo:** toggle them from the scenario-runner UI at
`http://localhost:8000/scenario-runner/home`, or via the `/scenario-runner/api/*` endpoints. The
scheduled `.github/workflows/flow-*.yml` workflows cycle them automatically.

## Request-header quick trigger

Several FastAPI services honor per-request demo headers via `utils/process_headers.py`:

| Header | Effect |
|--------|--------|
| `extra-transaction-time` | Blocking `time.sleep()` for that many seconds (adds latency) |
| `error` | Raises the given 4xx/5xx HTTP status |

Example — inject latency + an error, targeting bill-pay:

```
extra-transaction-time: 0.5
error: 500
```

## Runbooks

- Database connection-pool stress: [DATABASE_POOL_SCENARIO.md](DATABASE_POOL_SCENARIO.md)
