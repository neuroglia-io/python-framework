"""
Unit tests for Mario's Pizzeria domain entities
"""

import pytest
from datetime import datetime
from decimal import Decimal

import sys
from pathlib import Path

# Add samples to path
samples_root = Path(__file__).parent.parent.parent.parent.parent / "samples" / "mario-pizzeria"
sys.path.insert(0, str(samples_root))

from domain.entities import Order, Pizza, Customer, Kitchen, OrderStatus
from domain.events import (
    OrderPlacedEvent,
    CookingStartedEvent,
    OrderReadyEvent,
    OrderDeliveredEvent,
)


class TestPizza:
    """Test cases for Pizza entity"""

    def test_pizza_creation_with_defaults(self):
        """Test creating a pizza with default values"""
        pizza = Pizza(name="Margherita", size="medium")

        assert pizza.name == "Margherita"
        assert pizza.size == "medium"
        assert pizza.toppings == []
        assert pizza.price == Decimal("0.00")

    def test_pizza_creation_with_toppings(self):
        """Test creating a pizza with toppings"""
        toppings = ["extra cheese", "mushrooms"]
        pizza = Pizza(name="Pepperoni", size="large", toppings=toppings)

        assert pizza.name == "Pepperoni"
        assert pizza.size == "large"
        assert pizza.toppings == toppings

    def test_pizza_calculate_price_base_only(self):
        """Test price calculation with base price only"""
        pizza = Pizza(name="Margherita", size="medium")
        base_price = Decimal("12.99")
        size_multiplier = Decimal("1.0")

        pizza.calculate_price(base_price, size_multiplier, {})

        assert pizza.price == base_price * size_multiplier

    def test_pizza_calculate_price_with_toppings(self):
        """Test price calculation with toppings"""
        pizza = Pizza(name="Pepperoni", size="large", toppings=["extra cheese", "mushrooms"])
        base_price = Decimal("14.99")
        size_multiplier = Decimal("1.3")
        topping_prices = {"extra cheese": Decimal("1.50"), "mushrooms": Decimal("1.00")}

        pizza.calculate_price(base_price, size_multiplier, topping_prices)

        expected_price = (base_price * size_multiplier) + Decimal("1.50") + Decimal("1.00")
        assert pizza.price == expected_price

    def test_pizza_calculate_price_missing_topping(self):
        """Test price calculation with missing topping price"""
        pizza = Pizza(name="Custom", size="small", toppings=["unknown_topping"])
        base_price = Decimal("10.00")
        size_multiplier = Decimal("0.8")

        pizza.calculate_price(base_price, size_multiplier, {})

        # Should only include base price when topping price is missing
        assert pizza.price == base_price * size_multiplier

    def test_pizza_equality(self):
        """Test pizza equality comparison"""
        pizza1 = Pizza(name="Margherita", size="medium", toppings=["extra cheese"])
        pizza2 = Pizza(name="Margherita", size="medium", toppings=["extra cheese"])
        pizza3 = Pizza(name="Pepperoni", size="medium", toppings=["extra cheese"])

        assert pizza1 == pizza2
        assert pizza1 != pizza3


class TestCustomer:
    """Test cases for Customer entity"""

    def test_customer_creation(self):
        """Test creating a customer"""
        customer = Customer(
            name="Mario Rossi", phone="+1-555-0123", address="123 Pizza Street, Little Italy"
        )

        assert customer.name == "Mario Rossi"
        assert customer.phone == "+1-555-0123"
        assert customer.address == "123 Pizza Street, Little Italy"
        assert customer.id is not None
        assert customer.order_history == []

    def test_customer_add_order_to_history(self):
        """Test adding an order to customer history"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        order_id = "order123"

        customer.add_order_to_history(order_id)

        assert order_id in customer.order_history

    def test_customer_multiple_orders_in_history(self):
        """Test customer with multiple orders"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")

        customer.add_order_to_history("order1")
        customer.add_order_to_history("order2")
        customer.add_order_to_history("order3")

        assert len(customer.order_history) == 3
        assert "order1" in customer.order_history
        assert "order2" in customer.order_history
        assert "order3" in customer.order_history


class TestOrder:
    """Test cases for Order entity"""

    def test_order_creation(self):
        """Test creating an order"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]

        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")

        assert order.customer == customer
        assert order.pizzas == pizzas
        assert order.payment_method == "credit_card"
        assert order.status == OrderStatus.PLACED
        assert order.total == Decimal("0.00")
        assert order.id is not None
        assert order.placed_at is not None

    def test_order_raises_placed_event(self):
        """Test that creating an order raises OrderPlacedEvent"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]

        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")
        events = order.get_uncommitted_events()

        assert len(events) == 1
        assert isinstance(events[0], OrderPlacedEvent)
        assert events[0].order_id == order.id
        assert events[0].customer_name == customer.name
        assert events[0].total == order.total

    def test_order_calculate_total(self):
        """Test order total calculation"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")

        pizza1 = Pizza(name="Margherita", size="medium")
        pizza1.price = Decimal("12.99")

        pizza2 = Pizza(name="Pepperoni", size="large")
        pizza2.price = Decimal("18.99")

        order = Order(customer=customer, pizzas=[pizza1, pizza2], payment_method="credit_card")
        order.calculate_total()

        assert order.total == Decimal("31.98")

    def test_order_start_cooking(self):
        """Test starting to cook an order"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]
        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")

        # Clear the initial placed event
        order.mark_events_as_committed()

        order.start_cooking()

        assert order.status == OrderStatus.COOKING
        assert order.cooking_started_at is not None

        events = order.get_uncommitted_events()
        assert len(events) == 1
        assert isinstance(events[0], CookingStartedEvent)
        assert events[0].order_id == order.id

    def test_order_start_cooking_invalid_status(self):
        """Test that starting to cook fails if order is not placed"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]
        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")
        order.status = OrderStatus.COOKING

        with pytest.raises(ValueError, match="Can only start cooking orders that are placed"):
            order.start_cooking()

    def test_order_mark_ready(self):
        """Test marking an order as ready"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]
        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")
        order.status = OrderStatus.COOKING

        # Clear initial events
        order.mark_events_as_committed()

        order.mark_ready()

        assert order.status == OrderStatus.READY
        assert order.ready_at is not None

        events = order.get_uncommitted_events()
        assert len(events) == 1
        assert isinstance(events[0], OrderReadyEvent)
        assert events[0].order_id == order.id

    def test_order_mark_ready_invalid_status(self):
        """Test that marking ready fails if order is not cooking"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]
        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")
        # Status is PLACED by default

        with pytest.raises(ValueError, match="Can only mark orders as ready when they are cooking"):
            order.mark_ready()

    def test_order_deliver(self):
        """Test delivering an order"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]
        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")
        order.status = OrderStatus.READY

        # Clear initial events
        order.mark_events_as_committed()

        order.deliver()

        assert order.status == OrderStatus.DELIVERED
        assert order.delivered_at is not None

        events = order.get_uncommitted_events()
        assert len(events) == 1
        assert isinstance(events[0], OrderDeliveredEvent)
        assert events[0].order_id == order.id

    def test_order_deliver_invalid_status(self):
        """Test that delivery fails if order is not ready"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]
        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")
        # Status is PLACED by default

        with pytest.raises(ValueError, match="Can only deliver orders that are ready"):
            order.deliver()

    def test_order_cancel(self):
        """Test cancelling an order"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]
        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")

        order.cancel()

        assert order.status == OrderStatus.CANCELLED
        assert order.cancelled_at is not None

    def test_order_cancel_invalid_status(self):
        """Test that cancellation fails if order is delivered"""
        customer = Customer(name="Test Customer", phone="+1-555-0123", address="Test Address")
        pizzas = [Pizza(name="Margherita", size="medium")]
        order = Order(customer=customer, pizzas=pizzas, payment_method="credit_card")
        order.status = OrderStatus.DELIVERED

        with pytest.raises(ValueError, match="Cannot cancel delivered orders"):
            order.cancel()


class TestKitchen:
    """Test cases for Kitchen entity"""

    def test_kitchen_creation(self):
        """Test creating a kitchen"""
        kitchen = Kitchen(capacity=5)

        assert kitchen.capacity == 5
        assert kitchen.current_orders == []
        assert kitchen.is_available() is True

    def test_kitchen_add_order(self):
        """Test adding an order to kitchen"""
        kitchen = Kitchen(capacity=2)
        order_id = "order123"

        result = kitchen.add_order(order_id)

        assert result is True
        assert order_id in kitchen.current_orders
        assert len(kitchen.current_orders) == 1

    def test_kitchen_add_order_at_capacity(self):
        """Test adding order when kitchen is at capacity"""
        kitchen = Kitchen(capacity=1)
        kitchen.current_orders = ["order1"]

        result = kitchen.add_order("order2")

        assert result is False
        assert "order2" not in kitchen.current_orders
        assert len(kitchen.current_orders) == 1

    def test_kitchen_complete_order(self):
        """Test completing an order in kitchen"""
        kitchen = Kitchen(capacity=3)
        kitchen.current_orders = ["order1", "order2", "order3"]

        result = kitchen.complete_order("order2")

        assert result is True
        assert "order2" not in kitchen.current_orders
        assert len(kitchen.current_orders) == 2
        assert "order1" in kitchen.current_orders
        assert "order3" in kitchen.current_orders

    def test_kitchen_complete_nonexistent_order(self):
        """Test completing an order that's not in kitchen"""
        kitchen = Kitchen(capacity=3)
        kitchen.current_orders = ["order1"]

        result = kitchen.complete_order("order999")

        assert result is False
        assert len(kitchen.current_orders) == 1

    def test_kitchen_availability_check(self):
        """Test kitchen availability checking"""
        kitchen = Kitchen(capacity=2)

        # Empty kitchen should be available
        assert kitchen.is_available() is True

        # Kitchen with space should be available
        kitchen.current_orders = ["order1"]
        assert kitchen.is_available() is True

        # Full kitchen should not be available
        kitchen.current_orders = ["order1", "order2"]
        assert kitchen.is_available() is False

    def test_kitchen_get_current_load(self):
        """Test getting current kitchen load"""
        kitchen = Kitchen(capacity=5)

        # Empty kitchen
        assert kitchen.get_current_load() == 0

        # Partially loaded kitchen
        kitchen.current_orders = ["order1", "order2"]
        assert kitchen.get_current_load() == 2

        # Full kitchen
        kitchen.current_orders = ["order1", "order2", "order3", "order4", "order5"]
        assert kitchen.get_current_load() == 5
