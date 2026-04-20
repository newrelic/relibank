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

newrelic.agent.initialize()

# Environment variables for the Azure Function
AZURE_FUNCTION_URL = os.environ.get("AZURE_FUNCTION_URL")


def trigger_azure_function(payload):
    """
    Triggers the Azure Function with a JSON payload.
    """
    if not AZURE_FUNCTION_URL:
        logger.warning("Azure Function not configured, using local mock")
        logger.info(f"Notification triggered (LOCAL MOCK): {payload.get('type')} to {payload.get('recipient')}")
        return

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(AZURE_FUNCTION_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        logger.info(f"Azure Function triggered: {payload.get('type')} to {payload.get('recipient')}")
    except requests.exceptions.RequestException as e:
        newrelic.agent.notice_error(attributes={
            'service': 'notifications',
            'endpoint': 'internal',
            'action': 'trigger_azure_function'
        })
        logger.error(json.dumps({
            "message": {
                "log_level": "ERROR",
                "service": "notifications_service",
                "event": "AZURE_FUNCTION_ERROR",
                "error": str(e),
                "payload_type": payload.get('type'),
                "recipient": payload.get('recipient')
            }
        }))


# --- Notification Logic ---
@newrelic.agent.background_task()
async def process_event(message):
    """Processes a single Kafka message based on the event type."""
    try:
        event = json.loads(message.value.decode('utf-8'))
        event_type = event.get('eventType')
        attrs = [(k, v) for k, v in event.items() if "timestamp" not in k.lower() and v is not None]
        newrelic.agent.add_custom_attributes(attrs)
        logger.info(f"Processing event: {event_type} from topic {message.topic}")

        # --- Payment is Due Event ---
        if event_type == "PaymentDueNotificationEvent":
            logger.info("Processing payment due notification")
            
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
            logger.info("Processing payment completed notification")

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
            logger.info("Processing recurring payment scheduled notification")

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
        newrelic.agent.notice_error(attributes={
            'service': 'notifications',
            'endpoint': 'kafka',
            'action': 'process_event'
        })
        logger.error(json.dumps({
            "message": {
                "log_level": "ERROR",
                "service": "notifications_service",
                "event": "KAFKA_DECODE_ERROR",
                "error": str(e)
            }
        }))
    except Exception as e:
        newrelic.agent.notice_error(attributes={
            'service': 'notifications',
            'endpoint': 'kafka',
            'action': 'process_event'
        })
        logger.error(json.dumps({
            "message": {
                "log_level": "ERROR",
                "service": "notifications_service",
                "event": "EVENT_PROCESSING_ERROR",
                "error": str(e)
            }
        }))


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
    logger.info("Kafka consumer started")

    try:
        async for message in consumer:
            await process_event(message)
    finally:
        logger.warning("Stopping Kafka consumer")
        await consumer.stop()

def main():
    """Application entry point."""
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(json.dumps({
            "message": {
                "log_level": "ERROR",
                "service": "notifications_service",
                "event": "FATAL_ERROR",
                "error": str(e)
            }
        }))

if __name__ == '__main__':
    main()