import asyncio
import os
import json
import logging
import psycopg2
from psycopg2 import extras, pool
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid
import httpx
import newrelic.agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

newrelic.agent.initialize(log_file='/app/newrelic.log', log_level=logging.DEBUG)

# Database connection details from environment variables
DB_HOST = os.getenv("DB_HOST", "accounts-db")
DB_NAME = os.getenv("DB_NAME", "accountsdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_postgres_password_here")
CONNECTION_STRING = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

# Transaction service API URL
# tries to retrieve from host env TRANSACTION_SERVICE_URL and TRANSACTION_SERVICE_SERVICE_PORT
# if not, default to local development variables
TRANSACTION_SERVICE_URL = f"http://{os.getenv("TRANSACTION_SERVICE_SERVICE_HOST", "transaction-service")}:{os.getenv("TRANSACTION_SERVICE_SERVICE_PORT", "5001")}"

# Global connection pool
connection_pool = None

def get_db_connection():
    """Get a connection from the pool."""
    global connection_pool
    if connection_pool:
        return connection_pool.getconn()
    else:
        raise HTTPException(status_code=503, detail="Database connection pool not available")

def return_db_connection(conn):
    """Return a connection to the pool."""
    global connection_pool
    if connection_pool and conn:
        connection_pool.putconn(conn)

# Pydantic models for user and account data
class User(BaseModel):
    id: str
    name: str
    alert_preferences: Optional[dict]
    phone: Optional[str]
    email: str
    address: Optional[str]
    income: Optional[float]
    preferred_language: Optional[str]
    marketing_preferences: Optional[dict]
    privacy_preferences: Optional[dict]


class Account(BaseModel):
    id: int
    name: str
    balance: float
    routing_number: Optional[str]
    interest_rate: Optional[float]
    last_statement_date: Optional[str]
    account_type: str


class AccountType(BaseModel):
    id: int
    account_type: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Initializes database connection pool.
    """
    global connection_pool
    retries = 10
    delay = 3
    for i in range(retries):
        try:
            logging.info(f"Attempting to create database connection pool (attempt {i+1}/{retries})...")
            connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, CONNECTION_STRING)
            logging.info("Database connection pool created successfully.")
            break
        except Exception as e:
            logging.error(f"Database connection error: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 1.5
    else:
        logging.error("Failed to create database connection pool after multiple retries. The application will not start.")
        raise ConnectionError("Failed to connect to PostgreSQL during startup.")

    yield

    if connection_pool:
        connection_pool.closeall()
        logging.info("Database connection pool closed.")


app = FastAPI(
    title="Relibank Accounts Service",
    description="Manages user and account data.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This allows all domains
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.get("/accounts-service/users/{email}")
async def get_user(email: str, request: Request):
    """Retrieves user info by email."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM user_account WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            return User(**user)
    except Exception as e:
        logging.error(f"Error retrieving user: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving user.")
    finally:
        return_db_connection(conn)


@app.get("/accounts-service/accounts/{email}")
async def get_accounts(email: str, request: Request):
    """Retrieves all accounts for a given user email."""
    accounts = []
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            # First, get the user's ID using their email
            cursor.execute("SELECT id FROM user_account WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            user_id = user["id"]

            # Query checking accounts
            cursor.execute(
                """
                SELECT ca.id, ca.name, ca.routing_number, ca.interest_rate, ca.last_statement_date, 'checking' AS account_type FROM checking_accounts ca
                JOIN account_user au ON ca.id = au.account_id
                WHERE au.user_id = %s
            """,
                (user_id,),
            )
            checking_accounts = cursor.fetchall()

            # Query savings accounts
            cursor.execute(
                """
                SELECT sa.id, sa.name, sa.routing_number, sa.interest_rate, sa.last_statement_date, 'savings' AS account_type FROM savings_accounts sa
                JOIN account_user au ON sa.id = au.account_id
                WHERE au.user_id = %s
            """,
                (user_id,),
            )
            savings_accounts = cursor.fetchall()

            # Query credit accounts
            cursor.execute(
                """
                SELECT cra.id, cra.name, cra.routing_number, cra.interest_rate, cra.last_statement_date, cra.payment_schedule, cra.last_payment_date, cra.automatic_pay, 'credit' AS account_type FROM credit_accounts cra
                JOIN account_user au ON cra.id = au.account_id
                WHERE au.user_id = %s
            """,
                (user_id,),
            )
            credit_accounts = cursor.fetchall()

            all_accounts = checking_accounts + savings_accounts + credit_accounts

            if not all_accounts:
                raise HTTPException(status_code=404, detail="No accounts found for user.")

            # Fetch current balance from transaction-service for each account
            async with httpx.AsyncClient() as client:
                for account in all_accounts:
                    # Convert datetime fields to strings for Pydantic validation
                    if account.get('last_statement_date'):
                        account['last_statement_date'] = account['last_statement_date'].isoformat() if hasattr(account['last_statement_date'], 'isoformat') else str(account['last_statement_date'])
                    if account.get('last_payment_date'):
                        account['last_payment_date'] = account['last_payment_date'].isoformat() if hasattr(account['last_payment_date'], 'isoformat') else str(account['last_payment_date'])

                    # Correctly handling UUID as a string
                    account_id_int = int(account["id"])
                    try:
                        # Correctly passing a string UUID to the transaction service
                        print(f"URL: {TRANSACTION_SERVICE_URL}/transaction-service/ledger/{account_id_int}")
                        response = await client.get(f"{TRANSACTION_SERVICE_URL}/transaction-service/ledger/{account_id_int}")
                        response.raise_for_status()
                        account["balance"] = response.json()["current_balance"]
                    except httpx.HTTPStatusError as e:
                        logging.warning(
                            f"Ledger balance for account {account_id_int} not found. Defaulting to 0. Error: {e.response.status_code}"
                        )
                        account["balance"] = 0.0
                    except Exception as e:
                        logging.error(f"Error fetching ledger balance for account {account_id_int}: {e}")
                        account["balance"] = 0.0

            return [Account(**account) for account in all_accounts]
    except Exception as e:
        logging.error(f"Error retrieving accounts: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving accounts.")
    finally:
        return_db_connection(conn)

@app.get("/account/type/{account_id}", response_model=AccountType)
async def get_account_type(account_id: int, request: Request):
    """
    Retrieves the type of a specific account by its ID.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check checking accounts
            cursor.execute(
                "SELECT id, 'checking' AS account_type FROM checking_accounts WHERE id = %s",
                (account_id,),
            )
            account_data = cursor.fetchone()
            if account_data:
                return AccountType(id=account_data[0], account_type=account_data[1])

            # Check savings accounts
            cursor.execute(
                "SELECT id, 'savings' AS account_type FROM savings_accounts WHERE id = %s",
                (account_id,),
            )
            account_data = cursor.fetchone()
            if account_data:
                return AccountType(id=account_data[0], account_type=account_data[1])

            # Check credit accounts
            cursor.execute(
                "SELECT id, 'credit' AS account_type FROM credit_accounts WHERE id = %s",
                (account_id,),
            )
            account_data = cursor.fetchone()
            if account_data:
                return AccountType(id=account_data[0], account_type=account_data[1])

            raise HTTPException(status_code=404, detail="Account not found.")
    except Exception as e:
        logging.error(f"Error retrieving account type: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving account type.")
    finally:
        return_db_connection(conn)


@app.post("/accounts-service/users")
async def create_user(user: User, request: Request):
    """Creates a new user account."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_account (id, name, alert_preferences, phone, email, address, income, preferred_language, marketing_preferences, privacy_preferences)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    user.id,
                    user.name,
                    json.dumps(user.alert_preferences),
                    user.phone,
                    user.email,
                    user.address,
                    user.income,
                    user.preferred_language,
                    json.dumps(user.marketing_preferences),
                    json.dumps(user.privacy_preferences),
                ),
            )
            conn.commit()
            return {"status": "success", "message": "User created successfully."}
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Error creating user.")
    finally:
        return_db_connection(conn)


@app.post("/accounts-service/accounts/{email}")
async def create_account(email: str, account: Account, request: Request):
    """Creates a new account and links it to a user."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # First, get the user's ID using their email
            cursor.execute("SELECT id FROM user_account WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            user_id = user[0]

            if account.account_type == "checking":
                cursor.execute(
                    """
                    INSERT INTO checking_accounts (id, name, balance, routing_number, interest_rate, last_statement_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        account.id,
                        account.name,
                        account.balance,
                        account.routing_number,
                        account.interest_rate,
                        account.last_statement_date,
                    ),
                )
            elif account.account_type == "savings":
                cursor.execute(
                    """
                    INSERT INTO savings_accounts (id, name, balance, routing_number, interest_rate, last_statement_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        account.id,
                        account.name,
                        account.balance,
                        account.routing_number,
                        account.interest_rate,
                        account.last_statement_date,
                    ),
                )
            elif account.account_type == "credit":
                # Correctly handling the nullable fields for a credit account
                cursor.execute(
                    """
                    INSERT INTO credit_accounts (id, name, balance, outstanding_balance, routing_number, interest_rate, last_statement_date, payment_schedule, last_payment_date, automatic_pay)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        account.id,
                        account.name,
                        account.balance,
                        0,
                        account.routing_number,
                        account.interest_rate,
                        account.last_statement_date,
                        None,
                        None,
                        False,
                    ),
                )

            cursor.execute(
                """
                INSERT INTO account_user (account_id, user_id)
                VALUES (%s, %s)
            """,
                (account.id, user_id),
            )

            conn.commit()
            return {
                "status": "success",
                "message": f"{account.account_type} account created and linked to user.",
            }
    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        if "duplicate key value violates unique constraint" in str(e):
            logging.warning(f"Attempt to create duplicate account with ID {account.id}")
            raise HTTPException(
                status_code=409,
                detail=f"Account with ID {account.id} already exists. Please use a different account ID."
            )
        else:
            logging.error(f"Database integrity error creating account: {e}")
            raise HTTPException(status_code=400, detail="Invalid account data provided.")
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail="Error creating account.")
    finally:
        return_db_connection(conn)

@app.get("/accounts-service")
async def simple_health_check():
    """Simple health check endpoint."""
    return "ok"

@app.get("/accounts-service/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
