import asyncio
import os
import sys
import json
import logging
import hashlib
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

# Add parent directory to path to import utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils import process_headers

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

newrelic.agent.initialize()

def get_propagation_headers(request: Request) -> dict:
    """
    Extract headers that should be propagated to downstream services.
    Currently propagates: x-browser-user-id, error, extra-transaction-time
    """
    headers_to_propagate = {}

    if "x-browser-user-id" in request.headers:
        headers_to_propagate["x-browser-user-id"] = request.headers["x-browser-user-id"]

    if "error" in request.headers:
        headers_to_propagate["error"] = request.headers["error"]

    if "extra-transaction-time" in request.headers:
        headers_to_propagate["extra-transaction-time"] = request.headers["extra-transaction-time"]

    return headers_to_propagate

async def get_ab_test_config():
    """Fetch A/B test configuration from scenario service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config",
                timeout=2.0
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("config", {})
    except Exception as e:
        logging.debug(f"Could not fetch A/B test config: {e}")

    # Return defaults if scenario service unavailable
    return {
        "lcp_slowness_percentage_enabled": False,
        "lcp_slowness_percentage": 0.0,
        "lcp_slowness_percentage_delay_ms": 0,
        "lcp_slowness_cohort_enabled": False,
        "lcp_slowness_cohort_delay_ms": 0,
        "db_pool_stress_enabled": False,
        "db_pool_stress_delay_ms": 0,
        "db_pool_stress_affected_pool": "pool-a"
    }

def assign_user_to_pool(user_id: str) -> str:
    """
    Deterministically assign a user to database pool A or B based on user_id hash.
    Uses MD5 hash for consistent assignment (same user always gets same pool).

    Returns: "pool-a" or "pool-b"
    """
    user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return "pool-a" if (user_hash % 2) == 0 else "pool-b"

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

# Scenario service API URL
SCENARIO_SERVICE_URL = f"http://{os.getenv("SCENARIO_RUNNER_SERVICE_SERVICE_HOST", "scenario-runner-service")}:{os.getenv("SCENARIO_RUNNER_SERVICE_SERVICE_PORT", "8000")}"

# Hardcoded list of 11 test users for LCP slowness A/B testing
# These users will experience LCP delays when the scenario is enabled
LCP_SLOW_USERS = {
    'b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d',  # Alice Johnson
    'f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a',  # Bob Williams
    'e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b',  # Charlie Brown
    'f47ac10b-58cc-4372-a567-0e02b2c3d471',  # Solaire Astora
    'd9b1e2a3-f4c5-4d6e-8f7a-9b0c1d2e3f4a',  # Malenia Miquella
    '8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f',  # Artorias Abyss
    '7f6e5d4c-3b2a-1c0d-9e8f-7a6b5c4d3e2f',  # Priscilla Painted
    '6e5d4c3b-2a1c-0d9e-8f7a-6b5c4d3e2f1a',  # Gwyn Cinder
    '5d4c3b2a-1c0d-9e8f-7a6b-5c4d3e2f1a0b',  # Siegmeyer Catarina
    '4c3b2a1c-0d9e-8f7a-6b5c-4d3e2f1a0b9c',  # Ornstein Dragon
    '3b2a1c0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d',  # Smough Executioner
}

# Global connection pool
connection_pool = None

# Global scenario config cache (fetched periodically)
_scenario_config_cache = None
_scenario_config_last_fetch = 0

async def get_cached_scenario_config():
    """Get scenario config with caching to reduce API calls"""
    global _scenario_config_cache, _scenario_config_last_fetch
    current_time = time.time()

    # Cache for 5 seconds to reduce load on scenario service
    if _scenario_config_cache is None or (current_time - _scenario_config_last_fetch) > 5:
        _scenario_config_cache = await get_ab_test_config()
        _scenario_config_last_fetch = current_time

    return _scenario_config_cache

async def get_db_connection_with_pool_tracking(user_id: str = None):
    """
    Get a connection from the pool with database pool stress scenario support.

    Args:
        user_id: Optional user ID for pool assignment and stress testing

    Returns:
        tuple: (connection, pool_id, wait_time_ms, pool_exhausted)
    """
    global connection_pool
    if not connection_pool:
        raise HTTPException(status_code=503, detail="Database connection pool not available")

    start_time = time.time()
    pool_id = "unknown"
    pool_exhausted = False

    # Determine which pool this user belongs to
    if user_id:
        pool_id = assign_user_to_pool(user_id)

    # Check if pool stress scenario is active
    scenario_config = await get_cached_scenario_config()
    apply_delay = False

    if scenario_config.get("db_pool_stress_enabled"):
        affected_pool = scenario_config.get("db_pool_stress_affected_pool", "pool-a")
        if pool_id == affected_pool:
            apply_delay = True
            delay_ms = scenario_config.get("db_pool_stress_delay_ms", 500)

    try:
        # Get connection from pool
        conn = connection_pool.getconn()
        wait_time_ms = int((time.time() - start_time) * 1000)

        # Apply stress delay if this user is on the affected pool
        if apply_delay and conn:
            await asyncio.sleep(delay_ms / 1000.0)
            logging.info(f"[DB Pool Stress] User on {pool_id} held connection for {delay_ms}ms")

        return conn, pool_id, wait_time_ms, pool_exhausted

    except pool.PoolError as e:
        pool_exhausted = True
        wait_time_ms = int((time.time() - start_time) * 1000)
        logging.error(f"[DB Pool Stress] Pool exhausted for {pool_id}: {e}")
        raise HTTPException(status_code=503, detail="Database connection pool exhausted")

def get_db_connection():
    """Get a connection from the pool (legacy sync method)."""
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
    stripe_customer_id: Optional[str] = None
    stripe_payment_method_id: Optional[str] = None
    stripe_payment_method_name: Optional[str] = None


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

@app.get("/accounts-service/users/by-id/{user_id}")
async def get_user_by_id(user_id: str, request: Request):
    """Retrieves user info by UUID."""
    conn = None
    try:
        conn = get_db_connection()
        process_headers(dict(request.headers))
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM user_account WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            return User(**user)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving user: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving user.")
    finally:
        return_db_connection(conn)


@app.get("/accounts-service/users/{email}")
async def get_user(email: str, request: Request):
    """Retrieves user info by email."""
    conn = None
    try:
        conn = get_db_connection()
        process_headers(dict(request.headers))
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM user_account WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            return User(**user)
    except Exception as e:
        logging.error(f"Error retrieving user: {e}")
        newrelic.agent.notice_error(attributes={
            'service': 'accounts',
            'endpoint': '/accounts-service/user/{email}',
            'action': 'get_user'
        })
        raise HTTPException(status_code=500, detail="Error retrieving user.")
    finally:
        return_db_connection(conn)


@app.get("/accounts-service/accounts/{email}")
async def get_accounts(email: str, request: Request):
    """Retrieves all accounts for a given user email."""
    accounts = []
    conn = None
    pool_id = "unknown"
    wait_time_ms = 0
    pool_exhausted = False

    try:
        # First get user ID to determine pool assignment
        temp_conn = get_db_connection()
        with temp_conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute("SELECT id FROM user_account WHERE email = %s", (email,))
            user_data = cursor.fetchone()
        return_db_connection(temp_conn)

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found.")

        user_id = user_data["id"]

        # Process headers early to ensure New Relic transaction is initialized
        process_headers(dict(request.headers))

        # Get connection with pool tracking
        conn, pool_id, wait_time_ms, pool_exhausted = await get_db_connection_with_pool_tracking(user_id)

        # Add New Relic custom attributes immediately after getting pool info
        # Using dot notation (confirmed working with enduser.id)
        newrelic.agent.add_custom_attribute('db.pool_id', pool_id)
        newrelic.agent.add_custom_attribute('db.pool_wait_time_ms', wait_time_ms)
        newrelic.agent.add_custom_attribute('db.pool_exhausted', pool_exhausted)
        logging.info(f"[DB Pool Monitoring] Set pool attributes: pool={pool_id}, wait_time={wait_time_ms}ms, exhausted={pool_exhausted}")

        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            # Query checking accounts
            cursor.execute(
                """
                SELECT ca.id, ca.name, ca.balance, ca.routing_number, ca.interest_rate, ca.last_statement_date, 'checking' AS account_type FROM checking_accounts ca
                JOIN account_user au ON ca.id = au.account_id
                WHERE au.user_id = %s
            """,
                (user_id,),
            )
            checking_accounts = cursor.fetchall()

            # Query savings accounts
            cursor.execute(
                """
                SELECT sa.id, sa.name, sa.balance, sa.routing_number, sa.interest_rate, sa.last_statement_date, 'savings' AS account_type FROM savings_accounts sa
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
            propagation_headers = get_propagation_headers(request)
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
                        response = await client.get(
                            f"{TRANSACTION_SERVICE_URL}/transaction-service/ledger/{account_id_int}",
                            headers=propagation_headers
                        )
                        response.raise_for_status()
                        account["balance"] = response.json()["current_balance"]
                        process_headers(dict(request.headers))
                    except httpx.HTTPStatusError as e:
                        logging.warning(
                            f"Ledger balance for account {account_id_int} not found. Defaulting to 0. Error: {e.response.status_code}"
                        )
                        account["balance"] = 0.0
                    except Exception as e:
                        logging.error(f"Error fetching ledger balance for account {account_id_int}: {e}")
                        newrelic.agent.notice_error(attributes={
                            'service': 'accounts',
                            'endpoint': '/accounts-service/accounts',
                            'action': 'get_accounts',
                            'account_id': str(account_id_int)
                        })
                        account["balance"] = 0.0

            return [Account(**account) for account in all_accounts]
    except Exception as e:
        logging.exception(f"Error retrieving accounts: {e}")
        newrelic.agent.notice_error(attributes={
            'service': 'accounts',
            'endpoint': '/accounts-service/accounts',
            'action': 'get_accounts'
        })
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
            process_headers(dict(request.headers))

            raise HTTPException(status_code=404, detail="Account not found.")
    except Exception as e:
        logging.error(f"Error retrieving account type: {e}")
        newrelic.agent.notice_error(attributes={
            'service': 'accounts',
            'endpoint': '/account/type/{account_id}',
            'action': 'get_account_type'
        })
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
            process_headers(dict(request.headers))
            return {"status": "success", "message": "User created successfully."}
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        newrelic.agent.notice_error(attributes={
            'service': 'accounts',
            'endpoint': '/accounts-service/users',
            'action': 'create_user'
        })
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
            process_headers(dict(request.headers))
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
            newrelic.agent.notice_error(attributes={
                'service': 'accounts',
                'endpoint': '/accounts-service/accounts',
                'action': 'create_account'
            })
            raise HTTPException(status_code=400, detail="Invalid account data provided.")
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Error creating account: {e}")
        newrelic.agent.notice_error(attributes={
            'service': 'accounts',
            'endpoint': '/accounts-service/accounts',
            'action': 'create_account'
        })
        raise HTTPException(status_code=500, detail="Error creating account.")
    finally:
        return_db_connection(conn)

@app.get("/accounts-service")
async def simple_health_check():
    """Simple health check endpoint."""
    newrelic.agent.ignore_transaction()
    return "ok"

@app.get("/accounts-service/health")
async def health_check(request: Request):
    """Simple health check endpoint."""
    newrelic.agent.ignore_transaction()
    process_headers(dict(request.headers))
    return {"status": "healthy"}

@app.get("/accounts-service/browser-user")
async def get_browser_user(request: Request):
    """
    Returns a user ID for browser tracking.
    Priority 1: Uses x-browser-user-id header if provided and valid
    Priority 2: Returns random user ID from database
    """
    conn = None
    try:
        conn = get_db_connection()
        process_headers(dict(request.headers))

        # Check for x-browser-user-id header
        browser_user_id = request.headers.get("x-browser-user-id")

        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            if browser_user_id:
                # Validate UUID format
                try:
                    import uuid
                    uuid.UUID(browser_user_id)  # Validate UUID format

                    # Accept the header user ID for A/B testing even if not in database
                    # This allows deterministic cohort assignment for testing and analytics
                    logging.info(f"[Browser User] Using header-provided user ID: {browser_user_id}")

                    # Fetch A/B test config and assign LCP slowness cohort
                    ab_config = await get_ab_test_config()
                    lcp_delay_ms = 0

                    # Check percentage-based scenario first
                    if ab_config.get("lcp_slowness_percentage_enabled"):
                        percentage = ab_config.get("lcp_slowness_percentage", 0.0)
                        # Deterministically assign cohort based on user_id hash
                        user_hash = int(hashlib.md5(browser_user_id.encode()).hexdigest(), 16)
                        if (user_hash % 100) < percentage:
                            lcp_delay_ms = ab_config.get("lcp_slowness_percentage_delay_ms", 0)
                            logging.info(f"[Browser User] User {browser_user_id} assigned to SLOW LCP cohort via PERCENTAGE ({lcp_delay_ms}ms delay)")

                    # Check cohort-based scenario (can override percentage if both enabled)
                    elif ab_config.get("lcp_slowness_cohort_enabled"):
                        # Check if user is in the hardcoded slow cohort (11 test users)
                        if browser_user_id in LCP_SLOW_USERS:
                            lcp_delay_ms = ab_config.get("lcp_slowness_cohort_delay_ms", 0)
                            logging.info(f"[Browser User] User {browser_user_id} assigned to SLOW LCP cohort via COHORT ({lcp_delay_ms}ms delay)")
                        else:
                            logging.info(f"[Browser User] User {browser_user_id} assigned to NORMAL LCP cohort")
                    else:
                        logging.info(f"[Browser User] User {browser_user_id} assigned to NORMAL LCP cohort (no scenarios enabled)")

                    return {
                        "user_id": browser_user_id,
                        "source": "header",
                        "lcp_delay_ms": lcp_delay_ms
                    }
                except (ValueError, Exception) as e:
                    logging.warning(f"[Browser User] Invalid UUID format: {e}, falling back to random")

            # Fall back to random selection
            cursor.execute("SELECT id FROM user_account ORDER BY RANDOM() LIMIT 1")
            random_user = cursor.fetchone()

            if not random_user:
                raise HTTPException(
                    status_code=500,
                    detail="No users found in database. Cannot assign browser user ID."
                )

            user_id = random_user["id"]
            logging.info(f"[Browser User] Randomly selected user ID: {user_id}")

            # Fetch A/B test config and assign LCP slowness cohort
            ab_config = await get_ab_test_config()
            lcp_delay_ms = 0

            # Check percentage-based scenario first
            if ab_config.get("lcp_slowness_percentage_enabled"):
                percentage = ab_config.get("lcp_slowness_percentage", 0.0)
                # Deterministically assign cohort based on user_id hash
                user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
                if (user_hash % 100) < percentage:
                    lcp_delay_ms = ab_config.get("lcp_slowness_percentage_delay_ms", 0)
                    logging.info(f"[Browser User] User {user_id} assigned to SLOW LCP cohort via PERCENTAGE ({lcp_delay_ms}ms delay)")

            # Check cohort-based scenario (can override percentage if both enabled)
            elif ab_config.get("lcp_slowness_cohort_enabled"):
                # Check if user is in the hardcoded slow cohort (11 test users)
                if user_id in LCP_SLOW_USERS:
                    lcp_delay_ms = ab_config.get("lcp_slowness_cohort_delay_ms", 0)
                    logging.info(f"[Browser User] User {user_id} assigned to SLOW LCP cohort via COHORT ({lcp_delay_ms}ms delay)")
                else:
                    logging.info(f"[Browser User] User {user_id} assigned to NORMAL LCP cohort")
            else:
                logging.info(f"[Browser User] User {user_id} assigned to NORMAL LCP cohort (no scenarios enabled)")

            return {
                "user_id": user_id,
                "source": "random",
                "lcp_delay_ms": lcp_delay_ms
            }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting browser user: {e}")
        newrelic.agent.notice_error(attributes={
            'service': 'accounts',
            'endpoint': '/accounts-service/browser-user',
            'action': 'get_browser_user'
        })
        raise HTTPException(status_code=500, detail="Error retrieving browser user ID.")
    finally:
        return_db_connection(conn)
