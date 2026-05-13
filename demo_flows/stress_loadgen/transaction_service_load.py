"""
Locust load test for transaction-service during stress chaos experiments.
Generates continuous load to make CPU stress impact visible in APM metrics.
"""

from locust import HttpUser, task, between
import random

class TransactionServiceUser(HttpUser):
    wait_time = between(0.5, 1.5)  # Wait 0.5-1.5 seconds between requests
    host = ""  # Will be set via command line

    # Valid account IDs from MSSQL init.sql
    ACCOUNT_IDS = [
        12345, 56789, 98765, 67890, 10111,  # Original accounts
        10001, 10002, 10003, 10004, 10005, 10006, 10007, 10008, 10009, 10010,
        10011, 10012, 10013, 10014, 10015,  # Checking accounts
        20001, 20002, 20003, 20004, 20005, 20006, 20007, 20008, 20009, 20010,  # Savings accounts
        30001, 30002, 30003, 30004, 30005, 30006, 30007, 30008, 30009, 30010,
        30011, 30012, 30013, 30014, 30015  # Credit accounts
    ]

    @task(5)
    def get_transactions(self):
        """Get all transactions - most common operation"""
        self.client.get("/transaction-service/transactions")

    @task(3)
    def get_ledger(self):
        """Get ledger balance for random account"""
        account_id = random.choice(self.ACCOUNT_IDS)
        self.client.get(f"/transaction-service/ledger/{account_id}")

    @task(2)
    def get_recurring_payments(self):
        """Get recurring payments"""
        self.client.get("/transaction-service/recurring-payments")

    SLOW_QUERY_TYPES = [
        "spending_velocity",
        "merchant_risk",
        "transaction_patterns",
        "account_velocity",
        "flagged_analysis",
    ]

    @task(2)
    def slow_query(self):
        """Cycle through all slow query types at max lookback so NRDOT can correlate
        active sessions to Query Store entries and emit execution plans."""
        query_type = random.choice(self.SLOW_QUERY_TYPES)
        self.client.get(f"/transaction-service/slow-query?query_type={query_type}&delay_seconds=12")
