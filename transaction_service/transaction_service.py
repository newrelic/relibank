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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        populate_by_name = True # This tells Pydantic to use the alias when converting from the database row

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

EVENT_MODELS = {
    "BillPaymentInitiated": BillPaymentInitiated,
    "RecurringPaymentScheduled": RecurringPaymentScheduled,
    "BillPaymentCancelled": BillPaymentCancelled
}

# Global database connection, Kafka producer, and consumer task
producer = None
consumer_task = None

def get_db_connection():
    """
    Returns a new database connection with retry logic.
    """
    retries = 5
    delay = 5
    for i in range(retries):
        try:
            cnxn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
            logging.info("Successfully connected to MSSQL database.")
            return cnxn
        except Exception as e:
            logging.error(f"Database connection error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2
    
    raise ConnectionError("Failed to connect to MSSQL database after multiple retries.")

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
            logging.info(f"Attempting to connect Kafka consumer (attempt {i+1}/{retries})...")
            consumer = AIOKafkaConsumer(
                'bill_payments',
                'recurring_payments',
                'payment_cancellations',
                bootstrap_servers=kafka_broker,
                group_id='transaction-consumer-group',
                auto_offset_reset='earliest'
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
        cnxn = get_db_connection()
        cursor = cnxn.cursor()
        async for message in consumer:
            message_value = json.loads(message.value.decode('utf-8'))
            event_type = message_value.get('eventType')

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
                if event_type == 'BillPaymentInitiated':
                    cursor.execute("""
                        INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, event_model.eventType, event_model.billId, event_model.amount,
                       event_model.currency, event_model.accountId, event_model.timestamp)
                elif event_type == 'RecurringPaymentScheduled':
                    cursor.execute("""
                        INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, event_model.eventType, event_model.billId, event_model.amount,
                       event_model.currency, event_model.accountId, event_model.timestamp)
                elif event_type == 'BillPaymentCancelled':
                    # Update the existing transaction record
                    cursor.execute("""
                        UPDATE Transactions SET EventType = ?, CancellationUserID = ?, CancellationTimestamp = ?
                        WHERE BillID = ?
                    """, event_model.eventType, event_model.user_id, event_model.timestamp, event_model.billId)
                
                cnxn.commit()
                logging.info(f"Database write successful for event {event_model.eventType}.")
            except Exception as e:
                logging.error(f"Database write error: {e}")
                # In a real-world scenario, you might send this to a DLQ topic.
                continue

    except Exception as e:
        logging.error(f"An error occurred while consuming message: {e}")
    finally:
        if consumer:
            await consumer.stop()
        if cnxn:
            cnxn.close()
        logging.info("Consumer and database connection stopped.")

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
            logging.info(f"Attempting to connect to 'master' database (attempt {i+1}/{retries})...")
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
            logging.info(f"Attempting to connect Kafka producer (attempt {i+1}/{retries})...")
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
    lifespan=lifespan
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
        cnxn = get_db_connection()
        cursor = cnxn.cursor()
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
    finally:
        cnxn.close()

@app.post("/transaction", status_code=201)
async def create_transaction(transaction_details: CreateTransaction):
    """
    Creates a new transaction by publishing an event to Kafka.
    """
    if not producer:
        raise HTTPException(status_code=503, detail="Kafka producer is not connected.")

    logging.info(f"Received API request to create transaction for billId: {transaction_details.billId}")

    try:
        kafka_message = {
            "eventType": "BillPaymentInitiated",
            "billId": transaction_details.billId,
            "amount": transaction_details.amount,
            "currency": transaction_details.currency,
            "accountId": transaction_details.accountId,
            "timestamp": time.time()
        }
        message_bytes = json.dumps(kafka_message).encode('utf-8')
        await producer.send_and_wait("bill_payments", message_bytes)
        logging.info("Transaction initiation event successfully published to Kafka.")
    except Exception as e:
        logging.error(f"Failed to publish message to Kafka: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish transaction event.")
    
    return {"status": "success", "message": "Transaction event published successfully."}

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
