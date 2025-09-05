# Stage 1: Build Stage
FROM python:3.12 AS builder

# Set the working directory in the container
WORKDIR /app

ARG NEW_RELIC_APP_NAME="Jared - Transaction Service"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_API_KEY=$NEW_RELIC_USER_API_KEY

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true

# Install build dependencies required for C extensions and the ODBC driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    unixodbc-dev \
    curl \
    gnupg \
    lsb-release

# Add the Microsoft ODBC repository for Debian and install the latest driver (msodbcsql18)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft-prod.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/trusted.gpg.d/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
    libodbc2 \
    msodbcsql18

# Copy the dependency management file into the container
COPY pyproject.toml .

# Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U pip && pip install uv && uv sync

# Copy the application code file
COPY transaction_service.py .

# Expose the port the FastAPI app will run on
EXPOSE 5000

# Command to run the consumer script
CMD ["uv", "run", "newrelic-admin", "run-program", "uvicorn", "transaction_service:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
