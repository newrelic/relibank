# Dockerfile

# Stage 1: Build Stage
# Use a slim Python image for building dependencies
FROM python:3.9-slim-buster AS builder

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production Stage
# Use a smaller, runtime-optimized Python image
FROM python:3.9-slim-buster

# Set the working directory
WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# Copy the application code
COPY app.py .

# Expose the port the FastAPI app will run on
EXPOSE 5000

# Command to run the application using Uvicorn
# The --host 0.0.0.0 makes it accessible from outside the container.
# The --port 5000 matches the EXPOSE port.
# The --workers 1 is suitable for a demo; for production, you might use more workers.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
