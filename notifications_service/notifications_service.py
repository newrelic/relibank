import asyncio
import os
import json
import logging
from aiokafka import AIOKafkaConsumer

# import httpx # Required for calling external APIs like SendGrid or Twilio
from azure.communication.email import EmailClient
from azure.communication.sms import SmsClient
import newrelic.agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

newrelic.agent.initialize(log_file='/app/newrelic.log', log_level=logging.DEBUG)

# Get Kafka broker address from environment variable
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:29092")

# Get notification service credentials from environment variables
# TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
# TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
# SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
# SENDGRID_SENDER_EMAIL = os.getenv("SENDGRID_SENDER_EMAIL")

# New environment variables for Azure Communication Services
AZURE_ACS_CONNECTION_STRING = os.getenv("AZURE_ACS_CONNECTION_STRING")
AZURE_ACS_EMAIL_ENDPOINT = os.getenv("AZURE_ACS_EMAIL_ENDPOINT")
AZURE_ACS_SMS_PHONE_NUMBER = os.getenv("AZURE_ACS_SMS_PHONE_NUMBER")
AZURE_ACS_EMAIL_SENDER = os.getenv("AZURE_ACS_EMAIL_SENDER")

# TODO add an endpoint to be used by mobile to do a popup
# TODO add values to ignore a % of good/successful notifications,
# but keep all bad/failed notifications for demo scenario purposes


@newrelic.agent.background_task()
async def send_sms_notification(to_number: str, body: str):
    """
    Sends an SMS notification using Azure Communication Services.
    """
    if AZURE_ACS_CONNECTION_STRING and AZURE_ACS_SMS_PHONE_NUMBER:
        try:
            client = SmsClient.from_connection_string(AZURE_ACS_CONNECTION_STRING)
            client.send(from_=AZURE_ACS_SMS_PHONE_NUMBER, to=[to_number], message=body)
            logging.info("SMS notification sent via Azure Communication Services.")
        except Exception as e:
            logging.error(f"Failed to send SMS via Azure Communication Services: {e}")
    else:
        logging.info(f"SIMULATED SMS: To '{to_number}', Body: '{body}'")

    # Sends an SMS notification using Twilio. Update with free tier Twilio creds or use the ACS solution.
    # if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
    #     logging.warning("Twilio credentials not set. Skipping SMS notification.")
    #     return

    # from twilio.rest import Client
    # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # try:
    #     message = client.messages.create(
    #         to=to_number,
    #         from_=TWILIO_PHONE_NUMBER,
    #         body=body
    #     )
    #     logging.info(f"SMS notification sent successfully. SID: {message.sid}")
    # except Exception as e:
    #     logging.error(f"Failed to send SMS notification: {e}")
    # logging.info(f"SIMULATED SMS: To '{to_number}', Body: '{body}'")

@newrelic.agent.background_task()
async def send_email_notification(to_email: str, subject: str, body: str):
    """
    Sends an SMS notification using Azure Communication Services.
    """
    if AZURE_ACS_CONNECTION_STRING and AZURE_ACS_EMAIL_ENDPOINT and AZURE_ACS_EMAIL_SENDER:
        try:
            client = EmailClient(
                endpoint=AZURE_ACS_EMAIL_ENDPOINT,
                connection_string=AZURE_ACS_CONNECTION_STRING,
            )
            client.send_message(
                from_address=AZURE_ACS_EMAIL_SENDER,
                to_address=[{"address": to_email}],
                subject=subject,
                content={"html": body},
            )
            logging.info("Email sent via Azure Communication Services.")
        except Exception as e:
            logging.error(f"Failed to send email via Azure Communication Services: {e}")
    else:
        logging.info(f"SIMULATED EMAIL: To '{to_email}', Subject: '{subject}', Body: '{body}'")

    # Sends an email notification using SendGrid. Update with free tier SendGrid creds or use the ACS solution.
    # if not SENDGRID_API_KEY or not SENDGRID_SENDER_EMAIL:
    #     logging.warning("SendGrid credentials not set. Skipping email notification.")
    #     return

    # from sendgrid import SendGridAPIClient
    # from sendgrid.helpers.mail import Mail
    # message = Mail(
    #     from_email=SENDGRID_SENDER_EMAIL,
    #     to_emails=to_email,
    #     subject=subject,
    #     html_content=body
    # )
    # try:
    #     sg = SendGridAPIClient(SENDGRID_API_KEY)
    #     response = sg.send(message)
    #     logging.info(f"Email sent successfully. Status code: {response.status_code}")
    # except Exception as e:
    #     logging.error(f"Failed to send email notification: {e}")
    # logging.info(f"SIMULATED EMAIL: To '{to_email}', Subject: '{subject}', Body: '{body}'")

@newrelic.agent.background_task()
async def consume_and_notify():
    """
    Consumes messages from Kafka topics and processes them to send notifications.
    """
    consumer = AIOKafkaConsumer(
        "bill_payments",
        "recurring_payments",
        "payment_cancellations",
        bootstrap_servers=KAFKA_BROKER,
        group_id="notifications-consumer-group",
        auto_offset_reset="earliest",
    )

    try:
        logging.info(f"Connecting to Kafka at {KAFKA_BROKER}...")
        await consumer.start()
        logging.info("Consumer connected. Waiting for messages...")

        async for message in consumer:
            topic = message.topic
            value = json.loads(message.value.decode("utf-8"))
            event_type = value.get("eventType")

            logging.info(f"Received event: {event_type} on topic {topic}")

            # This is where you would handle the different types of notifications
            # For a demo, we will log a message and simulate a notification
            if event_type == "BillPaymentInitiated":
                subject = f"Bill {value['billId']} Paid!"
                body = f"Your bill {value['billId']} for {value['amount']} {value['currency']} has been successfully paid from account {value['accountId']}."
                await send_email_notification("user@example.com", subject, body)
            elif event_type == "RecurringPaymentScheduled":
                subject = f"Recurring Payment for Bill {value['billId']} is Due Soon!"
                body = f"A recurring payment for bill {value['billId']} is coming up on {value['startDate']}."
                await send_email_notification("user@example.com", subject, body)
                await send_sms_notification("+15551234567", body)
            elif event_type == "BillPaymentCancelled":
                subject = f"Bill {value['billId']} Cancelled!"
                body = f"Your bill {value['billId']} was cancelled by user {value['user_id']}."
                await send_email_notification("user@example.com", subject, body)
            else:
                logging.warning(f"Unknown eventType '{event_type}'. Skipping notification.")

    except Exception as e:
        logging.error(f"Consumer encountered an error: {e}")
    finally:
        await consumer.stop()
        logging.info("Consumer stopped.")


if __name__ == "__main__":
    asyncio.run(consume_and_notify())
