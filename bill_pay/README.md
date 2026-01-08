# Relibank Bill Pay Service

This service is a core component of the **Relibank** FinServ application. Its primary function is to handle customer-initiated payment requests and cancellations. It acts as a **producer** in our event-driven architecture, validating requests and publishing events to a **Kafka** message queue for other services to consume.

---

### 🚀 Key Features

* **RESTful API**: Exposes a RESTful API for handling one-time, recurring, and cancellation requests.

* **Stripe Integration**: Processes card payments via Stripe API (test mode only for development).

* **Payment Method Storage**: Stores and manages customer payment methods (cards) in Stripe.

* **Pydantic Validation**: Validates all incoming API requests to ensure data integrity.

* **Kafka Producer**: Publishes payment-related events to dedicated Kafka topics: `bill_payments`, `recurring_payments`, `payment_cancellations`, and `card_payments`.

* **Service-to-Service Communication**: Makes a synchronous API call to the `transaction-service` to check for the existence of a `billId` before processing a payment or cancellation. This ensures data consistency and prevents duplicate transactions.

* **Asynchronous Processing**: All payments are handled asynchronously by publishing events, allowing for a highly responsive user experience.

---

### 📦 API Endpoints

The service exposes the following API endpoints, which are designed to be consumed by the customer portal or other upstream services.

#### Account Transfer Payments
| Endpoint | Method | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `/pay` | `POST` | Initiates a one-time bill payment. | `fromAccountId`, `toAccountId`, `amount`, `currency`, `billId` |
| `/recurring` | `POST` | Schedules a recurring bill payment. | `fromAccountId`, `toAccountId`, `amount`, `currency`, `billId`, `frequency`, `startDate` |
| `/cancel/{bill_id}` | `POST` | Cancels a pending or recurring payment after verifying it exists. | `user_id` |

#### Card Payments (Stripe)
| Endpoint | Method | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `/card-payment` | `POST` | Process a card payment via Stripe. | `billId`, `amount`, `currency`, `cardNumber`, `expMonth`, `expYear`, `cvc`, `saveCard`, `customerId` |
| `/payment-method` | `POST` | Save a payment method (card) for future use. | `cardNumber`, `expMonth`, `expYear`, `cvc`, `customerId`, `customerEmail` |
| `/payment-methods/{customer_id}` | `GET` | List all saved payment methods for a customer. | None |

#### Health Check
| Endpoint | Method | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | A health check endpoint that returns a status of `healthy`. | None |

---

### 🔧 Stripe Configuration

To enable card payment functionality, you need to configure Stripe API keys.

1. **Get Stripe Test Keys**:
   - Sign up at https://stripe.com
   - Get test API keys from https://dashboard.stripe.com/test/apikeys
   - Copy your `sk_test_*` (secret key) and `pk_test_*` (publishable key)

2. **Add to skaffold.env**:
   ```bash
   STRIPE_SECRET_KEY=sk_test_your_secret_key_here
   STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
   ```

3. **Keys Flow**: `skaffold.env` → `skaffold.yaml` → `Dockerfile` → container environment

4. **Test Cards**: Use Stripe test cards for development:
   - `4242424242424242` - Visa (succeeds)
   - `4000000000000002` - Visa (declined)
   - `4000000000009995` - Visa (insufficient funds)
   - Any future expiration, any CVC, any ZIP

**Note**: If Stripe keys are not configured, card payment endpoints will return 503 errors. Account transfer payments will continue to work normally.

---

### 🎭 Demo Scenarios

The card payment endpoint integrates with the scenario service to support runtime-toggleable failure scenarios for demonstrations:

#### Available Scenarios

1. **Card Decline**: Payments matching a specific amount will be declined with "insufficient funds"
   - Default decline amount: $999.99
   - Configurable via scenario service API

2. **Gateway Timeout**: Simulate payment gateway delays and timeouts
   - Default: Disabled
   - Configurable delay: 1-60 seconds
   - Enables realistic timeout behavior for demos

#### Managing Scenarios

Control scenarios via the scenario service API (port 8000):

```bash
# Get current scenario configuration
curl http://localhost:8000/scenario-runner/api/payment-scenarios

# Enable gateway timeout with 15 second delay
curl -X POST "http://localhost:8000/scenario-runner/api/payment-scenarios/gateway-timeout?enabled=true&delay=15"

# Set decline amount to $50.00
curl -X POST "http://localhost:8000/scenario-runner/api/payment-scenarios/decline-amount?amount=50.00"

# Reset all scenarios to defaults
curl -X POST http://localhost:8000/scenario-runner/api/payment-scenarios/reset
```

These scenarios are also available in the Postman collection under "scenario service".

---

### ⚙️ How to Run

This service is designed to be run using Skaffold as part of the larger **Relibank** application stack.

1.  **Configure Environment**: Ensure `skaffold.env` contains required variables including Stripe keys (optional).

2.  **Navigate to Root Directory**: Open a terminal and navigate to the root directory of the `relibank` repository.

3.  **Start the Stack**: Run the following command to build and deploy all services:

    ```bash
    skaffold dev
    ```

    This command will build all services, deploy to Kubernetes, and start port forwarding.
    
