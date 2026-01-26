"""
Locust load test for transaction-service during stress chaos experiments.
Generates continuous load to make CPU stress impact visible in APM metrics.
"""

from locust import HttpUser, task, between
import random

class TransactionServiceUser(HttpUser):
    wait_time = between(0.5, 1.5)  # Wait 0.5-1.5 seconds between requests
    host = ""  # Will be set via command line

    @task(5)
    def get_transactions(self):
        """Get user transactions - most common operation"""
        self.client.get("/transaction-service/transactions")

    @task(3)
    def get_transaction_by_id(self):
        """Get specific transaction by bill_id"""
        bill_id = random.randint(1, 100)
        self.client.get(f"/transaction-service/transaction/{bill_id}")

    @task(2)
    def get_recurring_payments(self):
        """Get recurring payments"""
        self.client.get("/transaction-service/recurring-payments")

    @task(1)
    def get_ledger(self):
        """Get ledger for random account"""
        account_id = random.choice(["checking", "savings"])
        self.client.get(f"/transaction-service/ledger/{account_id}")

    @task(1)
    def slow_query(self):
        """Hit slow query endpoint to add extra CPU load"""
        self.client.get("/transaction-service/slow-query")
