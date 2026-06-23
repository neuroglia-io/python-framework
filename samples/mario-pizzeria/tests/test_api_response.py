import json
import tempfile

from fastapi.testclient import TestClient
from main import create_pizzeria_app

# Create app with temporary data directory
temp_dir = tempfile.mkdtemp(prefix="test_")
app = create_pizzeria_app(data_dir=temp_dir)
client = TestClient(app)

order_data = {
    "customer_name": "John Test",
    "customer_email": "john@test.com",
    "customer_phone": "555-123-4567",
    "customer_address": "123 Test Street",
    "pizzas": [{"name": "Margherita", "size": "large", "toppings": ["extra cheese"]}],
    "payment_method": "credit_card",
    "notes": "Test order",
}

print("Sending POST request...")
response = client.post("/api/orders/", json=order_data)
print(f"\nStatus: {response.status_code}")
print(f"\nResponse JSON:")
result = response.json()
print(json.dumps(result, indent=2))
