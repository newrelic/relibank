# Use a slim Python image as the base for building and running
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies required for C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    unixodbc-dev

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code file
COPY notifications_service.py .

# Expose port for potential health checks or service communication
EXPOSE 5000

# Command to run the consumer script
CMD ["python", "notifications_service.py"]
