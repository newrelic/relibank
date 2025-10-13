from locust import HttpUser, task, between
import json
import os

class RelibankUser(HttpUser):
    # This simulates a user waiting between 1 to 5 seconds between tasks
    wait_time = between(1, 5)

    @task
    def pay_and_cancel_bill(self):
        """
        Simulates the bill payment and cancellation flow.
        """
        # Task 1: Pay a bill with a POST request
        pay_payload = {
            "billId": "BILL-TEST-001",
            "amount": 75.25,
            "currency": "USD",
            "fromAccountId": 67890,
            "toAccountId": 10111
        }

        bill_pay_host = os.getenv("BILL_PAY_SERVICE_SERVICE_HOST")
        bill_pay_port = os.getenv("BILL_PAY_SERVICE_SERVICE_PORT")

        with self.client.post(f"http://{bill_pay_host}:{bill_pay_port}/pay", json=pay_payload, catch_response=True) as response:
        # with self.client.post(f"{self.host}/pay", json=pay_payload, catch_response=True) as response:
        # with self.client.post(f"http://localhost:5000/pay", json=pay_payload, catch_response=True) as response:
            if response.status_code == 200:
                print("Successfully paid the bill.")
            else:
                response.failure("Failed to pay the bill.")

        # Task 2: Cancel the paid bill with a POST request
        with self.client.post(f"http://{bill_pay_host}:{bill_pay_port}/cancel/BILL-TEST-001", catch_response=True) as response:
        # with self.client.post(f"http://localhost:5000/cancel/BILL-TEST-001", catch_response=True) as response:
            if response.status_code == 200:
                print("Successfully canceled the bill.")
            else:
                response.failure("Failed to cancel the bill.")
    
    @task
    def get_all_transactions(self):
        """
        Simulates getting all transactions with a GET request.
        """

        transaction_host = os.getenv("TRANSACTION_SERVICE_SERVICE_HOST")
        transaction_port = os.getenv("TRANSACTION_SERVICE_SERVICE_PORT")

        # Task 3: Get all transactions with a GET request
        with self.client.get(f"http://{transaction_host}:{transaction_port}/transaction-service/transactions", catch_response=True) as response:
        # with self.client.get(f"http://localhost:5001/transactions", catch_response=True) as response:
            if response.status_code == 200:
                print("Successfully fetched all transactions.")
            else:
                response.failure("Failed to get all transactions.")
