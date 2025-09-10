# Use a slim Python image as the base for building and running
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

ARG NEW_RELIC_APP_NAME="${APP_NAME} - Chatbot Service"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_API_KEY=$NEW_RELIC_USER_API_KEY

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true

ENV NEW_RELIC_CONFIG_FILE="newrelic.ini"

# Copy the application code file
COPY . .

# Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uv && uv sync

# Expose the port the FastAPI app will run on
EXPOSE 5003

# Command to run the application using Uvicorn
# CMD uv run gunicorn -w 1 -k uvicorn.workers.UvicornWorker chatbot_service:app --bind 0.0.0.0:5003 --log-config=logging.conf
CMD ["uv", "run", "newrelic-admin", "run-program", "gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "chatbot_service:app", "--bind", "0.0.0.0:5003", "--log-config", "logging.conf"]
