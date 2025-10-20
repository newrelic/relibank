import asyncio
import os
import json
import logging
import pyodbc
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from typing import Optional, List, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import time
import httpx
from httpx import HTTPStatusError, RequestError
import uuid
import newrelic.agent
from typing import Annotated

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

newrelic.agent.initialize(log_file='/app/newrelic.log', log_level=logging.DEBUG)

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
            logging.info(f"Attempting to connect to Kafka at {kafka_broker} (attempt {i + 1}/{retries})...")
            producer = AIOKafkaProducer(bootstrap_servers=kafka_broker)
            await producer.start()
            logging.info("Kafka producer connected successfully.")
            break
        except Exception as e:
            logging.warning(f"Failed to connect to Kafka: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
    else:
        logging.error(
            "Failed to connect to Kafka after multiple retries. The application will not be able to publish messages."
        )
        # We can still run the app, but publishing will fail.

    yield

    # Shutdown logic
    if producer:
        await producer.stop()
        logging.info("Kafka producer stopped.")


# FastAPI app instance with lifespan
app = FastAPI(
    title="Relibank Bill Pay Service",
    description="Handles bill payment requests and publishes events to Kafka.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This allows all domains
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# Pydantic models for request body and response validation
class PaymentDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    fromAccountId: int
    toAccountId: Optional[int] = 0


class PaymentSchedule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    fromAccountId: int
    toAccountId: Optional[int] = 0
    frequency: str = Field(min_length=1)
    startDate: str = Field(min_length=1)


class CancelPayment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
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
        message_bytes = json.dumps(message).encode("utf-8")
        await producer.send_and_wait(topic, message_bytes)
        logging.info(f"Message published to topic '{topic}': {message}")
    except Exception as e:
        logging.error(f"Failed to publish message to topic '{topic}': {e}")
        raise HTTPException(status_code=500, detail="Failed to publish message to Kafka")


@app.post("/bill-pay-service/pay")
async def process_bill_payment(
    payment_details: PaymentDetails,
    error: Annotated[int, Header()] = None,
    extra_transaction_time: Annotated[int | None, Header()] = 0
    ):
    """
    Processes a bill payment request that has already been authenticated.
    - Publishes two messages to a real Kafka topic, one for each account.
    """
    logging.info(f"Received payment request for: {payment_details.billId}, headers: {payment_details} {error} {extra_transaction_time}")
    logging.info("Authentication handled by upstream service. Proceeding with payment.")

    # --- Check for duplicate billId ---
    transaction_service_url = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:5001")
    async with httpx.AsyncClient() as client:
        # wait if header includes extra_transaction_time
        if extra_transaction_time:
            await asyncio.sleep(extra_transaction_time)
        try:
            logging.info(f"Checking for existing transaction with BillID: {payment_details.billId}")
            response = await client.get(f"{transaction_service_url}/transaction-service/transaction/{payment_details.billId}")
            if response.status_code == 200:
                logging.error(f"Transaction with BillID '{payment_details.billId}' already exists.")
                raise HTTPException(
                    status_code=409,
                    detail=f"Transaction with BillID '{payment_details.billId}' already exists.",
                )
            # make an error if header includes error code
            if error:
                try:
                    status_code = int(error)
                    raise HTTPException(status_code=status_code)
                except ValueError:
                    logging.error(f"Invalid status code received in 'error' header: {error}")
                    # Optionally raise a 400 or just ignore the invalid header
                    raise HTTPException(status_code=400, detail="Invalid 'error' status code provided in header.")
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                logging.info(f"Transaction with BillID '{payment_details.billId}' not found. OK to proceed.")
            else:
                logging.error(f"Unexpected error from transaction service: {e}")
                raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        except RequestError:
            logging.error("Failed to connect to transaction service.")
            raise HTTPException(status_code=503, detail="Transaction service is unavailable.")

    # Create a unique transaction ID for the double entry
    transaction_uuid = str(uuid.uuid4())

    # Kafka message for the debit side
    debit_event = {
        "eventType": "BillPaymentInitiatedFromAcct",
        "transactionId": transaction_uuid,
        "billId": payment_details.billId,
        "amount": payment_details.amount,
        "currency": payment_details.currency,
        "accountId": payment_details.fromAccountId,
        "timestamp": time.time(),
    }

    # Kafka message for the credit side
    credit_event = {
        "eventType": "BillPaymentInitiatedToAcct",
        "transactionId": transaction_uuid,
        "billId": payment_details.billId,
        "amount": payment_details.amount,
        "currency": payment_details.currency,
        "accountId": payment_details.toAccountId,
        "timestamp": time.time(),
    }

    await publish_message("bill_payments", debit_event)
    await publish_message("bill_payments", credit_event)

    logging.info(f"Bill payment for {payment_details.billId} successfully initiated.")
    return {
        "status": "success",
        "message": "Bill payment initiated successfully",
        "transactionId": transaction_uuid,
    }


@app.post("/bill-pay-service/recurring")
async def process_recurring_payment(payment_schedule: PaymentSchedule):
    """
    Simulates setting up a recurring bill payment.
    - Publishes a message to a real Kafka topic.
    """
    logging.info(f"Received request to schedule recurring payment for: {payment_schedule.billId}")

    # Check for a duplicate billId before creating
    transaction_service_url = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:5001")
    async with httpx.AsyncClient() as client:
        try:
            logging.info(f"Checking for existing transaction with BillID: {payment_schedule.billId}")
            response = await client.get(f"{transaction_service_url}/transaction-service/transaction/{payment_schedule.billId}")
            if response.status_code == 200:
                raise HTTPException(status_code=409, detail=f"Bill with ID '{payment_schedule.billId}' already exists.")
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                logging.info(f"Transaction with BillID '{payment_schedule.billId}' not found. OK to proceed.")
            else:
                logging.error(f"Unexpected error from transaction service: {e}")
                raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        except RequestError:
            logging.error("Failed to connect to transaction service.")
            raise HTTPException(status_code=503, detail="Transaction service is unavailable.")

    # Kafka message to create the schedule
    kafka_message = {
        "eventType": "RecurringPaymentScheduled",
        "billId": payment_schedule.billId,
        "amount": payment_schedule.amount,
        "currency": payment_schedule.currency,
        "accountId": payment_schedule.fromAccountId,
        "frequency": payment_schedule.frequency,
        "startDate": payment_schedule.startDate,
        "timestamp": time.time(),
    }

    await publish_message("recurring_payments", kafka_message)

    return {
        "status": "success",
        "message": "Recurring payment scheduled successfully",
        "recurringId": f"RECURRING-{str(uuid.uuid4())}",
    }


@app.post("/bill-pay-service/cancel/{bill_id}")
async def cancel_payment(bill_id: str, cancel_details: CancelPayment):
    """
    Cancels an initiated payment after checking if it exists.
    - Publishes a message to a real Kafka topic.
    """
    logging.info(f"Received request from user '{cancel_details.user_id}' to cancel payment for bill ID: {bill_id}")

    # --- Synchronous check with the transaction-service ---
    transaction_service_url = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:5001")
    async with httpx.AsyncClient() as client:
        try:
            logging.info(f"Checking for existing transaction with BillID: {bill_id}")
            response = await client.get(f"{transaction_service_url}/transaction-service/transaction/{bill_id}")
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Transaction with BillID '{bill_id}' not found.",
                )
        except httpx.RequestError as e:
            logging.error(f"Failed to connect to transaction service: {e}")
            raise HTTPException(status_code=503, detail="Transaction service is unavailable.")
        except HTTPStatusError as e:
            # Re-raise the exception if it's not a 404
            if e.response.status_code != 404:
                logging.error(f"Unexpected error from transaction service: {e}")
                raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    # If the check is successful, publish the cancellation event
    kafka_message = {
        "eventType": "BillPaymentCancelled",
        "billId": bill_id,
        "user_id": cancel_details.user_id,
        "timestamp": time.time(),
    }
    await publish_message("payment_cancellations", kafka_message)

    return {
        "status": "success",
        "message": f"Payment for bill ID {bill_id} has been cancelled successfully by user '{cancel_details.user_id}'.",
    }

@app.get("/bill-pay-service")
async def ok():
    """Root return 200"""
    return "ok"

@app.get("/bill-pay-service/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
