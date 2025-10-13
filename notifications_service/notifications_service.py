import json
import os
import asyncio
import logging
import newrelic.agent
from aiokafka import AIOKafkaConsumer

# Correct imports for ACS services
from azure.communication.email import EmailClient
from azure.communication.sms import SmsClient
from azure.core.exceptions import HttpResponseError

# Removed the failing imports (EmailContent, EmailRecipients, EmailAddress).
# We will use standard Python dictionaries to construct the message payload
# to avoid dependency on specific module export paths.

# --- Configuration ---
# Setting up basic logging
logging.basicConfig(level=logging.INFO,
                    format='[notifications-service] %(levelname)s [%(asctime)s] %(name)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

newrelic.agent.initialize(log_file='/app/newrelic.log', log_level=logging.DEBUG)

# Environment variables for ACS
ACS_CONNECTION_STRING = os.environ.get("ACS_CONNECTION_STRING")
ACS_SMS_SENDER = os.environ.get("ACS_SMS_SENDER", "+18883143834")
ACS_EMAIL_SENDER = os.environ.get("ACS_EMAIL_SENDER", "DoNotReply@a0c2117c-0bc8-4140-b298-d6a8309b76e1.azurecomm.net")

# Global clients
SMS_CLIENT = None
EMAIL_CLIENT = None

def init_clients():
    """Initializes the ACS clients if the connection string is available."""
    global SMS_CLIENT, EMAIL_CLIENT
    if ACS_CONNECTION_STRING:
        # Check if the connection string is set (True or False for logging)
        logger.debug(f"*** RUNTIME VAR CHECK: CONN_STRING Set: {bool(ACS_CONNECTION_STRING)}, SMS Sender: {ACS_SMS_SENDER}, Email Sender: {ACS_EMAIL_SENDER}")
        try:
            # Initialize both SMS and Email clients with the same connection string
            SMS_CLIENT = SmsClient.from_connection_string(ACS_CONNECTION_STRING)
            EMAIL_CLIENT = EmailClient.from_connection_string(ACS_CONNECTION_STRING)
            logger.info("ACS SMS and Email Clients initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ACS clients: {e}")
    else:
        logger.warning("ACS_CONNECTION_STRING is not set. Notifications will not be sent.")

# --- Notification Logic ---

def send_email(subject, body, recipient_address):
    """Sends an email notification via Azure Communication Services."""
    if not EMAIL_CLIENT:
        logger.error("Email client is not initialized.")
        return

    try:
        # FIX: Construct the entire message as a Python dictionary.
        # This structure avoids the ImportError by not relying on the named model classes.
        message = {
            "senderAddress": ACS_EMAIL_SENDER,
            "content": {
                "subject": subject,
                "plainText": body
                # 'html' can also be added here if needed
            },
            "recipients": {
                "to": [
                    { "address": recipient_address }
                ]
            }
        }

        # Send the email and poll for status (assuming synchronous call for simplicity)
        poller = EMAIL_CLIENT.begin_send(message)
        result = poller.result() # Wait for the result
        
        # Check the status of the sent email
        if result and result.get('status', '').lower() == 'succeeded':
            logger.info(f"Email sent successfully via ACS. Message ID: {result.get('id')}")
        else:
            # Error dictionary will contain 'error' key if failed
            logger.error(f"Failed to send email via ACS. Status: {result.get('status', 'Unknown')}, Error: {result.get('error')}")

    except HttpResponseError as he:
        logger.error(f"Failed to send email via ACS (HTTP Error): {he}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending email: {e}")

def send_sms(message, recipient_phone):
    """Sends an SMS notification via Azure Communication Services."""
    if not SMS_CLIENT:
        logger.error("SMS client is not initialized.")
        return

    try:
        sms_recipients = [{'to': recipient_phone, 'message': message}]
        # The logs show the SMS sender is working correctly, but we include the code here.
        # send_result will be a list of SendSmsResponse objects (or similar)
        send_result = SMS_CLIENT.send(from_=ACS_SMS_SENDER, sms_content=sms_recipients)
        
        # Log the result for each recipient/message sent
        for result in send_result:
            logger.info(f"SMS sent via ACS. Message ID: {result.message_id}, Status: {result.http_status_code}")

    except HttpResponseError as he:
        logger.error(f"Failed to send SMS via ACS (HTTP Error): {he}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending SMS: {e}")


async def process_event(message):
    """Processes a single Kafka message based on the event type."""
    try:
        event = json.loads(message.value.decode('utf-8'))
        event_type = event.get('eventType')
        logger.info(f"Received event: {event_type} on topic {message.topic}")
        logger.debug(f"Received RAW message on topic {message.topic}: {message.value.decode('utf-8')}")

        if event_type == "RecurringPaymentScheduled":
            logger.info("--- INFO: Recurring Payment event processing started. ---")
            
            bill_id = event.get('billId')
            amount = event.get('amount')
            currency = event.get('currency')
            frequency = event.get('frequency')
            
            # --- Dummy Recipient Data (Replace with actual lookup logic) ---
            # In a real system, you would look up the user's email/phone based on event.accountId
            # For this example, we use mock data to test the ACS integration:
            user_email = "test.user@example.com"
            user_phone = "+14255550100" # Use a valid, E.164 formatted number
            # ----------------------------------------------------------------

            # 1. Send Email Notification
            email_subject = f"Recurring Payment Scheduled: {bill_id}"
            email_body = (
                f"A recurring payment for {amount} {currency} has been successfully scheduled "
                f"with a {frequency} frequency. Bill ID: {bill_id}."
            )
            send_email(email_subject, email_body, user_email)

            # 2. Send SMS Notification
            sms_body = f"Payment Scheduled: {bill_id}. {amount} {currency} {frequency}. Check your email for details."
            send_sms(sms_body, user_phone)

        elif event_type == "PaymentCompleted":
            # Add logic for PaymentCompleted
            pass
        
        # Add other event types here (e.g., PaymentFailed, PaymentCancelled)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode Kafka message: {e}")
    except Exception as e:
        logger.error(f"An error occurred during event processing: {e}")


async def consume():
    """Main Kafka consumer loop."""
    consumer = AIOKafkaConsumer(
        'recurring_payments',
        'payment_cancellations',
        'bill_payments',
        bootstrap_servers='kafka:29092',
        group_id='notifications-consumer-group',
        auto_offset_reset='earliest'
    )
    
    # Start the consumer
    await consumer.start()
    logger.info("Kafka consumer started successfully.")

    try:
        # Poll for messages and process them
        async for message in consumer:
            await process_event(message)

    finally:
        # Ensure the consumer is closed when done
        logger.warning("Stopping Kafka consumer.")
        await consumer.stop()

def main():
    """Application entry point."""
    init_clients() # Initialize ACS clients
    try:
        # Start the consumer loop
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user.")
    except Exception as e:
        logger.error(f"A fatal error occurred in the main loop: {e}")

if __name__ == '__main__':
    main()
