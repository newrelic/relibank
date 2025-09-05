# Use a slim Python image as the base for building and running
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies required for C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev


# New Relic environment variables, these will be overwritten by the ini if they're defined in both places
# ARG NEW_RELIC_APP_NAME="${APP_NAME} - Bill Pay Service"
ARG NEW_RELIC_APP_NAME="Jared - Bill Pay Service"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_API_KEY=$NEW_RELIC_USER_API_KEY

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true

# ENV NEW_RELIC_CONFIG_FILE="newrelic.ini"

# Copy the dependency management file into the container
COPY pyproject.toml .

# Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uv && uv sync

# Copy the application code file
COPY bill_pay_service.py .

# Expose the port the FastAPI app will run on
EXPOSE 5000

# Command to run the application using Uvicorn
CMD ["uv", "run", "newrelic-admin", "run-program", "uvicorn", "bill_pay_service:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
