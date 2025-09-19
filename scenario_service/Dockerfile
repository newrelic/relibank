# Use a slim Python image as the base for building and running
FROM python:3.12

# Create the final application directory
WORKDIR /app

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

