# Stage 1: Build Stage
FROM python:3.12 AS builder

# Set the working directory in the container
WORKDIR /app

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

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code file
COPY transaction_service.py .

# Expose the port the FastAPI app will run on
EXPOSE 5000

# Command to run the consumer script
CMD ["uvicorn", "transaction_service:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
