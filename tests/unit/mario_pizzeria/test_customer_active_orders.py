"""
Unit tests for Customer entity active orders functionality
"""

import sys
from pathlib import Path

# Add samples to path
samples_root = Path(__file__).parent.parent.parent.parent.parent / "samples" / "mario-pizzeria"
sys.path.insert(0, str(samples_root))

from domain.entities import Customer


class TestCustomerActiveOrders:
    """Test cases for Customer entity active orders management"""

    def test_customer_creation_with_empty_active_orders(self):
        """Test that new customers have empty active orders list"""
        customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="+1-555-0123",
            address="123 Test St",
        )

        assert customer.state.active_orders == []
        assert not customer.has_active_orders()
        assert len(customer.get_active_orders()) == 0

    def test_add_active_order(self):
        """Test adding an order to customer's active orders"""
        customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="+1-555-0123",
            address="123 Test St",
        )

        order_id = "order-123"
        customer.add_active_order(order_id)

        assert order_id in customer.state.active_orders
        assert customer.has_active_orders()
        assert len(customer.get_active_orders()) == 1
        assert order_id in customer.get_active_orders()

    def test_add_duplicate_active_order(self):
        """Test that adding same order ID twice doesn't create duplicates"""
        customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="+1-555-0123",
            address="123 Test St",
        )

        order_id = "order-123"
        customer.add_active_order(order_id)
        customer.add_active_order(order_id)  # Add same order again

        assert len(customer.state.active_orders) == 1
        assert order_id in customer.state.active_orders

    def test_remove_active_order(self):
        """Test removing an order from customer's active orders"""
        customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="+1-555-0123",
            address="123 Test St",
        )

        order_id = "order-123"
        customer.add_active_order(order_id)
        assert customer.has_active_orders()

        customer.remove_active_order(order_id)
        assert not customer.has_active_orders()
        assert order_id not in customer.state.active_orders

    def test_remove_nonexistent_active_order(self):
        """Test removing an order that isn't in active orders"""
        customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="+1-555-0123",
            address="123 Test St",
        )

        # Try to remove order that was never added
        customer.remove_active_order("nonexistent-order")

        # Should not raise error and active orders should remain empty
        assert not customer.has_active_orders()
        assert len(customer.get_active_orders()) == 0

    def test_multiple_active_orders(self):
        """Test managing multiple active orders"""
        customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="+1-555-0123",
            address="123 Test St",
        )

        order_ids = ["order-1", "order-2", "order-3"]

        # Add multiple orders
        for order_id in order_ids:
            customer.add_active_order(order_id)

        assert len(customer.get_active_orders()) == 3
        for order_id in order_ids:
            assert order_id in customer.state.active_orders

        # Remove one order
        customer.remove_active_order("order-2")
        assert len(customer.get_active_orders()) == 2
        assert "order-1" in customer.state.active_orders
        assert "order-2" not in customer.state.active_orders
        assert "order-3" in customer.state.active_orders

    def test_get_active_orders_returns_copy(self):
        """Test that get_active_orders returns a copy to prevent external modification"""
        customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="+1-555-0123",
            address="123 Test St",
        )

        customer.add_active_order("order-123")
        active_orders = customer.get_active_orders()

        # Modify the returned list
        active_orders.append("external-order")

        # Original active orders should not be affected
        assert len(customer.get_active_orders()) == 1
        assert "external-order" not in customer.state.active_orders
