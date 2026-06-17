# Use a slim Python image as the base for building and running
FROM python:3.12

# Install git for pip to clone git dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

ARG APP_NAME
ENV APP_NAME=$APP_NAME
ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_USER_API_KEY=$NEW_RELIC_USER_API_KEY
ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID
ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_APP_NAME="${APP_NAME} - Support Service"
ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true
ENV NEW_RELIC_CONFIG_FILE="newrelic.ini"

# AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and ASSISTANT_B_DELAY_SECONDS are
# injected at runtime via the K8s ConfigMap/Secret wired by terraform/aks/app_module.
# The deployed AI flow is LangGraph-based (chat completions API) — there is no
# Assistants-API code path, so no ASSISTANT_*_ID values are needed.

# Copy the requirements file and install dependencies
COPY support_service/requirements.txt .
RUN pip install -r requirements.txt

# Copy the centralized utils directory
COPY utils /app/utils

# Copy the application code
COPY support_service /app


# Expose the port the FastAPI app will run on
EXPOSE 5003

# Command to run the application using Uvicorn
# CMD uv run gunicorn -w 1 -k uvicorn.workers.UvicornWorker support_service:app --bind 0.0.0.0:5003 --log-config=logging.conf
CMD ["newrelic-admin", "run-program", "gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "support_service:app", "--bind", "0.0.0.0:5003", "--log-config", "logging.conf"]
