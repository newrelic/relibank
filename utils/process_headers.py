import time
import logging
from typing import Dict, Any

from fastapi import HTTPException
import newrelic.agent

# This function is now synchronous (def) and uses time.sleep(),
# which WILL BLOCK the entire application process.
def process_headers(headers: Dict[str, str | Any]):
    """
    Checks request headers (which have lowercase keys) for simulation/testing parameters:
    'error' and 'extra-transaction-time'.

    Also handles New Relic APM user tracking via 'x-browser-user-id' header.

    If 'error' is present and valid, it raises the corresponding HTTPException.
    If 'extra-transaction-time' is present, it performs a BLOCKING time.sleep().

    Args:
        headers: A dictionary (from Request.headers) where keys are all lowercase.
    """

    # 0. Handle New Relic APM user tracking
    browser_user_id = headers.get("x-browser-user-id")
    if browser_user_id:
        try:
            # Set user ID as a custom attribute without checking for active transaction
            # The New Relic agent will attach it to the transaction when it becomes available
            newrelic.agent.add_custom_attribute('enduser.id', browser_user_id)
            logging.info(f"[APM User Tracking] Set enduser.id attribute: {browser_user_id}")
        except Exception as e:
            logging.warning(f"[APM User Tracking] Failed to set user ID: {e}")

    # 1. Handle extra-transaction-time (Blocking sleep simulation)
    delay_str = headers.get("extra-transaction-time", "0")
    extra_transaction_time = 0.0

    try:
        # We assume the time is floatable for simulation purposes
        extra_transaction_time = float(delay_str)
        if extra_transaction_time < 0:
            extra_transaction_time = 0.0
            logging.warning(f"Negative extra-transaction-time provided: {delay_str}. Using 0.")
    except ValueError:
        logging.error(f"Invalid value for 'extra-transaction-time' header: {delay_str}. Skipping delay.")

    if extra_transaction_time > 0:
        logging.warning(f"Simulating BLOCKING delay of {extra_transaction_time} seconds from header.")
        # WARNING: This line blocks the entire Python process/thread for the duration
        time.sleep(extra_transaction_time)


    # 2. Handle error status code (Error simulation)
    error_header = headers.get("error")

    if error_header:
        logging.warning(f"Found 'error' header with value: {error_header}. Raising exception for simulation.")
        try:
            # Attempt to convert the string value to an integer status code
            status_code = int(error_header)

            # Basic validation to ensure it's a valid error range (4xx or 5xx)
            if not (400 <= status_code < 600):
                logging.error(f"Simulated status code {status_code} is outside the 4xx/5xx error range.")
                raise HTTPException(
                    status_code=400,
                    detail="Provided 'error' status code is outside the valid 4xx/5xx range."
                )

            # Raise the requested error
            raise HTTPException(status_code=status_code)

        except ValueError:
            logging.error(f"Invalid status code received in 'error' header: {error_header}")
            # If the value is non-numeric, raise a 400 Bad Request error
            raise HTTPException(
                status_code=400,
                detail="Invalid 'error' status code provided in header (must be an integer)."
            )
