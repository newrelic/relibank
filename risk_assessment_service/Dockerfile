# Use a slim Python image as the base
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY risk_assessment_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the centralized utils directory (if needed for shared code)
COPY utils /app/utils

# Copy the application code
COPY risk_assessment_service /app

# Expose the port the FastAPI app will run on
EXPOSE 5001

# Command to run the application using Uvicorn
# Note: No New Relic instrumentation - this service is monitored via eBPF
CMD ["uvicorn", "risk_assessment_service:app", "--host", "0.0.0.0", "--port", "5001", "--workers", "1"]
