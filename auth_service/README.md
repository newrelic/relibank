# Relibank Auth Service

This service handles authentication for the Relibank application: it validates a user's email and password against the accounts database and returns a session token. It is built using Python with the FastAPI framework.

---

### 🚀 Key Features

* **Login Validation**: Authenticates a user by checking email/password against the `user_account` table in the shared accounts Postgres database.
* **Demo Token Issuance**: On successful login, returns a static demo token (`demo-token-12345`) rather than a signed JWT — this is a demo simplification, not production-grade session security (a real deployment would use bcrypt/argon2 password hashing and signed JWTs).
* **Resilient DB Connection**: Uses a `psycopg2` connection pool with retry/backoff (10 attempts) on startup so the service tolerates the Postgres container starting slightly later.
* **New Relic APM**: Instrumented via `newrelic-admin`, with distributed tracing enabled.

---

### 📦 API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/auth-service/login` | `POST` | Authenticates a user by email + password; returns `status`, `user_id`, `email`, and a demo `token`. |
| `/auth-service` | `GET` | Root health check, returns `"ok"`. |
| `/auth-service/health` | `GET` | Detailed health check, returns `{"status": "healthy", "service": "auth-service"}`. |

---

### 🔧 Configuration

#### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DB_HOST` | `accounts-db` | Postgres host for the accounts database. |
| `DB_NAME` | `accountsdb` | Postgres database name. |
| `DB_USER` | `postgres` | Postgres user. |
| `DB_PASSWORD` | — | Postgres password. |
| `NEW_RELIC_APP_NAME` | `"${APP_NAME} - Auth Service"` | New Relic APM application name. |
| `NEW_RELIC_LICENSE_KEY` | — | New Relic ingest license key. |
| `NEW_RELIC_ACCOUNT_ID` | — | New Relic account ID. |
| `NEW_RELIC_USER_API_KEY` | — | New Relic user API key (build-time). |
| `NEW_RELIC_DISTRIBUTED_TRACING_ENABLED` | `true` | Enables distributed tracing in the New Relic agent. |

---

### ⚙️ How to Run

This service is deployed as part of the larger **Relibank** application stack using Skaffold and Kubernetes.

1. **Ensure Prerequisites**: Make sure you have Docker Desktop (with Kubernetes enabled) or Minikube, Skaffold, kubectl, and Helm installed.

2. **Configure Environment**: From the root of the `relibank` repository, populate `skaffold.env` with the required secrets and configuration values.

3. **Start the Stack**: Run the following command from the root directory to build all images and deploy all services to your local Kubernetes cluster:

    ```bash
    skaffold dev
    ```

4. **Access the Service**: The container listens on port `5002`, but is forwarded locally to `http://localhost:5006` (port `5002` is already taken by `accounts-service`) — see `skaffold.yaml`'s `portForward` config.
