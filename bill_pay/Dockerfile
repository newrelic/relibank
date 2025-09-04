# Use a slim Python image as the base for building and running
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies required for C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev


# New Relic environment variables, these will be overwritten by the ini if they're defined in both places
# ARG NEW_RELIC_APP_NAME="Bill Pay Service - ${APP_NAME}"
ARG NEW_RELIC_APP_NAME="Bill Pay Service - Jared"
ENV NEW_RELIC_APP_NAME=$NEW_RELIC_APP_NAME

ARG NEW_RELIC_USER_API_KEY
ENV NEW_RELIC_API_KEY=$NEW_RELIC_USER_API_KEY

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the FastAPI app will run on
EXPOSE 5000

# curl -Ls https://download.newrelic.com/install/newrelic-cli/scripts/install.sh | bash && sudo NEW_RELIC_API_KEY=NRAK- NEW_RELIC_ACCOUNT_ID=4182956 /usr/local/bin/newrelic install -n logs-integration

ENV NEW_RELIC_CONFIG_FILE=newrelic.ini

# Command to run the application using Uvicorn
CMD ["newrelic-admin", "run-program", "uvicorn", "bill_pay_service:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
# CMD NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program $YOUR_COMMAND_OPTIONS uvicorn bill_pay_service:app --host 0.0.0.0 --port 5000 --workers 1

