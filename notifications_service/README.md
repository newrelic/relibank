# Relibank Notifications Service

This service is a crucial component of the **Relibank** event-driven architecture, designed to provide real-time updates to users via email and SMS. It acts as a dedicated **consumer**, reacting to a variety of payment-related events published to the **Kafka** message queue.

---

### 🚀 Key Features

* **Event-Driven**: The service is entirely asynchronous and decoupled from other services. It doesn't initiate actions itself but instead reacts to events from the `bill-pay` and `scheduler-service`.

* **Multi-Channel Notifications**: It contains draft functionality for sending notifications via email and SMS. The code is structured to support different providers, with commented-out examples for popular services like **Twilio** and **SendGrid**, as well as Azure-native **Azure Communication Services (ACS)**.

* **Pydantic Validation**: It uses Pydantic to validate incoming Kafka messages against a predefined schema, ensuring that the event data is clean and correctly formatted before a notification is sent.

---

### 📦 Event Topics

The service is configured to consume events from the following Kafka topics:

| Topic | Description | 
 | ----- | ----- | 
| `bill_payments` | Notifies users when a one-time payment has been successfully initiated. | 
| `recurring_payments` | Notifies users when a new recurring payment has been scheduled. | 
| `payment_cancellations` | Notifies users when a payment has been successfully canceled. | 
| `payment_due_notifications` | Notifies users that a recurring payment is coming up and is now due. | 

---

### ⚙️ How to Run

This service is deployed as part of the larger **Relibank** application stack using Skaffold and Kubernetes.

1. **Ensure Prerequisites**: Make sure you have Docker Desktop (with Kubernetes enabled) or Minikube, Skaffold, kubectl, and Helm installed.

2. **Configure Environment**: From the root of the `relibank` repository, populate `skaffold.env` with the required secrets and configuration values.

3. **Start the Stack**: Run the following command from the root directory to build all images and deploy all services to your local Kubernetes cluster:

   ```bash
   skaffold dev
   ```

   This will build the service images, deploy all Kubernetes resources, and set up port forwarding automatically.

4. **Test the Service**: After the containers are running, send a payment request to the `bill-pay` service. You will see a `SIMULATED EMAIL` or `SIMULATED SMS` log message appear in the console output for the `notifications-service`.

---

### 📡 New Relic Monitoring

The deployed Azure Function (`azure_function/`, triggered via `AZURE_FUNCTION_URL`) is monitored through New Relic's Azure cloud-polling integration — see `terraform/aks/newrelic/nr_azure_integration.tf` and [`docs/deployer/runbook.md`](../docs/deployer/runbook.md) for setup/troubleshooting. No agent runs inside the Function App; New Relic polls Azure Monitor directly.

**Known gaps as of this writing:**
- ~~Execution/error metrics (`functionExecutionCount`, `http5xx`) don't populate — the Function App has no Application Insights connected~~ — fixed: `terraform/aks/notifications/main.tf` now provisions a Log Analytics workspace + Application Insights for the Function App. Rolls out to each environment the next time its Stage 4 (`notifications`) is applied.
- Real Azure Communication Services delivery is disabled by design right now (`SIMULATE_NOTIFICATIONS=true`, default across all environments) because ACS itself is blocked: SMS sends fail with `Unauthorized`, email sends fail with `SubscriptionBlocked` ("All requests from this subscription are blocked due to the sender reputation"). This is an Azure-side issue tracked in `ticket-maker/2026-07-15-relibank-notification-delivery-failures` (needs an Azure Support ticket for the email block), not a bug in this service's code. Until it's resolved, `notify_user_trigger` logs a simulated send and returns success instead of calling ACS — see `SIMULATE_NOTIFICATIONS` in `function_app.py`. Flip it to `false` per-environment once ACS is confirmed fixed there.
- This has gone unnoticed because `scheduler_service`'s `PaymentDueNotificationEvent` — the only event type that triggers a real notification — hasn't fired in any environment in 30+ days. If you're debugging "notifications aren't sending," confirm the event is actually being produced before assuming the Azure/ACS layer is at fault.