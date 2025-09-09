import asyncio
import os
import json
import logging
import pyodbc
from aiokafka import AIOKafkaProducer
from datetime import date, timedelta
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Optional, List
import schedule
import time
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

# Global Kafka producer and database connection
producer = None
db_connection = None

def get_db_connection():
    """
    Returns a new database connection.
    """
    try:
        cnxn = pyodbc.connect(CONNECTION_STRING)
        logging.info("Successfully connected to MSSQL database.")
        return cnxn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        raise

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

@newrelic.agent.background_task()
async def check_for_due_payments():
    """
    Checks the database for recurring payments due today and triggers events.
    """
    global db_connection
    try:
        if not db_connection:
            db_connection = get_db_connection()
            
        cursor = db_connection.cursor()
        
        today_date = date.today().strftime('%Y-%m-%d')
        logging.info(f"Checking for recurring payments due today: {today_date}")
        
        cursor.execute("""
            SELECT BillID, AccountID, Amount, Currency
            FROM RecurringSchedules
            WHERE StartDate = ?
        """, today_date)
        
        due_payments = cursor.fetchall()
        
        if not due_payments:
            logging.info("No recurring payments due today.")
            return

        for payment in due_payments:
            bill_id, account_id, amount, currency = payment
            logging.info(f"Payment for bill {bill_id} is due. Triggering event.")
            
            event = PaymentDueNotificationEvent(
                transactionId=str(uuid.uuid4()),
                billId=bill_id,
                accountId=account_id,
                amount=float(amount),
                currency=currency,
                timestamp=time.time()
            ).model_dump()
            
            await send_event("payment_due_notifications", event)

        db_connection.commit()
    except Exception as e:
        logging.error(f"Error checking for due payments: {e}")
        
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
