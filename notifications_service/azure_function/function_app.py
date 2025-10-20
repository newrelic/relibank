
import logging
import json
import os
import azure.functions as func

# The following imports are based on your existing code
from azure.communication.email import EmailClient
from azure.communication.sms import SmsClient
from azure.core.exceptions import HttpResponseError

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# --- Configuration for ACS Clients ---
# Retrieve environment variables configured in the Azure Function App settings
ACS_CONNECTION_STRING = os.environ.get("AZURE_ACS_CONNECTION_STRING")
ACS_SMS_SENDER = os.environ.get("AZURE_ACS_SMS_SENDER", "+18883143834")
ACS_EMAIL_SENDER = os.environ.get("AZURE_ACS_EMAIL_SENDER", "DoNotReply@a0c2117c-0bc8-4140-b298-d6a8309b76e1.azurecomm.net")

# --- Global ACS Clients ---
SMS_CLIENT = None
EMAIL_CLIENT = None

def init_clients():
    """Initializes the ACS clients if the connection string is available."""
    global SMS_CLIENT, EMAIL_CLIENT
    if ACS_CONNECTION_STRING:
        try:
            SMS_CLIENT = SmsClient.from_connection_string(ACS_CONNECTION_STRING)
            EMAIL_CLIENT = EmailClient.from_connection_string(ACS_CONNECTION_STRING)
            logging.info("ACS SMS and Email Clients initialized successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize ACS clients: {e}")
            return False
    else:
        logging.warning("ACS_CONNECTION_STRING is not set in environment variables.")
        return False

# Call init_clients() once when the function app starts to warm up
clients_initialized = init_clients()

# --- Notification Logic (Copied from your existing code) ---

def send_email(subject, body, recipient_address):
    """Sends an email notification via Azure Communication Services."""
    if not EMAIL_CLIENT:
        logging.error("Email client is not initialized.")
        return {'status': 'error', 'message': 'Email client not initialized.'}

    try:
        message = {
            "senderAddress": ACS_EMAIL_SENDER,
            "content": {
                "subject": subject,
                "plainText": body
            },
            "recipients": {
                "to": [
                    { "address": recipient_address }
                ]
            }
        }
        poller = EMAIL_CLIENT.begin_send(message)
        result = poller.result()
        
        if result and result.get('status', '').lower() == 'succeeded':
            logging.info(f"Email sent successfully. Message ID: {result.get('id')}")
            return {'status': 'succeeded', 'message': 'Email sent successfully.'}
        else:
            error_details = result.get('error', {})
            error_message = f"Failed to send email. Status: {result.get('status', 'Unknown')}, Error Code: {error_details.get('code')}, Message: {error_details.get('message')}"
            logging.error(error_message)
            return {'status': 'error', 'message': error_message}

    except HttpResponseError as he:
        logging.error(f"Failed to send email via ACS (HTTP Error): {he}")
        return {'status': 'error', 'message': f'HTTP Error: {he}'}
    except Exception as e:
        logging.error(f"An unexpected error occurred while sending email: {e}")
        return {'status': 'error', 'message': f'Unexpected Error: {e}'}

def send_sms(message, recipient_phone):
    """Sends an SMS notification via Azure Communication Services."""
    if not SMS_CLIENT:
        logging.error("SMS client is not initialized.")
        return {'status': 'error', 'message': 'SMS client not initialized.'}
    
    try:
        send_result = SMS_CLIENT.send(from_=ACS_SMS_SENDER, to=[recipient_phone], message=message)

        # TODO fix SMS sending
        # sms_client = SmsClient.from_connection_string(connectionString)

        # sms_responses = sms_client.send(
        #     from_="+18883143834",
        #     to="+15034877864",
        #     message='''Hello World 👋🏻 via SMS'''
        # )
        
        # Check the result for success
        for result in send_result:
            if result.successful:
                logging.info(f"SMS sent successfully. Message ID: {result.message_id}")
                return {'status': 'succeeded', 'message': 'SMS sent successfully.'}
            else:
                error_message = f"Failed to send SMS. Status: {result.http_status_code}, Error: {result.error_message}"
                logging.error(error_message)
                return {'status': 'error', 'message': error_message}

    except HttpResponseError as he:
        logging.error(f"Failed to send SMS via ACS (HTTP Error): {he}")
        return {'status': 'error', 'message': f'HTTP Error: {he}'}
    except Exception as e:
        logging.error(f"An unexpected error occurred while sending SMS: {e}")
        return {'status': 'error', 'message': f'Unexpected Error: {e}'}

# --- Azure Function Main Entry Point ---

@app.route(route="notify_user_trigger")
def notify_user(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main entry point for the HTTP-triggered Azure Function.
    This function processes an incoming request and routes it
    to the appropriate ACS notification function.
    """
    logging.info('Azure Function HTTP trigger processed a request.')

    if not clients_initialized:
        return func.HttpResponse(
            "ACS clients are not configured correctly. Please check environment variables.",
            status_code=500
        )
    
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
             "Please pass a JSON object in the request body",
             status_code=400
        )

    # Validate the incoming JSON payload
    notification_type = req_body.get('type')
    recipient = req_body.get('recipient')
    message_content = req_body.get('message')
    subject = req_body.get('subject', 'Default Notification') # Optional for SMS

    if not all([notification_type, recipient, message_content]):
        return func.HttpResponse(
            "Missing one or more required fields: 'type', 'recipient', or 'message'.",
            status_code=400
        )

    # Route the request based on the notification type
    if notification_type == 'email':
        result = send_email(subject, message_content, recipient)
        status_code = 200 if result['status'] == 'succeeded' else 500
        return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=status_code)

    elif notification_type == 'sms':
        result = send_sms(message_content, recipient)
        status_code = 200 if result['status'] == 'succeeded' else 500
        return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=status_code)

    else:
        return func.HttpResponse(
            "Invalid notification type. Please use 'email' or 'sms'.",
            status_code=400
        )
    