import asyncio
import os
import json
import logging
import time
from datetime import datetime
from aiokafka import AIOKafkaProducer
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details from environment variables
DB_SERVER = os.getenv("DB_SERVER", "mssql")
DB_DATABASE = os.getenv("DB_DATABASE", "RelibankDB")
DB_USERNAME = os.getenv("DB_USERNAME", "SA")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrong@Password!")

# SQLAlchemy connection string for pymssql (no ODBC drivers needed)
CONNECTION_STRING = f"mssql+pymssql://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}/{DB_DATABASE}"
CONNECTION_STRING_MASTER = f"mssql+pymssql://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}/master"

# TODO "you have an upcoming payment due in 2 days", track future payment dates

# Global Kafka producer and database engine
producer = None
db_engine = None

def get_db_engine():
    """
    Returns SQLAlchemy engine for database connections.
    """
    global db_engine
    if db_engine is None:
        try:
            db_engine = create_engine(
                CONNECTION_STRING,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
            logging.info("Successfully created SQLAlchemy engine for MSSQL database.")
        except Exception as e:
            logging.error(f"Failed to create database engine: {e}")
            raise ConnectionError(f"Failed to connect to {DB_DATABASE} database: {e}")
    return db_engine

async def check_and_trigger_payments():
    """
    A background task that checks for and triggers due payments from the database.
    """
    global producer

    # Ensure producer is connected
    if not producer:
        logging.error("Kafka producer is not connected. Scheduler cannot run.")
        return

    while True:
        try:
            # Query the database for recurring payments that are due
            engine = get_db_engine()
            with engine.connect() as conn:
                today_str = datetime.now().strftime('%Y-%m-%d')
                logging.info(f"Checking for recurring payments due today: {today_str}")

                query = text("""
                    SELECT BillID, Amount, Currency, AccountID
                    FROM Transactions
                    WHERE EventType = 'RecurringPaymentScheduled' AND StartDate = :today
                """)

                result = conn.execute(query, {"today": today_str})

                for row in result:
                    billId, amount, currency, accountId = row
                    logging.info(f"Payment for bill {billId} is due. Triggering event.")

                    # Create a new event to trigger a notification and payment
                    payment_due_event = {
                        "eventType": "PaymentDueNotificationEvent",
                        "billId": billId,
                        "accountId": accountId,
                        "amount": amount,
                        "currency": currency,
                        "timestamp": time.time()
                    }
                    message_bytes = json.dumps(payment_due_event).encode('utf-8')
                    await producer.send_and_wait("payment_due_notifications", message_bytes)

        except SQLAlchemyError as e:
            logging.error(f"Database error checking for due payments: {e}")
        except Exception as e:
            logging.error(f"Error checking for due payments: {e}")

        # Check again in 60 seconds
        await asyncio.sleep(60)

async def main():
    global producer

    # --- Database Connection Logic ---
    retries = 10
    delay = 3
    master_engine = None

    for i in range(retries):
        try:
            logging.info(f"Attempting to connect to 'master' database (attempt {i+1}/{retries})...")
            master_engine = create_engine(CONNECTION_STRING_MASTER)

            with master_engine.connect() as conn:
                result = conn.execute(text(f"SELECT name FROM sys.databases WHERE name = '{DB_DATABASE}'"))
                if result.fetchone():
                    logging.info(f"Database '{DB_DATABASE}' exists. Proceeding with main database connection.")
                    # Initialize the main database engine
                    get_db_engine()
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

    # --- Kafka Producer Logic ---
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
        logging.error("Failed to connect producer after multiple retries. Scheduler cannot run.")
        return

    scheduler_task = asyncio.create_task(check_and_trigger_payments())

    try:
        await asyncio.gather(scheduler_task)
    finally:
        if producer:
            await producer.stop()
            logging.info("Kafka producer stopped.")

if __name__ == '__main__':
    asyncio.run(main())