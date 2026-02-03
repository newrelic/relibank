import asyncio
import os
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import psycopg2
from psycopg2 import extras, pool
import newrelic.agent
from utils.process_headers import process_headers

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# New Relic error tracking enabled for failed logins
# Note: New Relic is initialized via newrelic-admin run-program in Dockerfile

# Database connection details from environment variables
DB_HOST = os.getenv("DB_HOST", "accounts-db")
DB_NAME = os.getenv("DB_NAME", "accountsdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_postgres_password_here")
CONNECTION_STRING = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

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

# Custom exception classes for better New Relic error grouping
class FailedLoginUserNotFound(Exception):
    """Raised when login fails due to user not being found"""
    pass


class FailedLoginInvalidPassword(Exception):
    """Raised when login fails due to invalid password"""
    pass


# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    token: Optional[str] = None


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
    title="Relibank Auth Service",
    description="Manages user authentication.",
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


@app.post("/auth-service/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, request: Request):
    """
    Authenticates a user based on email and password.
    Validates credentials against the user_account database.

    NOTE: This implementation uses plain text password comparison for demo purposes.
    In production, use proper password hashing (bcrypt, argon2, etc.) and JWT tokens.
    """
    conn = None
    try:
        process_headers(dict(request.headers))

        conn = get_db_connection()
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            # Query user by email
            cursor.execute(
                "SELECT id, name, email, password FROM user_account WHERE email = %s",
                (login_request.email,)
            )
            user = cursor.fetchone()

            if not user:
                logging.warning(f"Failed login attempt - user not found: {login_request.email}")
                # Report failed login to New Relic with actor information
                try:
                    raise FailedLoginUserNotFound(f"Failed login attempt - user not found: {login_request.email}")
                except Exception:
                    newrelic.agent.notice_error(attributes={
                        "email": login_request.email,
                        "reason": "user_not_found",
                        "login_status": "failed",
                        "actor_ip": request.client.host if request.client else "unknown",
                        "actor_user_agent": request.headers.get("user-agent", "unknown"),
                        "actor_origin": request.headers.get("origin", "unknown")
                    })
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )

            # Validate password (plain text comparison for demo)
            # In production, use: bcrypt.checkpw(login_request.password.encode(), user['password'].encode())
            if user.get('password') != login_request.password:
                logging.warning(f"Failed login attempt - invalid password for user: {login_request.email}")
                # Report failed login to New Relic with actor information
                try:
                    raise FailedLoginInvalidPassword(f"Failed login attempt - invalid password for user: {login_request.email}")
                except Exception:
                    newrelic.agent.notice_error(attributes={
                        "email": login_request.email,
                        "reason": "invalid_password",
                        "login_status": "failed",
                        "actor_ip": request.client.host if request.client else "unknown",
                        "actor_user_agent": request.headers.get("user-agent", "unknown"),
                        "actor_origin": request.headers.get("origin", "unknown")
                    })
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )

            logging.info(f"Successful login for user: {login_request.email}")
            return LoginResponse(
                status="success",
                message="Login successful",
                user_id=str(user["id"]),
                email=user["email"],
                token="demo-token-12345"  # In production, generate a proper JWT token
            )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed login attempt"
        )
    finally:
        return_db_connection(conn)


@app.get("/auth-service")
async def simple_health_check():
    """Simple health check endpoint."""
    return "ok"


@app.get("/auth-service/health")
async def health_check():
    """Detailed health check endpoint."""
    return {"status": "healthy", "service": "auth-service"}
