"""Test file for Mario's Pizzeria API"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_create_order():
    """Test creating a new pizza order"""
    # Create order data
    order_data = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "customer_phone": "555-0123",
        "customer_address": "123 Main St",
        "pizzas": [{"size": "LARGE", "base_price": 15.99, "toppings": ["pepperoni", "mushrooms"]}],
    }

    # Post the order
    response = client.post("/api/orders/", json=order_data)

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    # Should be successful
    assert response.status_code == 201

    # Response should contain order data
    response_data = response.json()
    assert "id" in response_data
    assert response_data["status"] == "PENDING"
    assert len(response_data["pizzas"]) == 1


def test_get_orders():
    """Test getting all orders"""
    response = client.get("/api/orders/")

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    assert response.status_code == 200
    orders = response.json()
    assert isinstance(orders, list)


if __name__ == "__main__":
    test_create_order()
    test_get_orders()
