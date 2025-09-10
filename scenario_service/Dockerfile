# Use the official Python image for a later version
FROM python:3.12

# Set working directory in the container
WORKDIR /app

# Copy the pyproject.toml file
COPY pyproject.toml ./

# Copy the application code file
COPY . .

# Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uv && uv sync

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application with uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
