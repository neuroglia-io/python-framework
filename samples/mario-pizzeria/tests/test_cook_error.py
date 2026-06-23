import json
import tempfile

from fastapi.testclient import TestClient
from main import create_pizzeria_app

temp_dir = tempfile.mkdtemp(prefix="test_")
app = create_pizzeria_app(data_dir=temp_dir)
client = TestClient(app)

# Create order first
order_data = {
    "customer_name": "Test",
    "customer_email": "test@test.com",
    "customer_phone": "555-123-4567",  # Fixed: Must be at least 10 characters
    "customer_address": "123 Test St",
    "pizzas": [{"name": "Margherita", "size": "large", "toppings": []}],
    "payment_method": "cash",
    "notes": "Test",
}
create_resp = client.post("/api/orders/", json=order_data)
print(f"Create status: {create_resp.status_code}")
print(f"Create response: {json.dumps(create_resp.json(), indent=2)}")
if create_resp.status_code != 201:
    exit(1)

order_id = create_resp.json()["id"]
print(f"\nCreated order: {order_id}")

# Try to start cooking
cook_resp = client.put(f"/api/orders/{order_id}/cook")
print(f"\nCook response status: {cook_resp.status_code}")
print(f"Cook response: {json.dumps(cook_resp.json(), indent=2)}")
