# Use a slim Python image as the base for building and running
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

ARG APP_NAME
ENV APP_NAME=$APP_NAME
ARG NEW_RELIC_APP_NAME="${APP_NAME} - Auth Service"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_USER_API_KEY=$NEW_RELIC_USER_API_KEY

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true

# Copy the requirements file and install dependencies
COPY auth_service/requirements.txt .
RUN pip install -r requirements.txt

# Copy the centralized utils directory
COPY utils /app/utils

# Copy the application code
COPY auth_service /app


# Expose the port the FastAPI app will run on
EXPOSE 5002

# Command to run the application using Uvicorn
CMD ["newrelic-admin", "run-program", "uvicorn", "auth_service:app", "--host", "0.0.0.0", "--port", "5002", "--workers", "1", "--log-config", "logging.conf"]
