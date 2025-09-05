import asyncio
import os
import json
import logging
import pyodbc
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import time
import httpx
from httpx import HTTPStatusError, RequestError
import newrelic.agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

newrelic.agent.initialize(log_file='/app/newrelic.log', log_level=logging.DEBUG)

# Database connection details from environment variables
DB_SERVER = os.getenv("DB_SERVER", "mssql")
DB_DATABASE = os.getenv("DB_DATABASE", "RelibankDB")
DB_USERNAME = os.getenv("DB_USERNAME", "SA")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrong@Password!")
CONNECTION_STRING = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD};TrustServerCertificate=yes"
CONNECTION_STRING_MASTER = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE=master;UID={DB_USERNAME};PWD={DB_PASSWORD};TrustServerCertificate=yes"


# Pydantic models for API and Kafka message validation
class TransactionRecord(BaseModel):
    # Mapping SQL column names to Pydantic field names
    transaction_id: int = Field(alias="TransactionID")
    event_type: str = Field(alias="EventType")
    bill_id: str = Field(alias="BillID")
    amount: float = Field(alias="Amount")
    currency: str = Field(alias="Currency")
    account_id: int = Field(alias="AccountID")
    timestamp: float = Field(alias="Timestamp")
    cancellation_user_id: Optional[str] = Field(None, alias="CancellationUserID")
    cancellation_timestamp: Optional[float] = Field(None, alias="CancellationTimestamp")

    class Config:
        populate_by_name = True  # This tells Pydantic to use the alias when converting from the database row


class CreateTransaction(BaseModel):
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    accountId: int


class BillPaymentInitiated(BaseModel):
    eventType: str = "BillPaymentInitiated"
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    accountId: int
    timestamp: float


class RecurringPaymentScheduled(BaseModel):
    eventType: str = "RecurringPaymentScheduled"
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    accountId: int
    frequency: str = Field(min_length=1)
    startDate: str = Field(min_length=1)
    timestamp: float


class BillPaymentCancelled(BaseModel):
    eventType: str = "BillPaymentCancelled"
    billId: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    timestamp: float


class PaymentDueNotificationEvent(BaseModel):
    eventType: str = "PaymentDueNotificationEvent"
    billId: str = Field(min_length=1)
    accountId: int
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    timestamp: float


class LedgerRecord(BaseModel):
    account_id: int
    current_balance: float


class BillPaymentInitiatedFromAcct(BaseModel):
    eventType: str = "BillPaymentInitiatedFromAcct"
    transactionId: str
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    accountId: int
    timestamp: float


class BillPaymentInitiatedToAcct(BaseModel):
    eventType: str = "BillPaymentInitiatedToAcct"
    transactionId: str
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    accountId: int
    timestamp: float


# This is a model for the response from the accounts service
class AccountType(BaseModel):
    id: int
    account_type: str


EVENT_MODELS = {
    "BillPaymentInitiated": BillPaymentInitiated,
    "BillPaymentInitiatedFromAcct": BillPaymentInitiatedFromAcct,
    "BillPaymentInitiatedToAcct": BillPaymentInitiatedToAcct,
    "RecurringPaymentScheduled": RecurringPaymentScheduled,
    "BillPaymentCancelled": BillPaymentCancelled,
    "PaymentDueNotificationEvent": PaymentDueNotificationEvent,
}

# Global database connection, Kafka producer, and consumer task
producer = None
consumer_task = None
db_connection = None


def get_db_connection():
    """
    Returns a new database connection.
    """
    try:
        cnxn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
        logging.info("Successfully connected to MSSQL database.")
        return cnxn
    except Exception as e:
        raise ConnectionError(f"Failed to connect to {DB_DATABASE} database: {e}")


async def get_account_type(account_id: int):
    """
    Makes an API call to the accounts service to get the account type.
    """
    accounts_service_url = os.getenv("ACCOUNTS_SERVICE_URL", "http://accounts-service:5000")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{accounts_service_url}/account/type/{account_id}")
            response.raise_for_status()
            return AccountType(**response.json()).account_type
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                logging.error(f"Account with ID '{account_id}' not found in accounts service.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Account with ID '{account_id}' not found in accounts service.",
                )
            else:
                logging.error(f"Unexpected error from accounts service: {e}")
                raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        except RequestError as e:
            logging.error(f"Failed to connect to accounts service: {e}")
            raise HTTPException(status_code=503, detail="Accounts service is unavailable.")


async def start_kafka_consumer():
    """
    Connects to Kafka, consumes messages, and writes them to MSSQL.
    Runs as a background task.
    """
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:29092")

    retries = 5
    delay = 1
    consumer = None
    for i in range(retries):
        try:
            logging.info(f"Attempting to connect Kafka consumer (attempt {i + 1}/{retries})...")
            consumer = AIOKafkaConsumer(
                "bill_payments",
                "recurring_payments",
                "payment_cancellations",
                "payment_due_notifications",
                bootstrap_servers=kafka_broker,
                group_id="transaction-consumer-group",
                auto_offset_reset="earliest",
            )
            await consumer.start()
            logging.info("Consumer connected successfully. Waiting for messages...")
            break
        except Exception as e:
            logging.error(f"Kafka connection error: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2
    else:
        logging.error("Failed to connect to Kafka after multiple retries. Consumer will not run.")
        return

    try:
        cursor = db_connection.cursor()
        async for message in consumer:
            message_value = json.loads(message.value.decode("utf-8"))
            event_type = message_value.get("eventType")

            if event_type not in EVENT_MODELS:
                logging.warning(f"Unknown eventType '{event_type}'. Skipping message.")
                continue

            try:
                event_model = EVENT_MODELS[event_type](**message_value)
                logging.info(f"Received valid event: {event_type} on topic {message.topic}")

            except ValidationError as e:
                logging.warning(f"Message failed Pydantic validation: {e.errors()}. Skipping message.")
                continue

            try:
                if event_type == "BillPaymentInitiatedFromAcct":
                    # Log the debit to the ledger
                    cursor.execute(
                        """
                        UPDATE Ledger SET CurrentBalance = CurrentBalance - ? WHERE AccountID = ?
                        IF @@ROWCOUNT = 0
                        INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (?, ?)
                    """,
                        event_model.amount,
                        event_model.accountId,
                        event_model.accountId,
                        -event_model.amount,
                    )
                    db_connection.commit()
                    logging.info(f"Debited {event_model.amount} from account {event_model.accountId} in Ledger.")

                    # Insert into Transactions table
                    cursor.execute(
                        """
                        INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        event_model.eventType,
                        event_model.billId,
                        event_model.amount,
                        event_model.currency,
                        event_model.accountId,
                        event_model.timestamp,
                    )
                    db_connection.commit()
                    logging.info(f"Debit transaction {event_model.billId} recorded in Transactions table.")
                elif event_type == "BillPaymentInitiatedToAcct":
                    account_type = await get_account_type(event_model.accountId)
                    if account_type in ["loan", "credit"]:
                        # Payment to a loan/credit account is a debit to the balance
                        cursor.execute(
                            """
                            UPDATE Ledger SET CurrentBalance = CurrentBalance - ? WHERE AccountID = ?
                            IF @@ROWCOUNT = 0
                            INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (?, ?)
                        """,
                            event_model.amount,
                            event_model.accountId,
                            event_model.accountId,
                            -event_model.amount,
                        )
                        db_connection.commit()
                        logging.info(
                            f"Debited {event_model.amount} from loan/credit account {event_model.accountId} in Ledger."
                        )
                    else:
                        # Payment to a checking/savings account is a credit
                        cursor.execute(
                            """
                            UPDATE Ledger SET CurrentBalance = CurrentBalance + ? WHERE AccountID = ?
                            IF @@ROWCOUNT = 0
                            INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (?, ?)
                        """,
                            event_model.amount,
                            event_model.accountId,
                            event_model.accountId,
                            event_model.amount,
                        )
                        db_connection.commit()
                        logging.info(f"Credited {event_model.amount} to account {event_model.accountId} in Ledger.")

                    # Insert into Transactions table
                    cursor.execute(
                        """
                        INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        event_model.eventType,
                        event_model.billId,
                        event_model.amount,
                        event_model.currency,
                        event_model.accountId,
                        event_model.timestamp,
                    )
                    db_connection.commit()
                    logging.info(f"Credit transaction {event_model.billId} recorded in Transactions table.")
                elif event_type == "RecurringPaymentScheduled":
                    cursor.execute(
                        """
                        INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        event_model.eventType,
                        event_model.billId,
                        event_model.amount,
                        event_model.currency,
                        event_model.accountId,
                        event_model.timestamp,
                    )
                    db_connection.commit()
                    logging.info(f"Recurring payment scheduled for bill ID {event_model.billId} and inserted.")
                elif event_type == "BillPaymentCancelled":
                    # Update the existing transaction record
                    cursor.execute(
                        """
                        UPDATE Transactions SET EventType = ?, CancellationUserID = ?, CancellationTimestamp = ?
                        WHERE BillID = ?
                    """,
                        event_model.eventType,
                        event_model.user_id,
                        event_model.timestamp,
                        event_model.billId,
                    )
                    db_connection.commit()
                    logging.info(f"Payment for bill ID {event_model.billId} cancelled and updated.")
                elif event_type == "PaymentDueNotificationEvent":
                    # This event signals that a recurring payment is due
                    logging.info(
                        f"Received 'PaymentDueNotificationEvent' for bill ID {event_model.billId}. Simulating payment initiation..."
                    )

                    # Publish a new event to the `bill_payments` topic
                    # This event will be consumed by this service again to be recorded as a regular payment
                    payment_init_event = {
                        "eventType": "BillPaymentInitiatedFromAcct",
                        "billId": event_model.billId,
                        "amount": event_model.amount,
                        "currency": event_model.currency,
                        "accountId": event_model.accountId,
                        "timestamp": time.time(),
                    }
                    message_bytes = json.dumps(payment_init_event).encode("utf-8")
                    # Send the new event to the Kafka topic
                    await producer.send_and_wait("bill_payments", message_bytes)

                logging.info(f"Database write successful for event {event_model.eventType}.")
            except Exception as e:
                logging.error(f"Database write error: {e}")
                continue

    except Exception as e:
        logging.error(f"An error occurred while consuming message: {e}")
    finally:
        if consumer:
            await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Initializes database and Kafka producer/consumer.
    """
    global producer, consumer_task, db_connection

    # --- Database Connection Logic (Startup) ---
    retries = 10
    delay = 3
    cnxn_master = None
    for i in range(retries):
        try:
            logging.info(f"Attempting to connect to 'master' database (attempt {i + 1}/{retries})...")
            cnxn_master = pyodbc.connect(CONNECTION_STRING_MASTER)
            cursor = cnxn_master.cursor()
            cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{DB_DATABASE}'")
            if cursor.fetchone():
                cnxn_master.close()
                db_connection = get_db_connection()
                break
            else:
                logging.warning(f"Database '{DB_DATABASE}' not yet created. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 1.5
        except Exception as e:
            logging.error(f"Master database connection error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 1.5
    else:
        logging.error("Failed to connect to master database after multiple retries. The application will not start.")
        raise ConnectionError("Failed to connect to MSSQL during startup.")

    # --- Kafka Producer and Consumer Logic (Startup) ---
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:29092")
    retries = 5
    delay = 1
    for i in range(retries):
        try:
            logging.info(f"Attempting to connect Kafka producer (attempt {i + 1}/{retries})...")
            producer = AIOKafkaProducer(bootstrap_servers=kafka_broker)
            await producer.start()
            logging.info("Kafka producer connected successfully.")
            break
        except Exception as e:
            logging.warning(f"Producer connection error: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2
    else:
        logging.error("Failed to connect producer after multiple retries. API will not publish messages.")
        producer = None

    # Start the consumer in a background task
    consumer_task = asyncio.create_task(start_kafka_consumer())

    yield

    # --- Shutdown Logic ---
    if producer:
        await producer.stop()
        logging.info("Kafka producer stopped.")
    if consumer_task:
        consumer_task.cancel()
        logging.info("Consumer task cancelled.")
    if db_connection:
        db_connection.close()
        logging.info("Database connection closed.")


app = FastAPI(
    title="Relibank Transaction Service",
    description="Manages Relibank transactions via API and event processing.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/transactions", response_model=List[TransactionRecord])
async def get_transactions():
    """
    Retrieves all transactions from the database.
    """
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database connection failed.")

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM Transactions")
        columns = [column[0] for column in cursor.description]
        transactions = [TransactionRecord(**dict(zip(columns, row))) for row in cursor.fetchall()]
        logging.info(f"Retrieved {len(transactions)} transactions.")
        return transactions
    except Exception as e:
        logging.error(f"Error retrieving transactions: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving transactions.")


@app.get("/transaction/{bill_id}", response_model=TransactionRecord)
async def get_transaction(bill_id: str):
    """
    Retrieves a single transaction by its BillID.
    """
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database connection failed.")

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT TOP 1 * FROM Transactions WHERE BillID = ?", bill_id)
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        columns = [column[0] for column in cursor.description]
        transaction = TransactionRecord(**dict(zip(columns, row)))
        logging.info(f"Retrieved transaction for BillID: {bill_id}")
        return transaction
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving transaction: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving transaction.")


@app.get("/ledger/{account_id}", response_model=LedgerRecord)
async def get_ledger_balance(account_id: int):
    """
    Retrieves the current balance for a specific account from the Ledger table.
    """
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database connection failed.")

    try:
        cursor = db_connection.cursor()
        cursor.execute(
            "SELECT AccountID AS account_id, CurrentBalance AS current_balance FROM Ledger WHERE AccountID = ?",
            account_id,
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Account not found in ledger.")

        balance_record = {"account_id": row[0], "current_balance": float(row[1])}
        logging.info(f"Retrieved ledger balance for account {account_id}")
        return LedgerRecord(**balance_record)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving ledger balance: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving ledger balance.")
    finally:
        pass


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
