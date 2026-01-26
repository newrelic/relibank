"""
Locust load test for bill-pay-service during stress chaos experiments.
Generates continuous load to make memory stress impact visible in APM metrics.
"""

from locust import HttpUser, task, between
import random

class BillPayServiceUser(HttpUser):
    wait_time = between(0.5, 1.5)  # Wait 0.5-1.5 seconds between requests
    host = ""  # Will be set via command line

    @task(3)
    def get_payment_methods(self):
        """Get payment methods for customer"""
        customer_id = f"customer_{random.randint(1, 100)}"
        self.client.get(f"/bill-pay-service/payment-methods/{customer_id}")

    @task(2)
    def pay_bill(self):
        """Pay a bill"""
        self.client.post("/bill-pay-service/pay", json={
            "bill_id": random.randint(1, 100),
            "amount": round(random.uniform(50, 500), 2),
            "payment_method": "checking"
        })

    @task(2)
    def card_payment(self):
        """Process card payment"""
        self.client.post("/bill-pay-service/card-payment", json={
            "amount": round(random.uniform(10, 300), 2),
            "card_number": "4111111111111111",
            "customer_id": f"customer_{random.randint(1, 100)}"
        })

    @task(1)
    def cancel_bill(self):
        """Cancel a bill"""
        bill_id = random.randint(1, 100)
        self.client.post(f"/bill-pay-service/cancel/{bill_id}")
