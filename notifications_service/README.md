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

4. **Test the Service**: After the containers are running, send a payment request to the `bill-pay` service. You will see a `SIMULATED EMAIL` or `SIMULATED SMS` log message appear in the console output for the `notifications-servic