# Use a slim Python image as the base for building and running
FROM python:3.12

# Create the final application directory
WORKDIR /app

# Build deps + Microsoft ODBC Driver 18 for SQL Server (required by pyodbc for db-360 load).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    unixodbc-dev \
    curl \
    gnupg \
    lsb-release \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft-prod.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/trusted.gpg.d/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        libodbc2 \
        msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN mkdir locust
COPY ./locust /locust

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application with gunicorn and uvicorn workers
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "scenario_service.scenario_service:app"]
CMD ["uvicorn", "scenario_service:app", "--host", "0.0.0.0", "--port", "8000"]

