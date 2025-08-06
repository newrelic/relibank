# app.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Placeholder for New Relic APM Instrumentation ---
# In a real application, you would initialize the New Relic agent here.
# For example, if using newrelic-agent:
# import newrelic.agent
# newrelic.agent.initialize('newrelic.ini', os.environ.get('NEW_RELIC_ENV', 'development'))
#
# To instrument a FastAPI route, you might wrap the function or use a custom decorator
# if New Relic's auto-instrumentation doesn't cover it directly.
# For example:
# @app.post("/pay")
# @newrelic.agent.web_transaction()
# async def process_bill_payment(payment_details: PaymentDetails):
#     ...
# --- End New Relic Placeholder ---

app = FastAPI(
    title="Bill Pay Service",
    description="Simulates processing bill payments and interacting with other services.",
    version="0.1.0"
)

# Pydantic model for request body validation
class PaymentDetails(BaseModel):
    billId: str
    amount: float
    currency: str
    accountId: str

@app.post("/pay")
async def process_bill_payment(payment_details: PaymentDetails):
    """
    Simulates processing a bill payment.
    - Mocks interaction with an Authentication Service.
    - Mocks publishing a message to a Kafka topic.
    """
    logging.info(f"Received payment request for: {payment_details.billId}")

    # --- Simulate Authentication Service Call ---
    # In a real scenario, this would be an HTTP call to your Authentication Service.
    # We'll simulate success for the demo.
    logging.info("Simulating call to Authentication Service...")
    await asyncio.sleep(0.1) # Use asyncio.sleep for async operations
    auth_successful = True
    if not auth_successful:
        logging.error("Authentication failed (simulated).")
        raise HTTPException(status_code=401, detail="Authentication failed")
    logging.info("Authentication successful (simulated).")

    # --- Simulate Kafka Message Publishing ---
    # In a real scenario, you'd use an async Kafka client library (e.g., aiokafka)
    # to produce a message to a Kafka topic.
    # For the demo, we'll just log the "published" message.
    logging.info(f"Simulating publishing payment event to Kafka topic 'bill_payments'...")
    try:
        # Mock Kafka message payload
        kafka_message = {
            "eventType": "BillPaymentInitiated",
            "billId": payment_details.billId,
            "amount": payment_details.amount,
            "currency": payment_details.currency,
            "accountId": payment_details.accountId,
            "timestamp": time.time()
        }
        logging.info(f"Kafka message content (simulated): {kafka_message}")
        await asyncio.sleep(0.2) # Simulate Kafka producer latency
        logging.info("Payment event successfully 'published' to Kafka (simulated).")
    except Exception as e:
        logging.error(f"Failed to 'publish' to Kafka (simulated error): {e}")
        raise HTTPException(status_code=500, detail="Failed to process payment asynchronously")

    logging.info(f"Bill payment for {payment_details.billId} successfully initiated.")
    return {
        "status": "success",
        "message": "Bill payment initiated successfully",
        "transactionId": f"TXN-{int(time.time() * 1000)}" # Mock transaction ID
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}

# Note: FastAPI applications are typically run using Uvicorn directly, not app.run()
# The Dockerfile will handle running Uvicorn.
