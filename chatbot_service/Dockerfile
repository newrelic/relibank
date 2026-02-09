# Use a slim Python image as the base for building and running
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

ARG APP_NAME
ENV APP_NAME=$APP_NAME
ARG NEW_RELIC_APP_NAME="${APP_NAME} - Chatbot Service"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_USER_API_KEY=$NEW_RELIC_USER_API_KEY
ARG NEW_RELIC_ACCOUNT_ID
ARG NEW_RELIC_LICENSE_KEY

ENV NEW_RELIC_APP_NAME="${APP_NAME} - Chatbot Service"
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true
ENV NEW_RELIC_CONFIG_FILE="newrelic.ini"

ARG OPENAI_API_KEY
ENV OPENAI_API_KEY=$OPENAI_API_KEY
ARG OPENAI_LOG
ENV OPENAI_LOG=$OPENAI_LOG
ARG OPENAI_BASE_URL
ENV OPENAI_BASE_URL=$OPENAI_BASE_URL
ARG OPENAI_API_VERSION
ENV OPENAI_API_VERSION=$OPENAI_API_VERSION
ARG OPENAI_API_TYPE
ENV OPENAI_API_TYPE=$OPENAI_API_TYPE

# Copy the requirements file and install dependencies
COPY chatbot_service/requirements.txt .
RUN pip install -r requirements.txt

# Copy the centralized utils directory
COPY utils /app/utils

# Copy the application code
COPY chatbot_service /app


# Expose the port the FastAPI app will run on
EXPOSE 5003

# Command to run the application using Uvicorn
# CMD uv run gunicorn -w 1 -k uvicorn.workers.UvicornWorker chatbot_service:app --bind 0.0.0.0:5003 --log-config=logging.conf
CMD ["newrelic-admin", "run-program", "gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "chatbot_service:app", "--bind", "0.0.0.0:5003", "--log-config", "logging.conf"]
