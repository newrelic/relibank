import asyncio
import os
import json
import logging
import threading
import pyodbc
from aiokafka import AIOKafkaProducer
from datetime import date, timedelta
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Optional, List
import schedule
import time
import uuid
import newrelic.agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

newrelic.agent.initialize()

# Database connection details from environment variables
DB_SERVER = os.getenv("DB_SERVER", "mssql")
DB_DATABASE = os.getenv("DB_DATABASE", "RelibankDB")
DB_USERNAME = os.getenv("DB_USERNAME", "SA")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrong@Password!")
CONNECTION_STRING = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD};TrustServerCertificate=yes"

# Kafka broker details
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:29092")

# Pydantic models for data validation
class RecurringPaymentScheduled(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    eventType: str = Field(min_length=1)
    billId: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    accountId: int
    frequency: str = Field(min_length=1)
    startDate: str = Field(min_length=1)
    timestamp: float

class PaymentDueNotificationEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    eventType: str = "PaymentDueNotificationEvent"
    transactionId: str
    billId: str = Field(min_length=1)
    accountId: int
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3)
    timestamp: float


def add_nr_event_attributes(model: BaseModel) -> None:
    """Add all non-timestamp fields from a Pydantic model as NR custom attributes."""
    attrs = [
        (field_name, value)
        for field_name, value in model.model_dump().items()
        if "timestamp" not in field_name.lower() and value is not None
    ]
    newrelic.agent.add_custom_attributes(attrs)

# Global Kafka producer and database connection
producer = None
db_connection = None
_db_connection_lock = threading.Lock()  # see CLAUDE.md: serializes access to the shared connection

def get_db_connection():
    """
    Returns a new database connection.
    """
    try:
        cnxn = pyodbc.connect(CONNECTION_STRING, timeout=10)
        logging.info("Successfully connected to MSSQL database.")
        return cnxn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        raise


def _ensure_db_connection():
    global db_connection
    if db_connection is None:
        db_connection = get_db_connection()
    return db_connection


def _reset_db_connection():
    """Drop the shared connection so the next call reconnects, instead of reusing a
    connection left in a bad state by a dropped network/MSSQL restart/query failure."""
    global db_connection
    with _db_connection_lock:
        if db_connection is not None:
            try:
                db_connection.close()
            except Exception:
                pass
        db_connection = None

@newrelic.agent.background_task()
async def send_event(topic: str, event: dict):
    """
    Asynchronously sends a message to a Kafka topic.
    """
    if producer:
        try:
            message_bytes = json.dumps(event).encode('utf-8')
            await producer.send_and_wait(topic, message_bytes)
            logging.info(f"Event successfully published to Kafka topic '{topic}'.")
        except Exception as e:
            logging.error(f"Failed to send event to Kafka: {e}")
    else:
        logging.warning("Kafka producer not initialized. Skipping event.")

def _fetch_due_payments() -> list:
    """Synchronous DB work for check_for_due_payments -- run off the event loop via
    asyncio.to_thread so a slow/stuck query doesn't block every other scheduled job."""
    with _db_connection_lock:
        conn = _ensure_db_connection()
        cursor = conn.cursor()

        today_date = date.today().strftime('%Y-%m-%d')
        logging.info(f"Checking for recurring payments due today: {today_date}")

        # sp_ProcessDueRecurringPayments posts a Transactions/Ledger entry for each due
        # schedule and marks it processed, so it only ever returns rows that were
        # actually posted *this call* — the scheduler's 1-minute poll loop would
        # otherwise re-notify (and, before this procedure existed, never actually
        # paid) the same due schedule every minute all day.
        cursor.execute("{CALL dbo.sp_ProcessDueRecurringPayments (?)}", today_date)
        due_payments = cursor.fetchall()
        conn.commit()
        return due_payments


@newrelic.agent.background_task()
async def check_for_due_payments():
    """
    Checks the database for recurring payments due today and triggers events.
    """
    try:
        due_payments = await asyncio.to_thread(_fetch_due_payments)
    except Exception as e:
        logging.error(f"Error checking for due payments: {e}")
        _reset_db_connection()
        return

    newrelic.agent.add_custom_attribute("due_payments_count", len(due_payments))

    if not due_payments:
        logging.info("No recurring payments due today.")
        return

    for payment in due_payments:
        _schedule_id, bill_id, account_id, amount, currency = payment
        logging.info(f"Payment for bill {bill_id} is due. Triggering event.")

        event_model = PaymentDueNotificationEvent(
            transactionId=str(uuid.uuid4()),
            billId=bill_id,
            accountId=account_id,
            amount=float(amount),
            currency=currency,
            timestamp=time.time()
        )
        add_nr_event_attributes(event_model)
        await send_event("payment_due_notifications", event_model.model_dump())

def _run_spending_velocity_sample_sync() -> None:
    with _db_connection_lock:
        conn = _ensure_db_connection()
        cursor = conn.cursor()
        cursor.execute("{CALL dbo.sp_CalculateSpendingVelocity (?)}", 6)
        while cursor.fetchmany(2000):
            pass
        conn.commit()


@newrelic.agent.background_task()
async def run_spending_velocity_sample():
    """Periodically exercises sp_CalculateSpendingVelocity so it keeps showing recent
    activity in New Relic's QPM/Stored Procedures panels. @Months and the fetchmany loop
    are both load-bearing -- see scheduler_service/CLAUDE.md."""
    try:
        await asyncio.to_thread(_run_spending_velocity_sample_sync)
        logging.info("Ran sp_CalculateSpendingVelocity sample.")
    except Exception as e:
        logging.error(f"Error running spending velocity sample: {e}")
        _reset_db_connection()


def _run_ledger_rebuild_sample_sync() -> None:
    with _db_connection_lock:
        conn = _ensure_db_connection()
        cursor = conn.cursor()
        cursor.execute("{CALL dbo.sp_RebuildAccountLedgerBalance (?)}", None)
        while cursor.fetchmany(2000):
            pass
        conn.commit()


@newrelic.agent.background_task()
async def run_ledger_rebuild_sample():
    """Periodically exercises sp_RebuildAccountLedgerBalance across all accounts, same
    rationale as run_spending_velocity_sample above."""
    try:
        await asyncio.to_thread(_run_ledger_rebuild_sample_sync)
        logging.info("Ran sp_RebuildAccountLedgerBalance sample.")
    except Exception as e:
        logging.error(f"Error running ledger rebuild sample: {e}")
        _reset_db_connection()

async def scheduler_loop():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

@newrelic.agent.background_task()
async def main():
    """
    The main asynchronous loop for the scheduler.
    """
    global producer
    
    # Initialize Kafka producer
    retries = 5
    delay = 1
    for i in range(retries):
        try:
            logging.info(f"Attempting to connect Kafka producer (attempt {i+1}/{retries})...")
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKER)
            await producer.start()
            logging.info("Kafka producer connected successfully.")
            break
        except Exception as e:
            logging.warning(f"Producer connection error: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2
    else:
        logging.error("Failed to connect to Kafka after multiple retries. The scheduler will not run.")
        return

    # Schedule the job to run every minute for the demo
    schedule.every(1).minutes.do(lambda: asyncio.create_task(check_for_due_payments()))
    schedule.every(5).minutes.do(lambda: asyncio.create_task(run_spending_velocity_sample()))
    schedule.every(5).minutes.do(lambda: asyncio.create_task(run_ledger_rebuild_sample()))

    logging.info("Scheduler started. Waiting for jobs...")
    try:
        await scheduler_loop()
    except asyncio.CancelledError:
        logging.info("Scheduler loop cancelled.")
    finally:
        if producer:
            await producer.stop()
            logging.info("Kafka producer stopped.")

if __name__ == '__main__':
    asyncio.run(main())
