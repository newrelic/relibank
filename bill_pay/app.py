# app.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
import time
import logging
import json
from aiokafka import AIOKafkaProducer

# Add when we have a Transaction database
# import pyodbc

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="Bill Pay Service",
    description="Processes bill payments.",
    version="0.1.0"
)

# Pydantic models for request body and response validation
class PaymentDetails(BaseModel):
    billId: str
    amount: float
    currency: str
    accountId: int

class Payment(PaymentDetails):
    transactionId: str
    timestamp: float

class PaymentSchedule(BaseModel):
    billId: str
    amount: float
    currency: str
    accountId: int
    frequency: str # e.g., "monthly", "weekly"
    startDate: str # e.g., "2024-08-06"

# A placeholder for a simple, in-memory database
# Replace with MSSQL Transactions DB when we make it
MOCK_PAYMENTS_HISTORY = [
    Payment(
        billId="BILL-HISTORY-001", 
        amount=50.00, 
        currency="USD", 
        accountId="873467890",
        transactionId="TXN-1722950400",
        timestamp=1722950400.0
    ),
    Payment(
        billId="BILL-HISTORY-002", 
        amount=125.75, 
        currency="EUR", 
        accountId="873467890",
        transactionId="TXN-1722950500",
        timestamp=1722950500.0
    )
]

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

@app.post("/pay")
async def process_bill_payment(payment_details: PaymentDetails):
    """
    Processes a bill payment request that has already been authenticated.
    - Publishes a message to a real Kafka topic.
    """
    logging.info(f"Received payment request for: {payment_details.billId}")
    logging.info("Authentication handled by upstream service. Proceeding with payment.")
    
    # --- Real Kafka Message Publishing ---
    # Kafka is running on a container. We get the broker address from an environment variable.
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka-vm:9092")
    producer = AIOKafkaProducer(bootstrap_servers=kafka_broker)
    try:
        await producer.start()
        kafka_message = {
            "eventType": "BillPaymentInitiated",
            "billId": payment_details.billId,
            "amount": payment_details.amount,
            "currency": payment_details.currency,
            "accountId": payment_details.accountId,
            "timestamp": time.time()
        }
        message_bytes = json.dumps(kafka_message).encode('utf-8')
        await producer.send_and_wait("bill_payments", message_bytes)
        logging.info("Payment event successfully published to Kafka.")
    finally:
        await producer.stop()
    
    logging.info(f"Bill payment for {payment_details.billId} successfully initiated.")
    return {
        "status": "success",
        "message": "Bill payment initiated successfully",
        "transactionId": f"TXN-{int(time.time() * 1000)}"
    }

@app.post("/recurring")
async def process_recurring_payment(payment_schedule: PaymentSchedule):
    """
    Simulates setting up a recurring bill payment.
    - Publishes a message to a real Kafka topic.
    """
    logging.info(f"Received request to schedule recurring payment for: {payment_schedule.billId}")

    # --- Real Kafka Message Publishing ---
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka-vm:9092")
    producer = AIOKafkaProducer(bootstrap_servers=kafka_broker)
    try:
        await producer.start()
        kafka_message = {
            "eventType": "RecurringPaymentScheduled",
            "billId": payment_schedule.billId,
            "accountId": payment_schedule.accountId,
            "frequency": payment_schedule.frequency,
            "startDate": payment_schedule.startDate,
            "timestamp": time.time()
        }
        message_bytes = json.dumps(kafka_message).encode('utf-8')
        await producer.send_and_wait("recurring_payments", message_bytes)
        logging.info("Recurring payment event successfully published to Kafka.")
    finally:
        await producer.stop()
    
    return {
        "status": "success",
        "message": "Recurring payment scheduled successfully",
        "recurringId": f"RECURRING-{int(time.time() * 1000)}"
    }

# Probably lives in the Transaction service and not here
# @app.get("/history", response_model=List[Payment])
# async def get_payment_history():
#     """
#     Retrieves mock payment history data.
#     """
#     logging.info("Received request for payment history.")
#     # In a real app, this would query a database.
#     # For the demo, we return a hardcoded list.
#     return MOCK_PAYMENTS_HISTORY


# Later, we can check the auth service to see if the user has rights to cancel this bill pay
# Are they listed as an owner on the account this bill payment is coming from?
# We can also skip auth entirely and just log the user

# TODO check the transaction database to confirm the bill_id actually exists
@app.post("/cancel/{bill_id}")
async def cancel_payment(bill_id: str, user_id: Optional[str] = "unknown_user"):
    """
    Simulates canceling an initiated payment and includes a user_id.
    - Publishes a message to a real Kafka topic.
    """
    logging.info(f"Received request from user '{user_id}' to cancel payment for bill ID: {bill_id}")
    
    # --- Real Kafka Message Publishing ---
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka-vm:9092")
    producer = AIOKafkaProducer(bootstrap_servers=kafka_broker)
    try:
        await producer.start()
        kafka_message = {
            "eventType": "BillPaymentCancelled",
            "billId": bill_id,
            "user_id": user_id,
            "timestamp": time.time()
        }
        message_bytes = json.dumps(kafka_message).encode('utf-8')
        await producer.send_and_wait("payment_cancellations", message_bytes)
        logging.info("Payment cancellation event successfully published to Kafka.")
    finally:
        await producer.stop()

    return {
        "status": "success",
        "message": f"Payment for bill ID {bill_id} has been cancelled successfully by user '{user_id}'."
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}

# Note: FastAPI applications are typically run using Uvicorn directly, not app.run()
# The Dockerfile will handle running Uvicorn.
