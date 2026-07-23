# Service README Baseline

Every service's README must include, at minimum, the following five sections:

1. **Purpose** — one paragraph on what the service does and its role in the system.
2. **Tech stack** — language/framework, key dependencies (DB, message broker, external APIs).
3. **Interface** — for REST services: an API endpoints table (path, method, purpose). For Kafka-only services: topics produced/consumed and message shape. For infra/collector services: what it's configured to do and what depends on it.
4. **Configuration** — environment variables/config, each with purpose, as a table:

   | Variable | Default | Description |
   | :--- | :--- | :--- |
   | `EXAMPLE_VAR` | `default-value` | What it's for |

5. **How to run** — local/skaffold instructions (can stay boilerplate/shared where genuinely identical across services, but must be present).

Service-specific sections (DB schema, demo scenarios, third-party config, etc.) are additive — they go beyond this baseline, not instead of it.
