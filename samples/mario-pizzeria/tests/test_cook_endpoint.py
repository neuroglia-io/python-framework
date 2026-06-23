"""Quick test to debug endpoint issues"""

from main import create_pizzeria_app
from starlette.testclient import TestClient


def test():
    app = create_pizzeria_app()
    client = TestClient(app)

    # Create order
    order_data = {
        "customer_name": "Debug Test",
        "customer_email": "debug@test.com",
        "customer_phone": "555-9876543",
        "customer_address": "456 Debug Ave",
        "pizzas": [{"name": "Margherita", "size": "large", "toppings": ["basil"]}],
        "payment_method": "cash",
    }
    create_resp = client.post("/api/orders/", json=order_data)
    print(f"Create Status: {create_resp.status_code}")

    if create_resp.status_code != 201:
        print(f"Create Error: {create_resp.text}")
        return

    order_id = create_resp.json()["id"]
    print(f"Order ID: {order_id}")

    # Get order - test the fixed query handler
    get_resp = client.get(f"/api/orders/{order_id}")
    print(f"Get Status: {get_resp.status_code}")
    if get_resp.status_code == 200:
        order = get_resp.json()
        print(f"Order retrieved successfully!")
        print(f'Pizzas: {len(order["pizzas"])}')
        print(f'Total: {order["total_amount"]}')
    else:
        print(f"Get Error: {get_resp.text}")


if __name__ == "__main__":
    test()
