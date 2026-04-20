import asyncio
import os
import logging
import json
import time
import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaProducer

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Global Kafka producer instance
producer = None

# Support Service URL
SUPPORT_SERVICE_URL = os.getenv("SUPPORT_SERVICE_URL", "http://support-service.relibank.svc.cluster.local:5003")

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
            logger.info(f"Attempting to connect to Kafka at {kafka_broker} (attempt {i + 1}/{retries})")
            producer = AIOKafkaProducer(bootstrap_servers=kafka_broker)
            await producer.start()
            logger.info("Kafka producer connected successfully")
            break
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka: {e}. Retrying in {delay} seconds")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
    else:
        logger.error("Failed to connect to Kafka after multiple retries. Service will not publish messages")

    yield

    # Shutdown logic
    if producer:
        await producer.stop()
        logger.info("Kafka producer stopped")


# FastAPI app instance with lifespan
app = FastAPI(
    title="Relibank Risk Assessment Service",
    description="Assesses risk on bill payments and publishes events to Kafka.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class RiskAssessmentRequest(BaseModel):
    """Request model for risk assessment from Bill Pay"""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    account_id: str = Field(..., description="Account making the payment")
    amount: float = Field(..., description="Payment amount")
    payee: str = Field(..., description="Who the payment is going to")
    payment_method: str = Field(default="checking", description="Payment method (checking, savings, credit)")


class RiskAssessmentResponse(BaseModel):
    """Response model returned to Bill Pay"""
    transaction_id: str = Field(..., description="Transaction ID")
    decision: str = Field(..., description="approved or declined")
    risk_level: str = Field(..., description="low, medium, or high")
    risk_score: float = Field(..., description="0-100 risk score")
    reason: str = Field(..., description="Why this decision was made")
    assessment_duration_ms: int = Field(..., description="How long the assessment took")
    agent_model: str = Field(..., description="Which AI model was used for assessment")


class RiskAssessmentEvent(BaseModel):
    """Kafka event model for risk assessment results"""
    risk_level: str = Field(..., description="The assessed risk level (low, medium, high)")
    reason: str = Field(..., description="The reason for the assessed risk level")
    risk_score: float = Field(..., description="Numerical risk score (0-100)")
    decision: str = Field(..., description="approved or declined")
    transaction_id: str = Field(..., description="ID of the transaction being assessed")
    account_id: str = Field(..., description="Account ID from bill pay request")
    amount: float = Field(..., description="Transaction amount")
    payee: str = Field(..., description="Who the payment is going to")
    timestamp: str = Field(..., description="When the assessment was made")
    support_service_agent: str = Field(..., description="Which agent was used (for tracking model changes)")
    assessment_duration_ms: int = Field(..., description="How long the assessment took")


class SupportServiceRequest(BaseModel):
    """Request model for Support Service AI agent"""
    transaction_id: str
    account_id: str
    amount: float
    payee: str
    payment_method: str


# --- Helper Functions ---

async def call_support_service(request_data: dict) -> dict:
    """
    Call Support Service AI agent to get risk analysis.
    Returns the agent's assessment including risk score and reasoning.
    """
    start_time = time.time()

    logger.info(json.dumps({
        "message": {
            "log_level": "INFO",
            "service": "risk_assessment_service",
            "event": "SUPPORT_SERVICE_CALL",
            "transaction_id": request_data.get("transaction_id"),
            "account_id": request_data.get("account_id"),
            "amount": request_data.get("amount"),
            "payee": request_data.get("payee")
        }
    }))

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SUPPORT_SERVICE_URL}/support-service/assess-payment-risk",
                json=request_data,
            )

            response.raise_for_status()
            result = response.json()

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(json.dumps({
                "message": {
                    "log_level": "INFO",
                    "service": "risk_assessment_service",
                    "event": "SUPPORT_SERVICE_RESPONSE",
                    "transaction_id": request_data.get("transaction_id"),
                    "agent_model": result.get("agent_model"),
                    "decision": result.get("decision"),
                    "risk_level": result.get("risk_level"),
                    "risk_score": result.get("risk_score"),
                    "support_service_duration_ms": duration_ms
                }
            }))

            return result

    except httpx.HTTPStatusError as e:
        logger.error(json.dumps({
            "message": {
                "log_level": "ERROR",
                "service": "risk_assessment_service",
                "event": "SUPPORT_SERVICE_ERROR",
                "transaction_id": request_data.get("transaction_id"),
                "status_code": e.response.status_code,
                "error": str(e)
            }
        }))
        raise HTTPException(
            status_code=503,
            detail=f"Support Service error: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(json.dumps({
            "message": {
                "log_level": "ERROR",
                "service": "risk_assessment_service",
                "event": "SUPPORT_SERVICE_CONNECTION_FAILED",
                "transaction_id": request_data.get("transaction_id"),
                "error": str(e)
            }
        }))
        raise HTTPException(
            status_code=503,
            detail="Support Service unavailable"
        )
    except Exception as e:
        logger.error(json.dumps({
            "message": {
                "log_level": "ERROR",
                "service": "risk_assessment_service",
                "event": "SUPPORT_SERVICE_UNEXPECTED_ERROR",
                "transaction_id": request_data.get("transaction_id"),
                "error": str(e)
            }
        }))
        raise HTTPException(
            status_code=500,
            detail=f"Risk assessment failed: {str(e)}"
        )


# --- API Endpoints ---

@app.post("/risk-assessment-service/assess-risk")
async def assess_risk(request: RiskAssessmentRequest) -> RiskAssessmentResponse:
    """
    Main endpoint - Bill Pay calls this to assess transaction risk.

    Flow:
    1. Log incoming request with full context
    2. Call Support Service AI agent for risk analysis
    3. Process agent response and make decision
    4. Publish Kafka event if payment is declined
    5. Log final decision with full context
    6. Return response to Bill Pay
    """
    assessment_start = time.time()

    logger.info(json.dumps({
        "message": {
            "log_level": "INFO",
            "service": "risk_assessment_service",
            "event": "RISK_ASSESSMENT_REQUESTED",
            "transaction_id": request.transaction_id,
            "account_id": request.account_id,
            "amount": request.amount,
            "payee": request.payee,
            "payment_method": request.payment_method
        }
    }))

    try:
        # Call Support Service for AI-based risk analysis
        support_request = {
            "transaction_id": request.transaction_id,
            "account_id": request.account_id,
            "amount": request.amount,
            "payee": request.payee,
            "payment_method": request.payment_method,
        }

        support_response = await call_support_service(support_request)

        # Extract risk assessment from Support Service response
        risk_level = support_response.get("risk_level", "medium")
        risk_score = support_response.get("risk_score", 50.0)
        reason = support_response.get("reason", "Risk assessment completed")
        decision = support_response.get("decision", "approved")
        agent_model = support_response.get("agent_model", "unknown")

        assessment_duration_ms = int((time.time() - assessment_start) * 1000)

        # Create assessment event for Kafka
        assessment_event = RiskAssessmentEvent(
            risk_level=risk_level,
            reason=reason,
            risk_score=risk_score,
            decision=decision,
            transaction_id=request.transaction_id,
            account_id=request.account_id,
            amount=request.amount,
            payee=request.payee,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            support_service_agent=agent_model,
            assessment_duration_ms=assessment_duration_ms,
        )

        # Publish Kafka event for declined payments
        if decision == "declined":
            logger.warning(json.dumps({
                "message": {
                    "log_level": "WARNING",
                    "service": "risk_assessment_service",
                    "event": "PAYMENT_DECLINED",
                    "processor_model": agent_model,
                    "transaction_id": request.transaction_id,
                    "account_id": request.account_id,
                    "amount": request.amount,
                    "payee": request.payee,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                    "reason": reason,
                    "decision": "declined",
                    "assessment_duration_ms": assessment_duration_ms
                }
            }))

            try:
                await producer.send(
                    "payment-declined",
                    value=json.dumps(assessment_event.dict()).encode("utf-8")
                )
                logger.info(f"Published to Kafka topic payment-declined for transaction {request.transaction_id}")
            except Exception as e:
                logger.error(json.dumps({
                    "message": {
                        "log_level": "ERROR",
                        "service": "risk_assessment_service",
                        "event": "KAFKA_PUBLISH_FAILED",
                        "transaction_id": request.transaction_id,
                        "error": str(e)
                    }
                }))
                # Don't fail the request if Kafka publishing fails
        else:
            logger.info(json.dumps({
                "message": {
                    "log_level": "INFO",
                    "service": "risk_assessment_service",
                    "event": "PAYMENT_APPROVED",
                    "processor_model": agent_model,
                    "transaction_id": request.transaction_id,
                    "account_id": request.account_id,
                    "amount": request.amount,
                    "payee": request.payee,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                    "reason": reason,
                    "decision": "approved",
                    "assessment_duration_ms": assessment_duration_ms
                }
            }))

        # Return response to Bill Pay
        response = RiskAssessmentResponse(
            transaction_id=request.transaction_id,
            decision=decision,
            risk_level=risk_level,
            risk_score=risk_score,
            reason=reason,
            assessment_duration_ms=assessment_duration_ms,
            agent_model=agent_model,
        )

        logger.info(f"Risk assessment completed for transaction {request.transaction_id}: {decision}")

        return response

    except HTTPException:
        # Re-raise HTTP exceptions from helper functions
        raise
    except Exception as e:
        logger.error(json.dumps({
            "message": {
                "log_level": "ERROR",
                "service": "risk_assessment_service",
                "event": "RISK_ASSESSMENT_ERROR",
                "transaction_id": request.transaction_id,
                "error": str(e)
            }
        }))
        raise HTTPException(
            status_code=500,
            detail=f"Risk assessment failed: {str(e)}"
        )


@app.get("/risk-assessment-service")
async def root():
    """Root endpoint - returns OK"""
    return {"status": "ok", "service": "risk-assessment"}


@app.get("/risk-assessment-service/health")
async def health_check():
    """Health check endpoint for Kubernetes"""
    return {"status": "healthy"}


@app.get("/risk-assessment-service/healthz")
async def healthz():
    """Kubernetes liveness probe endpoint"""
    return {"status": "healthy"}
