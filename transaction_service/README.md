Relibank Transaction Service
This service is a core component of the Relibank FinServ application. It acts as a transactional data layer, consuming event-driven messages from a Kafka message queue and persisting them into a Microsoft SQL Server (MSSQL) database. It also exposes a RESTful API for querying transaction data.

🚀 Key Features
Kafka Consumer: Listens for and processes payment-related events from the bill_payments, recurring_payments, and payment_cancellations topics.

MSSQL Database Integration: Persists all processed events into a Transactions table in a dedicated MSSQL database.

Pydantic Validation: Validates all incoming Kafka messages against a defined schema, ensuring data integrity before it's written to the database.

RESTful API: Provides endpoints for retrieving transaction data.

📦 API Endpoints
The service exposes the following API endpoints, which are designed to be consumed by other microservices.

Endpoint

Method

Description

/transactions

GET

Retrieves a list of all transactions from the database.

/transaction/{bill_id}

GET

Retrieves a single transaction record by its bill_id.

/health

GET

A health check endpoint that returns a status of healthy.

⚙️ How to Run
This service is designed to be run using Docker Compose as part of the larger Relibank application stack.

Ensure Docker Compose is Installed: Make sure you have Docker and Docker Compose installed and running on your system.

Navigate to the Root Directory: Open a terminal and navigate to the root directory of the relibank repository, where the docker-compose.yml file is located.

Start the Stack: Run the following command to build the service images and start all containers. The --build flag is crucial for applying any code or dependency changes.

docker compose up --build

This command will start the mssql and kafka containers first, wait for them to become healthy, and then start the transaction-service.