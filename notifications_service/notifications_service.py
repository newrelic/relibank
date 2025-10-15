import json
import os
import asyncio
import logging
import newrelic.agent
import requests
from aiokafka import AIOKafkaConsumer

# --- Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='[notifications-service] %(levelname)s [%(asctime)s] %(name)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

newrelic.agent.initialize(log_file='/app/newrelic.log', log_level=logging.DEBUG)

# Environment variables for the Azure Function
AZURE_FUNCTION_URL = os.environ.get("AZURE_FUNCTION_URL")


def trigger_azure_function(payload):
    """
    Triggers the Azure Function with a JSON payload.
    """
    if not AZURE_FUNCTION_URL:
        logger.warning("Azure Function environment variables not configured. Logging notification instead.")
        logger.info(f"Notification triggered (LOCAL MOCK): {payload}")
        return

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(AZURE_FUNCTION_URL, data=json.dumps(payload), headers=headers)
        logger.info(f"Function URL: {AZURE_FUNCTION_URL}, data: {json.dumps(payload)}, headers: {headers}")
        response.raise_for_status()
        logger.info(f"Successfully triggered Azure Function. Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to trigger Azure Function: {e}")


# --- Notification Logic ---
@newrelic.agent.background_task()
async def process_event(message):
    """Processes a single Kafka message based on the event type."""
    try:
        event = json.loads(message.value.decode('utf-8'))
        event_type = event.get('eventType')
        logger.info(f"Received event: {event_type} on topic {message.topic}")

        # --- Payment is Due Event ---
        if event_type == "PaymentDueNotificationEvent":
            logger.info("--- INFO: Payment is due event processing started. ---")
            
            bill_id = event.get('billId')
            amount = event.get('amount')
            currency = event.get('currency')
            
            user_email = "test.user@example.com"
            user_phone = "+14255550100"

            email_payload = {
                "type": "email",
                "recipient": user_email,
                "subject": f"Payment Due: {bill_id}",
                "message": (
                    f"Your payment for {amount} {currency} is due. "
                    f"Please log in to your account to make the payment. Bill ID: {bill_id}."
                )
            }
            trigger_azure_function(email_payload)

            sms_payload = {
                "type": "sms",
                "recipient": user_phone,
                "message": f"Payment Due: {bill_id}. {amount} {currency} is due."
            }
            trigger_azure_function(sms_payload)

        # --- Bill Payments Event ---
        elif event_type == "PaymentCompleted":
            logger.info("--- INFO: Bill payment event processing started. ---")

            bill_id = event.get('billId')
            amount = event.get('amount')
            currency = event.get('currency')

            user_email = "test.user@example.com"
            user_phone = "+14255550100"

            email_payload = {
                "type": "email",
                "recipient": user_email,
                "subject": f"Payment Completed: {bill_id}",
                "message": f"Your payment for {amount} {currency} has been successfully processed. Bill ID: {bill_id}."
            }
            trigger_azure_function(email_payload)

            sms_payload = {
                "type": "sms",
                "recipient": user_phone,
                "message": f"Payment Completed: {bill_id}. {amount} {currency} was successfully processed."
            }
            trigger_azure_function(sms_payload)

        # --- Recurring Payment Scheduled Event ---
        elif event_type == "RecurringPaymentScheduled":
            logger.info("--- INFO: Recurring payment scheduled event processing started. ---")

            bill_id = event.get('billId')
            amount = event.get('amount')
            currency = event.get('currency')
            frequency = event.get('frequency')

            user_email = "test.user@example.com"
            user_phone = "+14255550100"

            email_payload = {
                "type": "email",
                "recipient": user_email,
                "subject": f"Recurring Payment Scheduled: {bill_id}",
                "message": (
                    f"A recurring payment for {amount} {currency} has been successfully scheduled "
                    f"with a {frequency} frequency. Bill ID: {bill_id}."
                )
            }
            trigger_azure_function(email_payload)

            sms_payload = {
                "type": "sms",
                "recipient": user_phone,
                "message": f"Payment Scheduled: {bill_id}. {amount} {currency} {frequency}. Check your email for details."
            }
            trigger_azure_function(sms_payload)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode Kafka message: {e}")
    except Exception as e:
        logger.error(f"An error occurred during event processing: {e}")


async def consume():
    """Main Kafka consumer loop."""
    consumer = AIOKafkaConsumer(
        'payment_due_notifications',
        'bill_payments',
        'recurring_payments',
        # TODO add functionality for this if needed
        # 'payment_cancellations',
        bootstrap_servers='kafka:29092',
        group_id='notifications-consumer-group',
        auto_offset_reset='earliest'
    )
    
    await consumer.start()
    logger.info("Kafka consumer started successfully.")

    try:
        async for message in consumer:
            await process_event(message)
    finally:
        logger.warning("Stopping Kafka consumer.")
        await consumer.stop()

def main():
    """Application entry point."""
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user.")
    except Exception as e:
        logger.error(f"A fatal error occurred in the main loop: {e}")

if __name__ == '__main__':
    main()