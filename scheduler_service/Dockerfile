# Use a slim Python image as the base for building and running
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies required for C extensions and database connectivity
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    unixodbc-dev \
    libodbc2 \
    curl \
    gnupg

ARG NEW_RELIC_APP_NAME="Jared - Event Scheduler Service"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_API_KEY=$NEW_RELIC_USER_API_KEY

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true

# Add the Microsoft ODBC repository for Debian and install the driver
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/microsoft.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/trusted.gpg.d/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
    libodbc2 \
    msodbcsql18

# Copy the dependency management file into the container
COPY pyproject.toml .

# Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uv && uv sync

COPY scheduler_service.py .

# Command to run the scheduler script
CMD ["uv", "run", "newrelic-admin", "run-program", "python", "scheduler_service.py"]