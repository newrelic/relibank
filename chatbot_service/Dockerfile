# Use a slim Python image as the base for building and running
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy all necessary files to the container
COPY . .

# Install Python dependencies
RUN pip install -U pip && pip install uv
RUN uv sync

# Expose the port the FastAPI app will run on
EXPOSE 5003

# Command to run the application using Uvicorn
CMD uv run gunicorn -w 1 -k uvicorn.workers.UvicornWorker chatbot_service:app --bind 0.0.0.0:5003 --log-config=logging.conf