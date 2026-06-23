"""
Test data factories and fixtures for Mario's Pizzeria domain.

This module provides reusable test data factories that create realistic
business entities and value objects for testing the Neuroglia framework.

The test data is inspired by the Mario's Pizzeria sample application and
provides comprehensive coverage of:
- Domain entities (Pizza, Order, Customer, Kitchen)
- Value objects (OrderItem, Address, Money)
- Enums (PizzaSize, OrderStatus, PaymentMethod)
- Events (OrderCreated, PizzaAdded, OrderConfirmed)

Usage:
    from tests.fixtures.test_data import create_margherita_pizza, create_customer

    def test_order_workflow():
        pizza = create_margherita_pizza()
        customer = create_customer()
        order = create_order(customer_id=customer.id, pizzas=[pizza])

References:
    - Sample Application: samples/mario-pizzeria/
    - Domain Entities: samples/mario-pizzeria/domain/entities/
    - Test Architecture: tests/TEST_ARCHITECTURE.md
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

# =============================================================================
# Enums
# =============================================================================


class PizzaSize(Enum):
    """Pizza size options"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class OrderStatus(Enum):
    """Order status lifecycle"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    COOKING = "cooking"
    READY = "ready"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(Enum):
    """Payment method options"""

    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    MOBILE_PAYMENT = "mobile_payment"


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class Money:
    """
    Money value object for representing monetary amounts.

    Immutable value object that ensures consistency in currency representation.
    """

    amount: Decimal
    currency: str = "USD"

    def __add__(self, other):
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError(f"Cannot add {self.currency} and {other.currency}")
            return Money(self.amount + other.amount, self.currency)
        return Money(self.amount + Decimal(str(other)), self.currency)

    def __mul__(self, multiplier):
        return Money(self.amount * Decimal(str(multiplier)), self.currency)


@dataclass(frozen=True)
class Address:
    """
    Address value object.

    Immutable value object representing a delivery address.
    """

    street: str
    apartment: Optional[str]
    city: str
    state: str
    zip_code: str
    country: str = "USA"

    def __str__(self):
        parts = [self.street]
        if self.apartment:
            parts.append(f"Apt {self.apartment}")
        parts.append(f"{self.city}, {self.state} {self.zip_code}")
        return ", ".join(parts)


# =============================================================================
# Pizza Test Data Factories
# =============================================================================


def create_margherita_pizza(size: PizzaSize = PizzaSize.MEDIUM, extra_toppings: list[str] = None) -> dict:
    """
    Create test data for a Margherita pizza.

    Args:
        size: Pizza size (default: MEDIUM)
        extra_toppings: Additional toppings beyond the standard recipe

    Returns:
        Dict containing pizza data ready for entity construction

    Example:
        >>> pizza_data = create_margherita_pizza(size=PizzaSize.LARGE)
        >>> pizza_data["name"]
        'Margherita'

    Related:
        - samples/mario-pizzeria/domain/entities/pizza.py
    """
    base_toppings = ["mozzarella", "tomato sauce", "fresh basil", "olive oil"]
    all_toppings = base_toppings + (extra_toppings or [])

    return {"id": str(uuid4()), "name": "Margherita", "base_price": Decimal("12.99"), "size": size, "description": "Classic Italian pizza with tomato, mozzarella, and fresh basil", "toppings": all_toppings, "available": True}


def create_pepperoni_pizza(size: PizzaSize = PizzaSize.LARGE, extra_cheese: bool = False) -> dict:
    """Create test data for a Pepperoni pizza."""
    toppings = ["mozzarella", "tomato sauce", "pepperoni", "oregano"]
    if extra_cheese:
        toppings.append("extra mozzarella")

    return {"id": str(uuid4()), "name": "Pepperoni", "base_price": Decimal("14.99"), "size": size, "description": "American favorite with premium pepperoni and mozzarella", "toppings": toppings, "available": True}


def create_supreme_pizza(size: PizzaSize = PizzaSize.LARGE) -> dict:
    """Create test data for a Supreme pizza."""
    return {"id": str(uuid4()), "name": "Supreme", "base_price": Decimal("17.99"), "size": size, "description": "Loaded with premium meats and fresh vegetables", "toppings": ["mozzarella", "tomato sauce", "pepperoni", "Italian sausage", "bell peppers", "red onions", "mushrooms", "black olives"], "available": True}


def create_custom_pizza(name: str, base_price: Decimal, size: PizzaSize, toppings: list[str], description: str = "") -> dict:
    """
    Create test data for a custom pizza.

    Allows full customization for edge case testing.
    """
    return {"id": str(uuid4()), "name": name, "base_price": base_price, "size": size, "description": description or f"Custom {name} pizza", "toppings": toppings, "available": True}


# =============================================================================
# Customer Test Data Factories
# =============================================================================


def create_customer(name: str = "John Doe", phone: str = "+1-555-0123", email: str = "john.doe@email.com", address: Address = None) -> dict:
    """
    Create test data for a customer.

    Args:
        name: Customer full name
        phone: Contact phone number
        email: Email address
        address: Delivery address (creates default if None)

    Returns:
        Dict containing customer data

    Example:
        >>> customer = create_customer(name="Jane Smith")
        >>> customer["email"]
        'john.doe@email.com'

    Related:
        - samples/mario-pizzeria/domain/entities/customer.py
    """
    if address is None:
        address = Address(street="123 Main Street", apartment="4B", city="Springfield", state="IL", zip_code="62701")

    return {"id": str(uuid4()), "name": name, "phone": phone, "email": email, "address": str(address), "loyalty_points": 0, "is_premium": False, "created_at": datetime.now(timezone.utc)}


def create_premium_customer(name: str = "Premium Customer", loyalty_points: int = 500) -> dict:
    """Create test data for a premium customer with loyalty benefits."""
    customer = create_customer(name=name)
    customer["is_premium"] = True
    customer["loyalty_points"] = loyalty_points
    return customer


# =============================================================================
# Order Test Data Factories
# =============================================================================


def create_order(customer_id: str = None, pizzas: list[dict] = None, status: OrderStatus = OrderStatus.PENDING, payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD, notes: str = None) -> dict:
    """
    Create test data for an order.

    Args:
        customer_id: ID of the customer placing the order
        pizzas: List of pizza dicts to include in order
        status: Current order status
        payment_method: How the customer will pay
        notes: Special delivery instructions

    Returns:
        Dict containing order data

    Example:
        >>> margherita = create_margherita_pizza()
        >>> order = create_order(pizzas=[margherita], notes="Ring twice")
        >>> len(order["pizzas"])
        1

    Related:
        - samples/mario-pizzeria/domain/entities/order.py
    """
    if customer_id is None:
        customer_id = str(uuid4())

    if pizzas is None:
        pizzas = [create_margherita_pizza()]

    return {"id": str(uuid4()), "customer_id": customer_id, "pizzas": pizzas, "status": status, "order_time": datetime.now(timezone.utc), "confirmed_time": None, "cooking_started_time": None, "ready_time": None, "estimated_ready_time": None, "delivery_person_id": None, "out_for_delivery_time": None, "delivered_time": None, "payment_method": payment_method, "notes": notes}


def create_confirmed_order(customer_id: str = None, pizzas: list[dict] = None, estimated_minutes: int = 30) -> dict:
    """Create test data for a confirmed order with estimated ready time."""
    order = create_order(customer_id, pizzas, OrderStatus.CONFIRMED)
    order["confirmed_time"] = datetime.now(timezone.utc)
    order["estimated_ready_time"] = datetime.now(timezone.utc) + timedelta(minutes=estimated_minutes)
    return order


def create_cooking_order(customer_id: str = None, pizzas: list[dict] = None, chef_id: str = None, chef_name: str = "Chef Mario") -> dict:
    """Create test data for an order being cooked."""
    order = create_confirmed_order(customer_id, pizzas)
    order["status"] = OrderStatus.COOKING
    order["cooking_started_time"] = datetime.now(timezone.utc)
    order["chef_user_id"] = chef_id or str(uuid4())
    order["chef_name"] = chef_name
    return order


def create_ready_order(customer_id: str = None, pizzas: list[dict] = None) -> dict:
    """Create test data for a completed order ready for delivery."""
    order = create_cooking_order(customer_id, pizzas)
    order["status"] = OrderStatus.READY
    now = datetime.now(timezone.utc)
    order["ready_time"] = now
    order["actual_ready_time"] = now
    return order


# =============================================================================
# Command Test Data Factories
# =============================================================================


def create_place_order_command_data(customer_name: str = "John Doe", pizzas: list[dict] = None, include_customer_details: bool = True) -> dict:
    """
    Create test data for PlaceOrderCommand.

    Args:
        customer_name: Name of customer placing order
        pizzas: List of pizza configurations
        include_customer_details: Whether to include full customer info

    Returns:
        Dict ready for PlaceOrderCommand construction

    Related:
        - samples/mario-pizzeria/application/commands/place_order_command.py
    """
    if pizzas is None:
        pizzas = [{"name": "Margherita", "size": "medium", "toppings": []}]

    data = {"customer_name": customer_name, "pizzas": pizzas, "payment_method": "credit_card"}

    if include_customer_details:
        data.update({"customer_phone": "+1-555-0123", "customer_email": "john.doe@email.com", "customer_address": "123 Main St, Springfield, IL 62701", "notes": "Please ring doorbell twice"})

    return data


def create_update_order_status_command_data(order_id: str = None, new_status: str = "cooking", user_id: str = None, user_name: str = "Chef Mario") -> dict:
    """Create test data for UpdateOrderStatusCommand."""
    return {"order_id": order_id or str(uuid4()), "new_status": new_status, "user_id": user_id or str(uuid4()), "user_name": user_name}


# =============================================================================
# Query Test Data Factories
# =============================================================================


def create_get_order_query_data(order_id: str = None) -> dict:
    """Create test data for GetOrderByIdQuery."""
    return {"order_id": order_id or str(uuid4())}


def create_get_orders_by_status_query_data(status: str = "pending", limit: int = 20, offset: int = 0) -> dict:
    """Create test data for GetOrdersByStatusQuery."""
    return {"status": status, "limit": limit, "offset": offset}


def create_get_menu_query_data(include_unavailable: bool = False, category: str = None) -> dict:
    """Create test data for GetMenuQuery."""
    data = {"include_unavailable": include_unavailable}
    if category:
        data["category"] = category
    return data


# =============================================================================
# Domain Event Test Data Factories
# =============================================================================


def create_order_created_event_data(order_id: str = None, customer_id: str = None, pizza_count: int = 1) -> dict:
    """Create test data for OrderCreatedEvent."""
    return {"aggregate_id": order_id or str(uuid4()), "customer_id": customer_id or str(uuid4()), "order_time": datetime.now(timezone.utc), "pizza_count": pizza_count}


def create_order_confirmed_event_data(order_id: str = None, estimated_ready_minutes: int = 30) -> dict:
    """Create test data for OrderConfirmedEvent."""
    return {"aggregate_id": order_id or str(uuid4()), "confirmed_time": datetime.now(timezone.utc), "estimated_ready_time": datetime.now(timezone.utc) + timedelta(minutes=estimated_ready_minutes)}


def create_pizza_added_event_data(order_id: str = None, pizza_data: dict = None) -> dict:
    """Create test data for PizzaAddedToOrderEvent."""
    if pizza_data is None:
        pizza_data = create_margherita_pizza()

    return {"aggregate_id": order_id or str(uuid4()), "pizza_id": pizza_data["id"], "pizza_name": pizza_data["name"], "pizza_size": pizza_data["size"].value, "timestamp": datetime.now(timezone.utc)}


# =============================================================================
# Batch Test Data Generators
# =============================================================================


def create_sample_menu() -> list[dict]:
    """
    Create a sample menu with various pizzas.

    Returns:
        List of pizza dicts representing a typical restaurant menu
    """
    return [
        create_margherita_pizza(PizzaSize.SMALL),
        create_margherita_pizza(PizzaSize.MEDIUM),
        create_margherita_pizza(PizzaSize.LARGE),
        create_pepperoni_pizza(PizzaSize.MEDIUM),
        create_pepperoni_pizza(PizzaSize.LARGE),
        create_supreme_pizza(PizzaSize.LARGE),
        create_custom_pizza("BBQ Chicken", Decimal("16.99"), PizzaSize.LARGE, ["mozzarella", "bbq sauce", "grilled chicken", "red onions", "cilantro"]),
        create_custom_pizza("Vegetarian", Decimal("15.99"), PizzaSize.MEDIUM, ["mozzarella", "tomato sauce", "bell peppers", "mushrooms", "onions", "olives"]),
    ]


def create_sample_orders(count: int = 5) -> list[dict]:
    """
    Create multiple sample orders for testing.

    Args:
        count: Number of orders to create

    Returns:
        List of order dicts with varied configurations
    """
    orders = []
    statuses = [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.COOKING, OrderStatus.READY, OrderStatus.DELIVERING]

    for i in range(count):
        customer = create_customer(name=f"Customer {i+1}")
        pizza_count = (i % 3) + 1  # 1-3 pizzas per order
        pizzas = [create_margherita_pizza() for _ in range(pizza_count)]

        order = create_order(customer_id=customer["id"], pizzas=pizzas, status=statuses[i % len(statuses)])
        orders.append(order)

    return orders


def create_sample_customers(count: int = 10) -> list[dict]:
    """
    Create multiple sample customers for testing.

    Args:
        count: Number of customers to create

    Returns:
        List of customer dicts with varied profiles
    """
    customers = []
    first_names = ["John", "Jane", "Mike", "Sarah", "David", "Emily", "Chris", "Lisa", "Tom", "Anna"]
    last_names = ["Doe", "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Martinez", "Davis", "Rodriguez"]

    for i in range(count):
        first_name = first_names[i % len(first_names)]
        last_name = last_names[i % len(last_names)]
        name = f"{first_name} {last_name}"

        customer = create_customer(name=name, phone=f"+1-555-{i:04d}", email=f"{first_name.lower()}.{last_name.lower()}@email.com")

        # Make some customers premium
        if i % 3 == 0:
            customer["is_premium"] = True
            customer["loyalty_points"] = 100 * (i + 1)

        customers.append(customer)

    return customers
