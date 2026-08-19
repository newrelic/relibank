# Relibank Auth Service

This service is a core component of the **Relibank** FinServ application. Its sole
responsibility is authenticating users against the accounts database — checking email/password
credentials and returning a user identity for downstream services to use.

---

### 🚀 Key Features

* **RESTful API**: Exposes a single login endpoint consumed by the frontend.
* **PostgreSQL-Backed**: Validates credentials against the same `user_account` table used by
  `accounts-service`, via its own connection pool with startup retry/backoff.
* **New Relic Error Grouping**: Failed logins raise dedicated exception types
  (`FailedLoginUserNotFound`, `FailedLoginInvalidPassword`) purely so New Relic groups them
  distinctly, with actor context (IP, user agent, origin) attached for investigation.
* **Asynchronous Processing**: Built with FastAPI's async capabilities.

---

### 📦 API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/auth-service/login` | `POST` | Authenticates a user by email/password against the accounts database. |
| `/auth-service` | `GET` | Simple health check endpoint. |
| `/auth-service/health` | `GET` | Detailed health check endpoint that returns a status of `healthy`. |

---

### ⚙️ How to Run

This service is deployed as part of the larger **Relibank** application stack using Skaffold and
Kubernetes.

1. **Ensure Prerequisites**: Docker Desktop (with Kubernetes enabled) or Minikube, Skaffold,
   kubectl, and Helm.

2. **Configure Environment**: From the root of the `relibank` repository, populate `skaffold.env`
   with the required secrets and configuration values.

3. **Start the Stack**: Run the following command from the root directory to build all images and
   deploy all services to your local Kubernetes cluster:

    ```bash
    skaffold dev
    ```

    This will build the service images, deploy all Kubernetes resources, and set up port
    forwarding automatically.

4. **Test the Service**: Once deployed, send a `POST` request to
   `http://localhost:5006/auth-service/login` with an `email`/`password` body to authenticate a
   seeded user.

5. **Debug**:

    ```bash
    kubectl logs -n relibank deployment/auth-service --tail=50 -f
    ```
