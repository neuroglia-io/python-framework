"""Comprehensive integration tests for Mario's Pizzeria API"""

import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

# We need to create the app in a way that uses a temporary data directory for testing
from main import create_pizzeria_app


@pytest.fixture(scope="function")
def test_data_dir():
    """Create a temporary directory for test data"""
    temp_dir = tempfile.mkdtemp(prefix="mario_test_")
    yield temp_dir
    # Cleanup after tests
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def test_app(test_data_dir):
    """Create test application with temporary data directory"""
    app = create_pizzeria_app(data_dir=test_data_dir)
    return app


@pytest.fixture(scope="function")
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)


class TestPizzaOrderingWorkflow:
    """Test the complete pizza ordering workflow"""

    def test_get_menu(self, test_client):
        """Test getting the pizza menu - tests endpoint works even with empty menu"""
        response = test_client.get("/api/menu/")

        assert response.status_code == 200
        menu = response.json()
        assert isinstance(menu, list)
        # Empty menu is valid for a fresh test environment
        # Menu items would be seeded separately for integration/E2E tests

    def test_create_order_valid(self, test_client):
        """Test creating a valid pizza order"""
        order_data = {
            "customer_name": "John Test",
            "customer_email": "john@test.com",
            "customer_phone": "555-123-4567",
            "customer_address": "123 Test Street",
            "pizzas": [{"name": "Margherita", "size": "large", "toppings": ["extra cheese"]}],
            "payment_method": "credit_card",
            "notes": "Test order",
        }

        response = test_client.post("/api/orders/", json=order_data)

        assert response.status_code == 201
        order = response.json()

        # Verify order structure
        assert "id" in order
        assert order["customer_name"] == "John Test"
        assert order["customer_phone"] == "555-123-4567"
        assert order["status"] == "confirmed"
        assert len(order["pizzas"]) == 1
        assert order["pizzas"][0]["name"] == "Margherita"
        assert order["notes"] == "Test order"
        assert "total_amount" in order
        assert "order_time" in order

    def test_create_order_invalid_phone(self, test_client):
        """Test creating order with invalid phone number"""
        order_data = {
            "customer_name": "Jane Test",
            "customer_email": "jane@test.com",
            "customer_phone": "123",  # Too short
            "customer_address": "456 Test Ave",
            "pizzas": [{"name": "Pepperoni", "size": "medium", "toppings": []}],
            "payment_method": "cash",
        }

        response = test_client.post("/api/orders/", json=order_data)
        assert response.status_code == 422  # Validation error

    def test_create_order_invalid_payment(self, test_client):
        """Test creating order with invalid payment method"""
        order_data = {
            "customer_name": "Bob Test",
            "customer_email": "bob@test.com",
            "customer_phone": "555-987-6543",
            "customer_address": "789 Test Blvd",
            "pizzas": [{"name": "Quattro Stagioni", "size": "small", "toppings": ["mushrooms"]}],
            "payment_method": "bitcoin",  # Invalid payment method
        }

        response = test_client.post("/api/orders/", json=order_data)
        assert response.status_code == 422  # Validation error

    def test_get_orders(self, test_client):
        """Test getting all active orders"""
        response = test_client.get("/api/orders/")

        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)

    def test_get_order_by_id(self, test_client):
        """Test getting a specific order by ID"""
        # First create an order
        order_data = {
            "customer_name": "Alice Test",
            "customer_email": "alice@test.com",
            "customer_phone": "555-111-9999",
            "customer_address": "321 Test Lane",
            "pizzas": [{"name": "Pepperoni", "size": "medium", "toppings": ["extra pepperoni"]}],
            "payment_method": "debit_card",
        }

        create_response = test_client.post("/api/orders/", json=order_data)
        assert create_response.status_code == 201
        order_id = create_response.json()["id"]

        # Get the order by ID
        get_response = test_client.get(f"/api/orders/{order_id}")
        assert get_response.status_code == 200

        order = get_response.json()
        assert order["id"] == order_id
        assert order["customer_name"] == "Alice Test"

    def test_get_nonexistent_order(self, test_client):
        """Test getting a non-existent order"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/api/orders/{fake_id}")
        # The handler returns a bad request for not found orders
        assert response.status_code == 400

    def test_start_cooking_order(self, test_client):
        """Test starting to cook an order"""
        # Create an order first
        order_data = {
            "customer_name": "Chef Test",
            "customer_email": "chef@test.com",
            "customer_phone": "555-222-3333",
            "customer_address": "654 Kitchen St",
            "pizzas": [{"name": "Margherita", "size": "large", "toppings": ["basil"]}],
            "payment_method": "cash",
        }

        create_response = test_client.post("/api/orders/", json=order_data)
        assert create_response.status_code == 201
        order_id = create_response.json()["id"]

        # Start cooking the order
        cook_response = test_client.put(f"/api/orders/{order_id}/cook")
        assert cook_response.status_code == 200

        cooked_order = cook_response.json()
        assert cooked_order["status"] == "cooking"
        assert "cooking_started_time" in cooked_order

    def test_complete_order(self, test_client):
        """Test marking an order as ready"""
        # Create and start cooking an order
        order_data = {
            "customer_name": "Ready Test",
            "customer_email": "ready@test.com",
            "customer_phone": "555-444-5555",
            "customer_address": "987 Ready Road",
            "pizzas": [{"name": "Quattro Stagioni", "size": "medium", "toppings": ["olives"]}],
            "payment_method": "credit_card",
        }

        create_response = test_client.post("/api/orders/", json=order_data)
        order_id = create_response.json()["id"]

        # Start cooking
        test_client.put(f"/api/orders/{order_id}/cook")

        # Mark as ready
        ready_response = test_client.put(f"/api/orders/{order_id}/ready")
        assert ready_response.status_code == 200

        ready_order = ready_response.json()
        assert ready_order["status"] == "ready"
        assert "actual_ready_time" in ready_order

    def test_get_orders_by_status(self, test_client):
        """Test filtering orders by status"""
        response = test_client.get("/api/orders/?status=ready")
        assert response.status_code == 200

        orders = response.json()
        assert isinstance(orders, list)

        # All returned orders should have "ready" status
        for order in orders:
            assert order["status"] == "ready"

    def test_kitchen_status(self, test_client):
        """Test getting kitchen status"""
        response = test_client.get("/api/kitchen/status")
        assert response.status_code == 200

        status = response.json()
        assert "pending_orders" in status
        assert "cooking_orders" in status
        assert "ready_orders" in status
        assert "total_pending" in status
        assert "total_cooking" in status
        assert "total_ready" in status

    def test_complete_workflow(self, test_client):
        """Test the complete order workflow: create -> cook -> ready"""
        # Create order
        order_data = {
            "customer_name": "Workflow Test",
            "customer_email": "workflow@test.com",
            "customer_phone": "555-777-8888",
            "customer_address": "123 Workflow Way",
            "pizzas": [{"name": "Pepperoni", "size": "large", "toppings": ["extra cheese", "mushrooms"]}],
            "payment_method": "debit_card",
            "notes": "Complete workflow test",
        }

        # Step 1: Create order
        create_response = test_client.post("/api/orders/", json=order_data)
        assert create_response.status_code == 201

        order = create_response.json()
        order_id = order["id"]
        assert order["status"] == "confirmed"

        # Step 2: Start cooking
        cook_response = test_client.put(f"/api/orders/{order_id}/cook")
        assert cook_response.status_code == 200

        cooking_order = cook_response.json()
        assert cooking_order["status"] == "cooking"
        assert cooking_order["cooking_started_time"] is not None

        # Step 3: Mark as ready
        ready_response = test_client.put(f"/api/orders/{order_id}/ready")
        assert ready_response.status_code == 200

        ready_order = ready_response.json()
        assert ready_order["status"] == "ready"
        assert ready_order["actual_ready_time"] is not None

        # Verify complete order data
        assert ready_order["id"] == order_id
        assert ready_order["customer_name"] == "Workflow Test"
        assert ready_order["notes"] == "Complete workflow test"
        assert len(ready_order["pizzas"]) == 1
        assert ready_order["pizzas"][0]["toppings"] == ["extra cheese", "mushrooms"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
