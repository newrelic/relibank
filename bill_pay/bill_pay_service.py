# bill_pay_service.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import os
import time
import logging
import asyncio
import json
from contextlib import asynccontextmanager
from aiokafka import AIOKafkaProducer
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global Kafka producer instance
producer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Initializes and connects the Kafka producer.
    """
    global producer
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:29092")
    
    # Retry logic for Kafka connection
    retries = 5
    delay = 1
    for i in range(retries):
        try:
            logging.info(f"Attempting to connect to Kafka at {kafka_broker} (attempt {i+1}/{retries})...")
            producer = AIOKafkaProducer(bootstrap_servers=kafka_broker)
            await producer.start()
            logging.info("Kafka producer connected successfully.")
            break
        except Exception as e:
            logging.warning(f"Failed to connect to Kafka: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
    else:
        logging.error("Failed to connect to Kafka after multiple retries. The application will not be able to publish messages.")
        # We can still run the app, but publishing will fail.
    
    yield

    # Shutdown logic
    if producer:
        await producer.stop()
        logging.info("Kafka producer stopped.")

# FastAPI app instance with lifespan
app = FastAPI(
    title="Bill Pay Service",
    description="Simulates processing bill payments and interacting with other services.",
    version="0.1.0",
    lifespan=lifespan
)

# Pydantic models for request body and response validation
class PaymentDetails(BaseModel):
    billId: str
    amount: float
    currency: str
    accountId: int

class PaymentSchedule(BaseModel):
    billId: str
    amount: float
    currency: str
    accountId: int
    frequency: str # e.g., "monthly", "weekly"
    startDate: str # e.g., "2024-08-06"

class CancelPayment(BaseModel):
    user_id: Optional[str] = "unknown_user"

async def publish_message(topic: str, message: dict):
    """
    A helper function to publish a message to a Kafka topic.
    Raises HTTPException if the producer is not connected.
    """
    if not producer:
        logging.error("Kafka producer is not connected.")
        raise HTTPException(status_code=503, detail="Kafka service is unavailable")

    try:
        message_bytes = json.dumps(message).encode('utf-8')
        await producer.send_and_wait(topic, message_bytes)
        logging.info(f"Message published to topic '{topic}': {message}")
    except Exception as e:
        logging.error(f"Failed to publish message to topic '{topic}': {e}")
        raise HTTPException(status_code=500, detail="Failed to publish message to Kafka")


@app.post("/pay")
async def process_bill_payment(payment_details: PaymentDetails):
    """
    Processes a bill payment request that has already been authenticated.
    - Publishes a message to a real Kafka topic.
    """
    logging.info(f"Received payment request for: {payment_details.billId}")
    logging.info("Authentication handled by upstream service. Proceeding with payment.")
    
    kafka_message = {
        "eventType": "BillPaymentInitiated",
        "billId": payment_details.billId,
        "amount": payment_details.amount,
        "currency": payment_details.currency,
        "accountId": payment_details.accountId,
        "timestamp": time.time()
    }
    await publish_message("bill_payments", kafka_message)
    
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

    kafka_message = {
        "eventType": "RecurringPaymentScheduled",
        "billId": payment_schedule.billId,
        "amount": payment_schedule.amount,
        "currency": payment_schedule.currency,
        "accountId": payment_schedule.accountId,
        "frequency": payment_schedule.frequency,
        "startDate": payment_schedule.startDate,
        "timestamp": time.time()
    }
    await publish_message("recurring_payments", kafka_message)
    
    return {
        "status": "success",
        "message": "Recurring payment scheduled successfully",
        "recurringId": f"RECURRING-{int(time.time() * 1000)}"
    }

@app.post("/cancel/{bill_id}")
async def cancel_payment(bill_id: str, cancel_details: CancelPayment):
    """
    Cancels an initiated payment after checking if it exists.
    - Publishes a message to a real Kafka topic.
    """
    logging.info(f"Received request from user '{cancel_details.user_id}' to cancel payment for bill ID: {bill_id}")

    # --- Synchronous check with the transaction-service ---
    transaction_service_url = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:5000")
    async with httpx.AsyncClient() as client:
        try:
            logging.info(f"Checking for existing transaction with BillID: {bill_id}")
            response = await client.get(f"{transaction_service_url}/transaction/{bill_id}")
            response.raise_for_status() # Raises an exception for 4xx/5xx responses
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logging.error(f"Transaction with BillID '{bill_id}' not found. Cannot cancel.")
                raise HTTPException(status_code=404, detail=f"Transaction with BillID '{bill_id}' not found.")
            else:
                logging.error(f"Unexpected error from transaction service: {e}")
                raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        except httpx.RequestError as e:
            logging.error(f"Failed to connect to transaction service: {e}")
            raise HTTPException(status_code=503, detail="Transaction service is unavailable.")
    
    # If the check is successful, publish the cancellation event
    kafka_message = {
        "eventType": "BillPaymentCancelled",
        "billId": bill_id,
        "user_id": cancel_details.user_id,
        "timestamp": time.time()
    }
    await publish_message("payment_cancellations", kafka_message)

    return {
        "status": "success",
        "message": f"Payment for bill ID {bill_id} has been cancelled successfully by user '{cancel_details.user_id}'."
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
