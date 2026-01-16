# Relibank Transaction Service

This service is a core component of the **Relibank** FinServ application. It acts as a transactional data layer, consuming event-driven messages from a **Kafka** message queue and persisting them into a Microsoft **SQL Server (MSSQL)** database. It also exposes a RESTful API for querying transaction data.

---

### 🚀 Key Features

* **Kafka Consumer**: Listens for and processes payment-related events from the `bill_payments`, `recurring_payments`, and `payment_cancellations` topics.

* **MSSQL Database Integration**: Persists all processed events into a `Transactions` table in a dedicated MSSQL database.

* **Pydantic Validation**: Validates all incoming Kafka messages against a defined schema, ensuring data integrity before it's written to the database.

* **RESTful API**: Provides endpoints for retrieving transaction data.

---

### 📦 API Endpoints

The service exposes the following API endpoints, which are designed to be consumed by other microservices.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/transaction-service/transactions` | `GET` | Retrieves a list of all transactions from the database. |
| `/transaction-service/transaction/{bill_id}` | `GET` | Retrieves a single transaction record by its `bill_id`. |
| `/transaction-service/recurring-payments` | `GET` | Retrieves all active recurring payment schedules from the `RecurringSchedules` table. Filters out cancelled schedules. Returns `RecurringScheduleRecord[]` with ScheduleID, BillID, AccountID, Amount, Currency, Frequency, StartDate, and timestamps. |
| `/transaction-service/health` | `GET` | A health check endpoint that returns a status of `healthy`. |

**Note**: The `/recurring-payments` endpoint includes automatic date conversion from MSSQL's `datetime.date` objects to ISO-format strings (`YYYY-MM-DD`) for proper JSON serialization.

---

### 🗄️ Database Schema

The service uses a Microsoft SQL Server database with the following key tables:

**Transactions Table:**
- Stores all processed payment transactions
- Populated by Kafka consumer from payment events
- Queried by the `/transactions` and `/transaction/{bill_id}` endpoints

**RecurringSchedules Table:**
- Stores recurring payment schedules
- Schema includes:
  - `ScheduleID` (int, primary key)
  - `BillID` (varchar)
  - `AccountID` (int)
  - `Amount` (decimal)
  - `Currency` (varchar)
  - `Frequency` (varchar) - e.g., "monthly", "weekly", "quarterly"
  - `StartDate` (date)
  - `Timestamp` (float) - Unix timestamp when schedule was created
  - `CancellationUserID` (varchar, nullable) - User who cancelled the schedule
  - `CancellationTimestamp` (float, nullable) - When schedule was cancelled

**Active vs Cancelled Schedules:**
- The `/recurring-payments` endpoint returns ALL schedules (including cancelled ones)
- Frontend is responsible for filtering based on `CancellationTimestamp` field
- A schedule is considered cancelled if `CancellationTimestamp` is not NULL
- Active schedules have `CancellationTimestamp = NULL`

### 📝 Data Models

**RecurringScheduleRecord (Pydantic Model):**
```python
class RecurringScheduleRecord(BaseModel):
    schedule_id: int = Field(alias="ScheduleID")
    bill_id: str = Field(alias="BillID")
    account_id: int = Field(alias="AccountID")
    amount: float = Field(alias="Amount")
    currency: str = Field(alias="Currency")
    frequency: str = Field(alias="Frequency")
    start_date: str = Field(alias="StartDate")  # Converted from date to string
    timestamp: float = Field(alias="Timestamp")
    cancellation_user_id: Optional[str] = Field(None, alias="CancellationUserID")
    cancellation_timestamp: Optional[float] = Field(None, alias="CancellationTimestamp")
```

**Key Features:**
- Uses Pydantic field aliases to map Python snake_case to database PascalCase
- Automatic date conversion in endpoint: `row_dict['StartDate'].strftime('%Y-%m-%d')`
- This conversion prevents Pydantic validation errors since MSSQL returns `datetime.date` objects

---

### ⚙️ How to Run

This service is designed to be run using Docker Compose as part of the larger **Relibank** application stack.

1.  **Ensure Docker Compose is Installed**: Make sure you have Docker and Docker Compose installed and running on your system.

2.  **Navigate to the Root Directory**: Open a terminal and navigate to the root directory of the `relibank` repository, where the `docker-compose.yml` file is located.

3.  **Start the Stack**: Run the following command to build the service images and start all containers. The `--build` flag is crucial for applying any code or dependency changes.

    ```bash
    docker compose up --build
    ```

    This command will start the `mssql` and `kafka` containers first, wait for them to become healthy, and then start the `transaction-service`.
