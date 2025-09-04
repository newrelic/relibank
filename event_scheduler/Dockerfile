# Use a slim Python image as the base for running
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies required for C extensions and database connectivity
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U pip && pip install uv

# Copy the project configuration
COPY pyproject.toml .
COPY uv.lock .

# Install Python dependencies
RUN uv sync --frozen

# Copy the application code file
COPY scheduler_service.py .

# Command to run the scheduler script
CMD ["uv", "run", "scheduler_service.py"]

