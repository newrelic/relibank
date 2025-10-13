# Use a slim Python image as the base for building and running
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Install build dependencies required for C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    unixodbc-dev

ARG APP_NAME
ENV APP_NAME=$APP_NAME
ARG NEW_RELIC_APP_NAME="${APP_NAME} - Notifications Service"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_USER_API_KEY=$NEW_RELIC_USER_API_KEY

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true

# Azure
ARG AZURE_ACS_CONNECTION_STRING
ENV AZURE_ACS_CONNECTION_STRING=$AZURE_ACS_CONNECTION_STRING
ARG AZURE_ACS_SMS_PHONE_NUMBER
ENV AZURE_ACS_SMS_PHONE_NUMBER=$AZURE_ACS_SMS_PHONE_NUMBER
ARG AZURE_ACS_EMAIL_SENDER
ENV AZURE_ACS_EMAIL_SENDER=$AZURE_ACS_EMAIL_SENDER

RUN echo "Docker Build Check: ACS Connection String: $AZURE_ACS_CONNECTION_STRING Azure ACS phone number: $AZURE_ACS_SMS_PHONE_NUMBER Azure ACS email: $AZURE_ACS_EMAIL_SENDER"

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the application code
COPY . .

# Expose port for potential health checks or service communication
EXPOSE 5000

# Command to run the consumer script
CMD ["newrelic-admin", "run-program", "python", "notifications_service.py"]
