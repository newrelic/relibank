# Relibank Accounts Service

This service is a core component of the **Relibank** FinServ application. It acts as a dedicated microservice for managing user and account data, using a **PostgreSQL** database as its backend. This service is designed to be highly secure and reliable, providing an API for user and account management.

---

### 🚀 Key Features

* **RESTful API**: Exposes a RESTful API for managing user accounts, checking accounts, savings accounts, and credit accounts.

* **PostgreSQL Database**: The service is tightly integrated with a PostgreSQL database, ensuring all account and user data is consistently and reliably stored.

* **Data Validation**: It uses Pydantic models to validate incoming API requests and ensure the data conforms to the required schema before being processed.

* **Stripe Integration**: Each user account is linked to a Stripe customer and payment method, enabling payment processing via the Stripe API.

---

### 📦 API Endpoints

The service exposes the following API endpoints, which are designed to be consumed by other microservices or the customer portal.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/users` | `POST` | Creates a new user account in the database. |
| `/users/{user_id}` | `GET` | Retrieves a single user's information by their unique ID. |
| `/accounts/{user_id}` | `GET` | Retrieves all accounts (checking, savings, and credit) associated with a specific user. |
| `/accounts/{user_id}` | `POST` | Creates a new account (checking, savings, or credit) and links it to a user. |
| `/browser-user` | `GET` | Returns a user ID for New Relic Browser tracking (random or header-based). |
| `/health` | `GET` | A health check endpoint that returns a status of `healthy`. |

---

## 🔍 New Relic APM User Tracking

### Overview
The accounts service (and all backend services) automatically extract and track user IDs from the `x-browser-user-id` header for New Relic APM monitoring. This enables end-to-end user tracking from browser sessions through all backend service calls.

### Browser User Endpoint

**Endpoint**: `GET /accounts-service/browser-user`

**Purpose**: Assigns a user ID for New Relic Browser session tracking.

**User ID Assignment Priority**:
1. **Header Override**: If `x-browser-user-id` header is present and matches a valid user in the database, returns that ID
2. **Random Selection**: Otherwise, returns a random user ID from the `user_account` table

**Response Format**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "header"  // or "random"
}
```

**Example Usage**:
```bash
# Random assignment
curl http://localhost:5002/accounts-service/browser-user

# Header override (for testing)
curl -H "x-browser-user-id: 550e8400-e29b-41d4-a716-446655440000" \
     http://localhost:5002/accounts-service/browser-user
```

### APM User ID Tracking

**Implementation**: All request handlers call `process_headers()` which:
1. Extracts the `x-browser-user-id` header
2. Calls `newrelic.agent.set_user_id()` to associate the request with the user
3. Logs the user ID for debugging

**Header Propagation**: The service propagates the `x-browser-user-id` header to downstream services:
- Calls to `transaction-service` include the header
- Helper function `get_propagation_headers(request)` extracts headers for propagation

**New Relic Integration**:
- User IDs appear in New Relic APM transactions
- Enables filtering and grouping by user in New Relic UI
- Provides end-to-end tracing from browser to backend services

**Logging**:
```
[APM User Tracking] Set user ID: 550e8400-e29b-41d4-a716-446655440000
```

---

---

## 💳 Stripe Integration

Each seeded `user_account` row is pre-linked to a real Stripe customer and payment method, so the app can process payments out-of-the-box after a fresh `docker compose up`.

### User Account Stripe Fields

| Column | Description |
| :--- | :--- |
| `stripe_customer_id` | Stripe Customer object ID (e.g. `cus_UDJUKtOkn6XoOB`) |
| `stripe_payment_method_id` | Stripe PaymentMethod object ID (e.g. `pm_1TExyFFGyca1lOb8OuCAwtEn`) |
| `stripe_payment_method_name` | Card brand token used in Stripe test mode (e.g. `pm_card_visa`) |

### Seed Data

All 43 test users in `accounts_service/postgres/init.sql` have Stripe IDs pre-populated. The IDs were created externally in Stripe and embedded directly into the seed `INSERT` so no additional setup is required.

> **Note:** New users created via `POST /users` will have `NULL` values for all three Stripe fields. Before card payments will work for a newly created user, you must create a Stripe Customer and attach a PaymentMethod to them via the Stripe API, then update the corresponding `user_account` row with the resulting `stripe_customer_id`, `stripe_payment_method_id`, and `stripe_payment_method_name`.

---

### ⚙️ How to Run

This service is designed to be run using Docker Compose as part of the larger **Relibank** application stack.

1.  **Ensure Docker Compose is Installed**: Make sure you have Docker and Docker Compose installed and running on your system.

2.  **Navigate to the Root Directory**: Open a terminal and navigate to the root directory of the `relibank` repository, where the `docker-compose.yml` file is located.

3.  **Start the Stack**: Run the following command to build the service images and start all containers. The `--build` flag is crucial for applying any code or dependency changes.

    ```bash
    docker compose up --build
    ```

    This command will start the `accounts-db` and other dependent containers, wait for them to become healthy, and then start the `accounts-service`.
