# Use a slim Python image as the base
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# New Relic environment variables, these will be overwritten by the ini if they're defined in both places
ARG APP_NAME
ENV APP_NAME=$APP_NAME
ARG NEW_RELIC_APP_NAME="${APP_NAME} - Compliance Archive"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_USER_API_KEY=$NEW_RELIC_USER_API_KEY

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app

# Expose the port the FastAPI app will run on
EXPOSE 5008

# Command to run the application using Uvicorn
CMD ["newrelic-admin", "run-program", "uvicorn", "compliance_archive_service:app", "--host", "0.0.0.0", "--port", "5008", "--workers", "1", "--log-config", "logging.conf"]
