# Use a slim Python image as the base for building and running
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code file
COPY chatbot_service.py .

# Expose the port the FastAPI app will run on
EXPOSE 5000

# Command to run the application using Uvicorn
CMD ["uvicorn", "chatbot_service:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
