import asyncio
import os
import json
import logging
import time
import pyodbc
from datetime import datetime, timedelta
from aiokafka import AIOKafkaProducer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details from environment variables
DB_SERVER = os.getenv("DB_SERVER", "mssql")
DB_DATABASE = os.getenv("DB_DATABASE", "RelibankDB")
DB_USERNAME = os.getenv("DB_USERNAME", "SA")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrong@Password!")
CONNECTION_STRING = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD};TrustServerCertificate=yes"
CONNECTION_STRING_MASTER = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE=master;UID={DB_USERNAME};PWD={DB_PASSWORD};TrustServerCertificate=yes"

# Global Kafka producer and database connection
producer = None
db_connection = None

def get_db_connection():
    """
    Returns a new database connection.
    This function is now a simple wrapper for pyodbc.connect.
    """
    try:
        cnxn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
        logging.info("Successfully connected to MSSQL database.")
        return cnxn
    except Exception as e:
        raise ConnectionError(f"Failed to connect to {DB_DATABASE} database: {e}")

async def check_and_trigger_payments():
    """
    A background task that checks for and triggers due payments from the database.
    """
    global db_connection, producer
    
    # Ensure producer is connected
    if not producer:
        logging.error("Kafka producer is not connected. Scheduler cannot run.")
        return

    while True:
        try:
            # Query the database for recurring payments that are due
            cursor = db_connection.cursor()
            today_str = datetime.now().strftime('%Y-%m-%d')
            logging.info(f"Checking for recurring payments due today: {today_str}")

            cursor.execute("""
                SELECT BillID, Amount, Currency, AccountID
                FROM Transactions
                WHERE EventType = 'RecurringPaymentScheduled' AND StartDate = ?
            """, today_str)

            for row in cursor.fetchall():
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

            cursor.close()
        except Exception as e:
            logging.error(f"Error checking for due payments: {e}")
        
        # Check again in 60 seconds
        await asyncio.sleep(60)

async def main():
    global db_connection, producer
    
    # --- Database Connection Logic ---
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
    await asyncio.gather(scheduler_task)

if __name__ == '__main__':
    asyncio.run(main())
