"""Debug script to test start cooking endpoint"""

import sys

sys.path.insert(0, ".")

import shutil
import tempfile

from fastapi.testclient import TestClient

from ..main import create_pizzeria_app

# Create temp dir
temp_dir = tempfile.mkdtemp(prefix="mario_test_")
print(f"Temp dir: {temp_dir}")

# Create app
app = create_pizzeria_app(data_dir=temp_dir)
client = TestClient(app)

# Create order
order_data = {
    "customer_name": "Test",
    "customer_email": "test@test.com",
    "customer_phone": "555-123-4567",
    "customer_address": "123 Test",
    "pizzas": [{"name": "Margherita", "size": "large", "toppings": []}],
    "payment_method": "cash",
}
create_resp = client.post("/api/orders/", json=order_data)
print(f"✅ Create status: {create_resp.status_code}")
if create_resp.status_code != 201:
    print(f"❌ Create failed: {create_resp.json()}")
    shutil.rmtree(temp_dir)
    sys.exit(1)

order_id = create_resp.json()["id"]
print(f"Order ID: {order_id}")

# Start cooking
cook_resp = client.put(f"/api/orders/{order_id}/cook")
print(f"\n🔍 Cook status: {cook_resp.status_code}")
print(f"🔍 Cook body: {cook_resp.json()}")

# Cleanup
shutil.rmtree(temp_dir)
