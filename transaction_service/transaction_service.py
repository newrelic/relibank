import asyncio
import os
import json
import logging
import pyodbc
import datetime
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
import time
import httpx
from httpx import HTTPStatusError, RequestError
import newrelic.agent
from utils.process_headers import process_headers

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


class RecurringScheduleRecord(BaseModel):
    # Mapping SQL column names to Pydantic field names for RecurringSchedules table
    schedule_id: int = Field(alias="ScheduleID")
    bill_id: str = Field(alias="BillID")
    account_id: int = Field(alias="AccountID")
    amount: float = Field(alias="Amount")
    currency: str = Field(alias="Currency")
    frequency: str = Field(alias="Frequency")
    start_date: str = Field(alias="StartDate")
    timestamp: float = Field(alias="Timestamp")
    cancellation_user_id: Optional[str] = Field(None, alias="CancellationUserID")
    cancellation_timestamp: Optional[float] = Field(None, alias="CancellationTimestamp")

    class Config:
        populate_by_name = True


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
                elif event_type == 'RecurringPaymentScheduled':
                    # This event is a schedule, so insert it into the RecurringSchedules table
                    cursor.execute("""
                        INSERT INTO RecurringSchedules (BillID, AccountID, Amount, Currency, Frequency, StartDate, Timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, event_model.billId, 
                        event_model.accountId, 
                        event_model.amount,
                        event_model.currency, 
                        event_model.frequency, 
                        event_model.startDate, 
                        event_model.timestamp)
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


@app.get("/transaction-service/transactions", response_model=List[TransactionRecord])
async def get_transactions(request: Request):
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
        process_headers(dict(request.headers))
        return transactions
    except Exception as e:
        logging.error(f"Error retrieving transactions: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving transactions.")


@app.get("/transaction-service/transaction/{bill_id}", response_model=TransactionRecord)
async def get_transaction(bill_id: str, request: Request):
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
        process_headers(dict(request.headers))
        return transaction
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving transaction: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving transaction.")


@app.get("/transaction-service/recurring-payments", response_model=List[RecurringScheduleRecord])
async def get_recurring_payments(request: Request):
    """
    Retrieves all recurring payments from the database.
    """
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database connection failed.")

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM RecurringSchedules")
        columns = [column[0] for column in cursor.description]

        schedules = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            # Convert StartDate from datetime.date to string
            if 'StartDate' in row_dict and row_dict['StartDate']:
                row_dict['StartDate'] = row_dict['StartDate'].strftime('%Y-%m-%d')
            schedules.append(RecurringScheduleRecord(**row_dict))

        logging.info(f"Retrieved {len(schedules)} recurring payments.")
        process_headers(dict(request.headers))
        return schedules
    except Exception as e:
        logging.error(f"Error retrieving recurring payments: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving recurring payments.")


@app.get("/transaction-service/ledger/{account_id}", response_model=LedgerRecord)
async def get_ledger_balance(account_id: int, request: Request):
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
        process_headers(dict(request.headers))
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

@app.get("/transaction-service/blocking")
async def create_blocking_scenario(delay_seconds: int = 30, request: Request = None):
    """
    Creates a blocking scenario on the Transactions table.
    Starts a transaction, locks a row, and holds it for the specified delay.
    This simulates blocking behavior for monitoring and testing purposes.
    """
    if delay_seconds < 1 or delay_seconds > 300:
        raise HTTPException(status_code=400, detail="delay_seconds must be between 1 and 300")

    if not db_connection:
        raise HTTPException(status_code=503, detail="Database connection failed.")

    # Create a new connection without autocommit for transaction control
    blocking_connection = None
    try:
        logging.info(f"Starting blocking scenario with {delay_seconds} second delay...")

        # Create connection without autocommit to control transactions manually
        blocking_connection = pyodbc.connect(CONNECTION_STRING, autocommit=False)
        cursor = blocking_connection.cursor()

        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")

        # First, ensure we have a transaction to lock
        # Check if BILL-1701 exists, if not create it
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM Transactions WHERE BillID = 'BILL-1701' AND EventType = 'BillPaymentInitiated')
            BEGIN
                INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp)
                VALUES ('BillPaymentInitiated', 'BILL-1701', 125.50, 'USD', 12345, DATEDIFF(s, '1970-01-01', GETUTCDATE()))
            END
        """)

        # First, SELECT and lock the row - this acquires and holds the lock
        # The lock will be held throughout the transaction until COMMIT
        cursor.execute("""
            SELECT TOP 1 TransactionID, BillID, Amount
            FROM Transactions WITH (UPDLOCK, ROWLOCK, HOLDLOCK)
            WHERE BillID = 'BILL-1701'
            AND EventType = 'BillPaymentInitiated'
            ORDER BY TransactionID DESC
        """)
        row = cursor.fetchone()

        if not row:
            cursor.execute("ROLLBACK TRANSACTION")
            blocking_connection.rollback()
            raise HTTPException(status_code=404, detail="No BILL-1701 transaction found to lock")

        transaction_id = row[0]
        bill_id = row[1]
        amount = row[2]

        logging.info(f"Locked TransactionID {transaction_id} (BillID: {bill_id}). Holding lock for {delay_seconds} seconds...")

        # Now update the locked row (lock is already held from the SELECT above)
        cursor.execute("""
            UPDATE Transactions
            SET Amount = Amount + 0.01
            WHERE TransactionID = ?
        """, transaction_id)

        # Hold the lock for the specified duration
        # The lock remains held because we're still in the transaction
        delay_formatted = f"00:{delay_seconds // 60:02d}:{delay_seconds % 60:02d}"
        cursor.execute(f"WAITFOR DELAY '{delay_formatted}'")

        # Commit the transaction to release the lock
        cursor.execute("COMMIT TRANSACTION")
        blocking_connection.commit()

        logging.info(f"Blocking scenario completed. Lock released on TransactionID {transaction_id}.")

        if request:
            process_headers(dict(request.headers))

        return {
            "status": "completed",
            "message": f"Blocking scenario executed successfully",
            "locked_transaction_id": transaction_id,
            "locked_bill_id": bill_id,
            "delay_seconds": delay_seconds
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during blocking scenario: {e}")
        if blocking_connection:
            try:
                cursor.execute("ROLLBACK TRANSACTION")
                blocking_connection.rollback()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error creating blocking scenario: {str(e)}")
    finally:
        if blocking_connection:
            try:
                blocking_connection.close()
                logging.info("Blocking connection closed.")
            except:
                pass


@app.post("/transaction-service/adjust-amount/{bill_id}")
async def adjust_transaction_amount(bill_id: str, adjustment: float = 0.01, request: Request = None):
    """
    Adjusts the amount of the most recent transaction for a given bill.
    Used for processing fee adjustments or corrections.
    Each request creates its own connection to ensure proper blocking detection.
    """
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database connection failed.")

    # Create a new connection for this request to ensure blocking works properly
    adjust_connection = None
    try:
        adjust_connection = pyodbc.connect(CONNECTION_STRING, autocommit=False)
        cursor = adjust_connection.cursor()

        # Begin transaction explicitly
        cursor.execute("BEGIN TRANSACTION")

        # Update the most recent transaction for this bill
        # Use UPDLOCK in subquery to prevent deadlocks when multiple sessions update
        cursor.execute("""
            UPDATE Transactions
            SET Amount = Amount + ?
            WHERE TransactionID = (
                SELECT TOP 1 TransactionID
                FROM Transactions WITH (UPDLOCK)
                WHERE BillID = ?
                AND EventType = 'BillPaymentInitiated'
                ORDER BY TransactionID DESC
            )
        """, adjustment, bill_id)

        affected_rows = cursor.rowcount

        if affected_rows == 0:
            cursor.execute("ROLLBACK TRANSACTION")
            adjust_connection.rollback()
            raise HTTPException(status_code=404, detail=f"No transaction found for bill {bill_id}")

        cursor.execute("COMMIT TRANSACTION")
        adjust_connection.commit()

        logging.info(f"Adjusted amount by {adjustment} for bill {bill_id}")

        if request:
            process_headers(dict(request.headers))

        return {
            "status": "success",
            "message": f"Transaction amount adjusted by ${adjustment}",
            "bill_id": bill_id,
            "affected_rows": affected_rows
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adjusting transaction amount: {e}")
        if adjust_connection:
            try:
                adjust_connection.rollback()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error adjusting amount: {str(e)}")
    finally:
        if adjust_connection:
            try:
                adjust_connection.close()
            except:
                pass


@app.get("/transaction-service/slow-query")
async def generate_slow_query(query_type: str = "summary", delay_seconds: int = 3, request: Request = None):
    """
    Generates an intentionally slow query for testing/demo purposes.
    This endpoint helps demonstrate New Relic's slow query detection.

    Query types:
    - summary: Transaction summary by EventType with aggregations
    - account_analysis: Account-level analysis with subqueries
    - window_functions: Running totals and moving averages
    - self_join: Duplicate detection via self-join
    - complex_filter: Full table scan with complex WHERE clause
    """
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database connection failed.")

    if delay_seconds < 1 or delay_seconds > 60:
        raise HTTPException(status_code=400, detail="delay_seconds must be between 1 and 60")

    delay_formatted = f"00:{delay_seconds // 60:02d}:{delay_seconds % 60:02d}"

    try:
        cursor = db_connection.cursor()
        start_time = datetime.datetime.now()

        if query_type == "summary":
            # Transaction summary report with delay
            cursor.execute(f"""
                SELECT
                    EventType,
                    COUNT(*) AS TransactionCount,
                    SUM(Amount) AS TotalAmount,
                    AVG(Amount) AS AvgAmount,
                    MIN(Amount) AS MinAmount,
                    MAX(Amount) AS MaxAmount,
                    COUNT(DISTINCT BillID) AS UniqueBills,
                    COUNT(DISTINCT AccountID) AS UniqueAccounts
                FROM Transactions
                GROUP BY EventType
                ORDER BY TotalAmount DESC
                WAITFOR DELAY '{delay_formatted}';
            """)
            results = cursor.fetchall()

        elif query_type == "account_analysis":
            # Inefficient subquery pattern
            cursor.execute(f"""
                SELECT TOP 50
                    AccountID,
                    (SELECT COUNT(*) FROM Transactions t WHERE t.AccountID = main.AccountID) AS TotalTransactions,
                    (SELECT SUM(Amount) FROM Transactions t WHERE t.AccountID = main.AccountID) AS TotalSpent,
                    (SELECT MAX(Amount) FROM Transactions t WHERE t.AccountID = main.AccountID) AS LargestTransaction
                FROM (SELECT DISTINCT AccountID FROM Transactions) main
                WAITFOR DELAY '{delay_formatted}';
            """)
            results = cursor.fetchall()

        elif query_type == "window_functions":
            # Window functions for running totals
            cursor.execute(f"""
                SELECT TOP 100
                    TransactionID,
                    AccountID,
                    EventType,
                    Amount,
                    SUM(Amount) OVER (PARTITION BY AccountID ORDER BY TransactionID) AS RunningTotal,
                    AVG(Amount) OVER (PARTITION BY AccountID ORDER BY TransactionID ROWS BETWEEN 10 PRECEDING AND CURRENT ROW) AS MovingAvg,
                    ROW_NUMBER() OVER (PARTITION BY AccountID ORDER BY Amount DESC) AS AmountRank
                FROM Transactions
                WHERE EventType IN ('BillPaymentInitiated', 'BillPaymentCompleted')
                WAITFOR DELAY '{delay_formatted}';
            """)
            results = cursor.fetchall()

        elif query_type == "self_join":
            # Self-join for duplicate detection
            cursor.execute(f"""
                SELECT TOP 50
                    t1.TransactionID AS Transaction1,
                    t2.TransactionID AS Transaction2,
                    t1.BillID,
                    t1.Amount,
                    t1.AccountID,
                    ABS(t1.Amount - t2.Amount) AS AmountDifference
                FROM Transactions t1
                INNER JOIN Transactions t2
                    ON t1.BillID = t2.BillID
                    AND t1.AccountID = t2.AccountID
                    AND t1.TransactionID < t2.TransactionID
                WHERE ABS(t1.Amount - t2.Amount) < 1.00
                WAITFOR DELAY '{delay_formatted}';
            """)
            results = cursor.fetchall()

        elif query_type == "complex_filter":
            # Full table scan with complex WHERE clause
            cursor.execute(f"""
                SELECT TOP 100 *
                FROM Transactions
                WHERE Amount > 100.00
                    AND LEN(BillID) > 10
                    AND Currency IN ('USD', 'EUR')
                    AND EventType LIKE '%Payment%'
                ORDER BY Amount DESC, TransactionID DESC
                WAITFOR DELAY '{delay_formatted}';
            """)
            results = cursor.fetchall()

        else:
            raise HTTPException(status_code=400, detail=f"Unknown query_type: {query_type}")

        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        logging.info(f"Slow query ({query_type}) completed in {duration:.2f} seconds")

        if request:
            process_headers(dict(request.headers))

        return {
            "status": "success",
            "message": f"Slow query executed successfully",
            "query_type": query_type,
            "delay_seconds": delay_seconds,
            "actual_duration_seconds": round(duration, 2),
            "rows_returned": len(results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error executing slow query: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing slow query: {str(e)}")


@app.get("/transaction-service")
async def ok():
    """Root return 200"""
    return "ok"

@app.get("/transaction-service/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
