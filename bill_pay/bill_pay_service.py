import asyncio
import os
import sys
import json
import logging
import pyodbc
import random
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import httpx
from httpx import HTTPStatusError, RequestError
import uuid
import newrelic.agent
from typing import Annotated
import stripe

# Add parent directory to path to import utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils import process_headers

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

newrelic.agent.initialize()

def get_propagation_headers(request: Request) -> dict:
    """
    Extract headers that should be propagated to downstream services.
    Currently propagates: x-browser-user-id, error, extra-transaction-time
    """
    headers_to_propagate = {}

    if "x-browser-user-id" in request.headers:
        headers_to_propagate["x-browser-user-id"] = request.headers["x-browser-user-id"]

    if "error" in request.headers:
        headers_to_propagate["error"] = request.headers["error"]

    if "extra-transaction-time" in request.headers:
        headers_to_propagate["extra-transaction-time"] = request.headers["extra-transaction-time"]

    return headers_to_propagate

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
if stripe.api_key:
    # Disable SSL verification for development (if behind corporate proxy)
    stripe.verify_ssl_certs = False
    logging.info("Stripe initialized successfully (SSL verification disabled for development)")
else:
    logging.warning("STRIPE_SECRET_KEY not set - Stripe functionality will be disabled")

# Scenario service URL
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://scenario-runner-service.relibank.svc.cluster.local:8000")

# Global Kafka producer instance
producer = None

async def get_payment_scenarios():
    """Fetch payment scenario configuration from scenario service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios",
                timeout=2.0
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("scenarios", {})
    except Exception as e:
        logging.debug(f"Could not fetch payment scenarios: {e}")

    # Return defaults if scenario service is unavailable
    return {
        "gateway_timeout_enabled": False,
        "gateway_timeout_delay": 10.0,
        "gateway_timeout_probability": 0.0,
        "card_decline_enabled": False,
        "card_decline_probability": 0.0,
        "stolen_card_enabled": False,
        "stolen_card_probability": 0.0,
    }

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

    # Seed demo customers with payment methods on startup
    if stripe.api_key:
        try:
            logging.info("Seeding demo customers with payment methods...")
            demo_users = [
                {"email": "solaire.a@sunlight.com", "name": "Solaire Astora"},
                {"email": "malenia.m@haligtree.org", "name": "Malenia Miquella"},
                {"email": "artorias.a@darksouls.net", "name": "Artorias Abyss"},
            ]

            for user in demo_users:
                # Check if customer already exists
                existing = stripe.Customer.list(email=user["email"], limit=1)

                if existing.data:
                    customer = existing.data[0]
                    logging.info(f"Demo customer exists: {user['email']} ({customer.id})")
                else:
                    # Create new customer
                    customer = stripe.Customer.create(
                        email=user["email"],
                        name=user["name"],
                        description=f"ReliBank Demo User"
                    )
                    logging.info(f"Created demo customer: {user['email']} ({customer.id})")

                # Check if they have a payment method
                payment_methods = stripe.PaymentMethod.list(customer=customer.id, type="card")

                if not payment_methods.data:
                    # Attach test Visa card
                    stripe.PaymentMethod.attach("pm_card_visa", customer=customer.id)
                    logging.info(f"Attached payment method to {user['email']}")

            logging.info("Demo customer seeding complete")
        except Exception as e:
            logging.warning(f"Failed to seed demo customers: {e}")

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
    currentBalance: Optional[float] = None
    accountType: Optional[str] = None


class CancelPayment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user_id: Optional[str] = "unknown_user"


class CardPaymentRequest(BaseModel):
    """Request model for card payments via Stripe"""
    model_config = ConfigDict(populate_by_name=True)
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(default="usd", min_length=3)
    paymentMethodId: str = Field(min_length=1)  # Payment method token from Stripe.js
    saveCard: bool = False
    customerId: Optional[str] = None  # Stripe customer ID if exists


class CreatePaymentMethodRequest(BaseModel):
    """Request model for creating/saving a payment method using test token"""
    model_config = ConfigDict(populate_by_name=True)
    paymentMethodToken: str = Field(min_length=1)  # Token like 'pm_card_visa' for testing
    customerId: Optional[str] = None
    customerEmail: Optional[str] = None


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
async def process_bill_payment(payment_details: PaymentDetails, request: Request):
    """
    Processes a bill payment request that has already been authenticated.
    - Publishes two messages to a real Kafka topic, one for each account.
    """
    logging.info(f"Received payment request for: {payment_details.billId}, headers: {payment_details}")
    logging.info("Authentication handled by upstream service. Proceeding with payment.")

    # --- Check for duplicate billId ---
    transaction_service_url = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:5001")
    propagation_headers = get_propagation_headers(request)
    async with httpx.AsyncClient() as client:
        # wait if header includes extra_transaction_time
        try:
            logging.info(f"Checking for existing transaction with BillID: {payment_details.billId}")
            response = await client.get(
                f"{transaction_service_url}/transaction-service/transaction/{payment_details.billId}",
                headers=propagation_headers
            )
            process_headers(dict(request.headers))
            if response.status_code == 200:
                logging.error(f"Transaction with BillID '{payment_details.billId}' already exists.")
                raise HTTPException(
                    status_code=409,
                    detail=f"Transaction with BillID '{payment_details.billId}' already exists.",
                )
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
async def process_recurring_payment(payment_schedule: PaymentSchedule, request: Request):
    """
    Simulates setting up a recurring bill payment.
    - Publishes a message to a real Kafka topic.
    """
    try:
        logging.info(f"Received request to schedule recurring payment for: {payment_schedule.billId}")
        logging.info(f"Payment details - Amount: {payment_schedule.amount}, Balance: {payment_schedule.currentBalance}, Account: {payment_schedule.accountType}")

        # Validate insufficient funds
        if payment_schedule.currentBalance is not None and payment_schedule.amount > payment_schedule.currentBalance:
            error_msg = f"Insufficient funds in {payment_schedule.accountType} account. Requested: ${payment_schedule.amount:.2f}, Available: ${payment_schedule.currentBalance:.2f}"
            logging.error(error_msg)

            # Report error to New Relic with custom attributes
            newrelic.agent.notice_error(
                attributes={
                    "error.class": "InsufficientFundsError",
                    "account_type": payment_schedule.accountType,
                    "requested_amount": payment_schedule.amount,
                    "available_balance": payment_schedule.currentBalance,
                    "from_account_id": payment_schedule.fromAccountId,
                    "bill_id": payment_schedule.billId,
                    "error_message": error_msg
                }
            )

            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Unexpected error in recurring payment endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    # Check for a duplicate billId before creating
    transaction_service_url = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:5001")
    propagation_headers = get_propagation_headers(request)
    async with httpx.AsyncClient() as client:
        try:
            logging.info(f"Checking for existing transaction with BillID: {payment_schedule.billId}")
            response = await client.get(
                f"{transaction_service_url}/transaction-service/transaction/{payment_schedule.billId}",
                headers=propagation_headers
            )
            process_headers(dict(request.headers))
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
async def cancel_payment(bill_id: str, cancel_details: CancelPayment, request: Request):
    """
    Cancels an initiated payment after checking if it exists.
    - Publishes a message to a real Kafka topic.
    """
    logging.info(f"Received request from user '{cancel_details.user_id}' to cancel payment for bill ID: {bill_id}")

    # --- Synchronous check with the transaction-service ---
    transaction_service_url = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:5001")
    propagation_headers = get_propagation_headers(request)
    async with httpx.AsyncClient() as client:
        try:
            logging.info(f"Checking for existing transaction with BillID: {bill_id}")
            response = await client.get(
                f"{transaction_service_url}/transaction-service/transaction/{bill_id}",
                headers=propagation_headers
            )
            process_headers(dict(request.headers))
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

@app.post("/bill-pay-service/card-payment")
async def process_card_payment(payment: CardPaymentRequest, request: Request):
    """
    Process a bill payment using a credit/debit card via Stripe.
    Uses Stripe test mode.
    
    See: https://stripe.com/docs/testing#cards
    """
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe payment processing is not configured")

    try:
        logging.info(f"Processing card payment for bill ID: {payment.billId}, amount: ${payment.amount}")

        # Fetch current payment scenarios
        scenarios = await get_payment_scenarios()

        # Check for stolen card scenario (probability-based)
        if scenarios["stolen_card_enabled"] and random.random() * 100 < scenarios["stolen_card_probability"]:
            payment_method_to_use = "pm_card_visa_chargeDeclinedStolenCard"
        else:
            payment_method_to_use = payment.paymentMethodId

        # Check for card decline scenario (probability-based)
        if scenarios["card_decline_enabled"] and random.random() * 100 < scenarios["card_decline_probability"]:
            logging.error(f"Payment processor declined transaction")
            newrelic.agent.record_custom_event("PaymentDeclined", {
                "billId": payment.billId,
                "amount": payment.amount,
                "reason": "card_declined",
                "paymentMethod": "card",
                "processor": "stripe"
            })
            raise HTTPException(
                status_code=402,
                detail="Payment declined by card issuer. Please try a different payment method or contact your bank."
            )

        # Check for gateway timeout scenario (probability-based)
        if scenarios["gateway_timeout_enabled"] and random.random() * 100 < scenarios["gateway_timeout_probability"]:
            delay = scenarios["gateway_timeout_delay"]
            logging.warning(f"Payment gateway experiencing delays (waiting {delay}s)")
            await asyncio.sleep(delay)
            logging.error(f"Payment gateway timeout after {delay}s")
            newrelic.agent.record_custom_event("PaymentTimeout", {
                "billId": payment.billId,
                "amount": payment.amount,
                "timeout_seconds": delay,
                "paymentMethod": "card"
            })
            raise HTTPException(
                status_code=504,
                detail="Payment gateway timeout - please try again later"
            )

        # Create or retrieve Stripe customer
        customer_id = payment.customerId
        if not customer_id:
            customer = stripe.Customer.create(
                description=f"ReliBank Customer for bill {payment.billId}",
                metadata={"billId": payment.billId}
            )
            customer_id = customer.id
            logging.info(f"Created new Stripe customer: {customer_id}")

        # Use the payment method (may be overridden by stolen card scenario)
        logging.info(f"Using payment method: {payment_method_to_use}")

        # Attach to customer if saving
        if payment.saveCard:
            stripe.PaymentMethod.attach(
                payment_method_to_use,
                customer=customer_id,
            )
            logging.info(f"Attached payment method to customer")

        # Create PaymentIntent
        amount_cents = int(payment.amount * 100)  # Stripe uses cents
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=payment.currency,
            customer=customer_id,
            payment_method=payment_method_to_use,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            metadata={
                "billId": payment.billId,
                "service": "relibank-bill-pay"
            }
        )

        logging.info(f"Payment intent created: {payment_intent.id}, status: {payment_intent.status}")

        # Publish to Kafka
        kafka_message = {
            "eventType": "CardPaymentProcessed",
            "billId": payment.billId,
            "amount": payment.amount,
            "currency": payment.currency,
            "paymentIntentId": payment_intent.id,
            "customerId": customer_id,
            "status": payment_intent.status,
            "timestamp": time.time()
        }
        await publish_message("card_payments", kafka_message)

        return {
            "status": "success",
            "message": f"Card payment of ${payment.amount} {payment.currency.upper()} processed successfully",
            "paymentIntentId": payment_intent.id,
            "customerId": customer_id,
            "paymentStatus": payment_intent.status,
            "billId": payment.billId
        }

    except HTTPException:
        # Re-raise HTTPException from scenario checks
        raise
    except stripe.error.CardError as e:
        # Stripe card declined (includes stolen card scenario)
        decline_code = e.code if hasattr(e, 'code') else 'unknown'
        logging.error(f"Card declined by processor: {e.user_message} (code: {decline_code})")

        newrelic.agent.record_custom_event("PaymentDeclined", {
            "billId": payment.billId,
            "amount": payment.amount,
            "reason": decline_code,
            "paymentMethod": "card",
            "processor": "stripe",
            "message": e.user_message
        })

        raise HTTPException(status_code=402, detail=f"Card declined: {e.user_message}")
    except stripe.error.StripeError as e:
        logging.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment processing error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error processing card payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bill-pay-service/payment-method")
async def create_payment_method(payment_method_request: CreatePaymentMethodRequest, request: Request):
    """
    Save a payment method (card) in Stripe for future use.

    Use Stripe test payment method tokens for testing:
    - pm_card_visa - Visa
    - pm_card_mastercard - Mastercard
    - pm_card_amex - American Express

    See: https://stripe.com/docs/testing#cards
    """
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    try:
        logging.info("Saving payment method")

        # Create or retrieve customer
        customer_id = payment_method_request.customerId
        if not customer_id:
            customer = stripe.Customer.create(
                email=payment_method_request.customerEmail,
                description="ReliBank Customer",
            )
            customer_id = customer.id
            logging.info(f"Created new Stripe customer: {customer_id}")

        # Attach the payment method token to customer
        payment_method = stripe.PaymentMethod.attach(
            payment_method_request.paymentMethodToken,
            customer=customer_id,
        )

        logging.info(f"Payment method {payment_method.id} attached to customer {customer_id}")

        return {
            "status": "success",
            "message": "Payment method saved successfully",
            "paymentMethodId": payment_method.id,
            "customerId": customer_id,
            "cardBrand": payment_method.card.brand,
            "cardLast4": payment_method.card.last4
        }

    except stripe.error.StripeError as e:
        logging.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving payment method: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bill-pay-service/payment-methods/{customer_id}")
async def list_payment_methods(customer_id: str):
    """
    List all saved payment methods for a customer.
    """
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type="card",
        )

        return {
            "status": "success",
            "customerId": customer_id,
            "paymentMethods": [
                {
                    "id": pm.id,
                    "brand": pm.card.brand,
                    "last4": pm.card.last4,
                    "expMonth": pm.card.exp_month,
                    "expYear": pm.card.exp_year
                }
                for pm in payment_methods.data
            ]
        }

    except stripe.error.StripeError as e:
        logging.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bill-pay-service/seed-demo-customers")
async def seed_demo_customers():
    """
    Seed demo customers with saved payment methods for load testing.
    Creates standard demo users with Visa cards attached.
    """
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    demo_users = [
        {"email": "solaire.a@sunlight.com", "name": "Solaire Astora"},
        {"email": "malenia.m@haligtree.org", "name": "Malenia Miquella"},
        {"email": "artorias.a@darksouls.net", "name": "Artorias Abyss"},
    ]

    created_customers = []

    try:
        for user in demo_users:
            # Check if customer already exists by email
            existing = stripe.Customer.list(email=user["email"], limit=1)

            if existing.data:
                customer = existing.data[0]
                logging.info(f"Customer already exists: {customer.id} ({user['email']})")
            else:
                # Create new customer
                customer = stripe.Customer.create(
                    email=user["email"],
                    name=user["name"],
                    description=f"ReliBank Demo User - {user['name']}"
                )
                logging.info(f"Created customer: {customer.id} ({user['email']})")

            # Check if they already have a payment method
            payment_methods = stripe.PaymentMethod.list(
                customer=customer.id,
                type="card"
            )

            if not payment_methods.data:
                # Attach a test Visa card
                payment_method = stripe.PaymentMethod.attach(
                    "pm_card_visa",
                    customer=customer.id
                )
                logging.info(f"Attached payment method to {customer.id}")

            created_customers.append({
                "customerId": customer.id,
                "email": user["email"],
                "name": user["name"],
                "hasPaymentMethod": True
            })

        return {
            "status": "success",
            "message": f"Seeded {len(created_customers)} demo customers",
            "customers": created_customers
        }

    except stripe.error.StripeError as e:
        logging.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bill-pay-service")
async def ok():
    """Root return 200"""
    return "ok"

@app.get("/bill-pay-service/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
