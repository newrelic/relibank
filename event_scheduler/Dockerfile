# Use a slim Python image as the base for running
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
COPY scheduler_service.py .

# Command to run the scheduler script
CMD ["python", "scheduler_service.py"]
