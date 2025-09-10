import json
from locust import HttpUser, task, between


# Pays a bill, cancels, then pulls all transactions

class RelibankUser(HttpUser):
    # This simulates a user waiting between 1 to 5 seconds between tasks
    wait_time = between(1, 5)

    # Base URLs for the services
    payment_service_base_url = "http://localhost:5000"
    transaction_service_base_url = "http://localhost:5001"

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
        with self.client.post(f"{self.payment_service_base_url}/pay", json=pay_payload, catch_response=True) as response:
            if response.status_code == 200:
                print("Successfully paid the bill.")
            else:
                response.failure("Failed to pay the bill.")

        # Task 2: Cancel the paid bill with a POST request
        with self.client.post(f"{self.payment_service_base_url}/cancel/BILL-TEST-001", catch_response=True) as response:
            if response.status_code == 200:
                print("Successfully canceled the bill.")
            else:
                response.failure("Failed to cancel the bill.")
    
    @task
    def get_all_transactions(self):
        """
        Simulates getting all transactions with a GET request.
        """
        # Task 3: Get all transactions with a GET request
        with self.client.get(f"{self.transaction_service_base_url}/transactions", catch_response=True) as response:
            if response.status_code == 200:
                print("Successfully fetched all transactions.")
            else:
                response.failure("Failed to get all transactions.")
