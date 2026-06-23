"""
Comprehensive tests for Domain-Driven Design patterns in the Neuroglia framework.

This test suite validates the core DDD building blocks:
- AggregateRoot: State separation, event sourcing, invariants
- Entity: Identity, lifecycle, business rules
- ValueObject: Immutability, equality by value
- DomainEvent: Event raising, event handling, state transitions

The tests use Mario's Pizzeria domain entities as realistic examples,
demonstrating proper usage patterns for framework consumers.

Expected Behavior:
    - Aggregates properly separate state from behavior
    - Domain events are raised and applied correctly via multipledispatch
    - Business rules are enforced in domain entities
    - State transitions follow domain logic
    - Event sourcing reconstructs aggregate state correctly

Test Coverage:
    - AggregateRoot base class functionality
    - State separation pattern (AggregateState)
    - Domain event registration and application
    - Business rule validation
    - Value object immutability and equality

Related Documentation:
    - [Domain-Driven Design](../../docs/patterns/domain-driven-design.md)
    - [Clean Architecture](../../docs/patterns/clean-architecture.md)
    - [Mario's Pizzeria Domain](../../samples/mario-pizzeria/domain/)

References:
    - Framework: neuroglia.data.abstractions.AggregateRoot
    - Sample: samples/mario-pizzeria/domain/entities/
    - Pattern: Domain-Driven Design by Eric Evans
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import pytest
from multipledispatch import dispatch

from neuroglia.data.abstractions import AggregateRoot, AggregateState
from tests.fixtures import (
    OrderStatus,
    PizzaSize,
    create_customer,
    create_margherita_pizza,
)

# =============================================================================
# Test Domain Events
# =============================================================================


@dataclass
class PizzaCreatedEvent:
    """Domain event raised when a pizza is created"""

    aggregate_id: str
    name: str
    base_price: Decimal
    size: str  # PizzaSize value
    description: str
    toppings: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ToppingAddedEvent:
    """Domain event raised when a topping is added to a pizza"""

    aggregate_id: str
    topping: str
    price: Decimal
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrderCreatedEvent:
    """Domain event raised when an order is created"""

    aggregate_id: str
    customer_id: str
    order_time: datetime


@dataclass
class OrderConfirmedEvent:
    """Domain event raised when an order is confirmed"""

    aggregate_id: str
    confirmed_time: datetime
    estimated_ready_time: datetime


@dataclass
class PizzaAddedToOrderEvent:
    """Domain event raised when a pizza is added to an order"""

    aggregate_id: str
    pizza_name: str
    pizza_size: str
    quantity: int = 1


# =============================================================================
# Test Aggregates with State Separation
# =============================================================================


@dataclass
class PizzaState(AggregateState[str]):
    """
    State object for Pizza aggregate.

    Demonstrates proper state separation - contains only data, no behavior.
    Event handlers use multipledispatch for type-safe event application.
    """

    name: Optional[str] = None
    base_price: Optional[Decimal] = None
    size: Optional[PizzaSize] = None
    description: str = ""
    toppings: list[str] = field(default_factory=list)

    @dispatch(PizzaCreatedEvent)
    def on(self, event: PizzaCreatedEvent) -> None:
        """Handle PizzaCreatedEvent to initialize state"""
        self.id = event.aggregate_id
        self.name = event.name
        self.base_price = event.base_price
        self.size = PizzaSize(event.size)
        self.description = event.description
        self.toppings = event.toppings.copy()

    @dispatch(ToppingAddedEvent)
    def on(self, event: ToppingAddedEvent) -> None:
        """Handle ToppingAddedEvent to update toppings"""
        self.toppings.append(event.topping)


class Pizza(AggregateRoot[PizzaState, str]):
    """
    Pizza aggregate demonstrating DDD patterns.

    - State separation: All data in PizzaState
    - Behavior: Methods enforce business rules
    - Events: Domain events track state changes
    - Invariants: Business rules always enforced
    """

    def __init__(self, name: str, base_price: Decimal, size: PizzaSize, description: str = ""):
        super().__init__()

        # Validate business rules
        if base_price <= 0:
            raise ValueError("Pizza price must be positive")
        if not name or not name.strip():
            raise ValueError("Pizza must have a name")

        # Raise and apply creation event
        event = PizzaCreatedEvent(aggregate_id=self.id(), name=name, base_price=base_price, size=size.value, description=description, toppings=[])
        self.raise_and_apply_event(event)

    def add_topping(self, topping: str, price: Decimal = Decimal("1.50")) -> None:
        """
        Add a topping to the pizza.

        Business Rule: Topping price must be positive
        Side Effect: Raises ToppingAddedEvent
        """
        if price <= 0:
            raise ValueError("Topping price must be positive")
        if not topping or not topping.strip():
            raise ValueError("Topping must have a name")

        event = ToppingAddedEvent(aggregate_id=self.id(), topping=topping, price=price)
        self.raise_and_apply_event(event)

    @property
    def total_price(self) -> Decimal:
        """
        Calculate total price including size multiplier and toppings.

        Business Logic:
            - SMALL: base price
            - MEDIUM: base price * 1.3
            - LARGE: base price * 1.6
            - Each topping: +$1.50
        """
        size_multipliers = {PizzaSize.SMALL: Decimal("1.0"), PizzaSize.MEDIUM: Decimal("1.3"), PizzaSize.LARGE: Decimal("1.6")}

        multiplier = size_multipliers.get(self.state.size, Decimal("1.0"))
        base_total = self.state.base_price * multiplier
        topping_cost = Decimal("1.50") * len(self.state.toppings)

        return base_total + topping_cost


@dataclass
class OrderState(AggregateState[str]):
    """State for Order aggregate"""

    customer_id: Optional[str] = None
    pizza_names: list[str] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    order_time: Optional[datetime] = None
    confirmed_time: Optional[datetime] = None

    @dispatch(OrderCreatedEvent)
    def on(self, event: OrderCreatedEvent) -> None:
        self.id = event.aggregate_id
        self.customer_id = event.customer_id
        self.order_time = event.order_time
        self.status = OrderStatus.PENDING

    @dispatch(PizzaAddedToOrderEvent)
    def on(self, event: PizzaAddedToOrderEvent) -> None:
        for _ in range(event.quantity):
            self.pizza_names.append(event.pizza_name)

    @dispatch(OrderConfirmedEvent)
    def on(self, event: OrderConfirmedEvent) -> None:
        self.status = OrderStatus.CONFIRMED
        self.confirmed_time = event.confirmed_time


class Order(AggregateRoot[OrderState, str]):
    """Order aggregate demonstrating workflow management"""

    def __init__(self, customer_id: str):
        super().__init__()

        if not customer_id:
            raise ValueError("Order must have a customer")

        event = OrderCreatedEvent(aggregate_id=self.id(), customer_id=customer_id, order_time=datetime.now(timezone.utc))
        self.raise_and_apply_event(event)

    def add_pizza(self, pizza_name: str, pizza_size: PizzaSize, quantity: int = 1) -> None:
        """Add pizza(s) to the order"""
        if self.state.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot add pizzas to {self.state.status.value} order")

        event = PizzaAddedToOrderEvent(aggregate_id=self.id(), pizza_name=pizza_name, pizza_size=pizza_size.value, quantity=quantity)
        self.raise_and_apply_event(event)

    def confirm(self, estimated_minutes: int = 30) -> None:
        """Confirm the order"""
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Can only confirm pending orders")
        if not self.state.pizza_names:
            raise ValueError("Cannot confirm order with no pizzas")

        now = datetime.now(timezone.utc)
        from datetime import timedelta

        estimated_ready = now + timedelta(minutes=estimated_minutes)

        event = OrderConfirmedEvent(aggregate_id=self.id(), confirmed_time=now, estimated_ready_time=estimated_ready)
        self.raise_and_apply_event(event)


# =============================================================================
# Test Suite
# =============================================================================


class TestAggregateRootPatterns:
    """
    Test AggregateRoot base functionality.

    Validates that the framework's AggregateRoot provides:
    - Unique identity generation
    - Event sourcing support
    - State management
    - Event application via multipledispatch
    """

    def test_aggregate_generates_unique_identity(self):
        """
        Test that each aggregate instance gets a unique ID.

        Expected Behavior:
            - ID is automatically generated
            - ID is a valid UUID string
            - Different instances have different IDs

        Related: neuroglia.data.abstractions.AggregateRoot
        """
        pizza1 = Pizza("Margherita", Decimal("12.99"), PizzaSize.MEDIUM)
        pizza2 = Pizza("Pepperoni", Decimal("14.99"), PizzaSize.LARGE)

        assert pizza1.id() is not None
        assert pizza2.id() is not None
        assert pizza1.id() != pizza2.id()
        assert len(pizza1.id()) == 36  # UUID format

    def test_aggregate_state_initialized_correctly(self):
        """
        Test that aggregate state is properly initialized via events.

        Expected Behavior:
            - State starts empty (no constructor parameters stored directly)
            - Creation event initializes state
            - State contains all expected fields from event

        Related: samples/mario-pizzeria/domain/entities/pizza.py
        """
        pizza = Pizza("Margherita", Decimal("12.99"), PizzaSize.MEDIUM, "Classic Italian")

        assert pizza.state.name == "Margherita"
        assert pizza.state.base_price == Decimal("12.99")
        assert pizza.state.size == PizzaSize.MEDIUM
        assert pizza.state.description == "Classic Italian"
        assert pizza.state.toppings == []

    def test_aggregate_raises_domain_events(self):
        """
        Test that business operations raise domain events.

        Expected Behavior:
            - Events are raised during construction
            - Events are raised during state changes
            - Events are accessible via get_uncommitted_events()

        Related Documentation:
            - docs/patterns/domain-driven-design.md
            - docs/patterns/event-driven.md
        """
        pizza = Pizza("Margherita", Decimal("12.99"), PizzaSize.MEDIUM)
        pizza.add_topping("extra_cheese")

        events = pizza.get_uncommitted_events()

        assert len(events) == 2
        assert isinstance(events[0], PizzaCreatedEvent)
        assert isinstance(events[1], ToppingAddedEvent)
        assert events[1].topping == "extra_cheese"

    def test_aggregate_applies_events_to_state(self):
        """
        Test that events are applied to state via multipledispatch.

        Expected Behavior:
            - Events modify state through on() handlers
            - State reflects all applied events
            - Events are applied in order

        Related: neuroglia.data.abstractions.AggregateState
        """
        pizza = Pizza("Pepperoni", Decimal("14.99"), PizzaSize.LARGE)

        # Initial state from creation event
        assert pizza.state.name == "Pepperoni"
        assert len(pizza.state.toppings) == 0

        # Add toppings
        pizza.add_topping("extra_cheese")
        pizza.add_topping("mushrooms")

        # State updated by events
        assert len(pizza.state.toppings) == 2
        assert "extra_cheese" in pizza.state.toppings
        assert "mushrooms" in pizza.state.toppings

    def test_aggregate_marks_events_as_committed(self):
        """
        Test event lifecycle: uncommitted -> committed.

        Expected Behavior:
            - New events are uncommitted
            - mark_events_as_committed() clears uncommitted list
            - Can continue raising new events after commit

        Related: Event sourcing and repository patterns
        """
        pizza = Pizza("Supreme", Decimal("17.99"), PizzaSize.LARGE)

        # Has uncommitted creation event
        assert len(pizza.get_uncommitted_events()) == 1

        # Mark as committed (simulates repository save)
        pizza.mark_events_as_committed()
        assert len(pizza.get_uncommitted_events()) == 0

        # New events after commit
        pizza.add_topping("olives")
        assert len(pizza.get_uncommitted_events()) == 1


class TestBusinessRuleEnforcement:
    """
    Test that domain entities enforce business rules.

    Business rules should be enforced at the domain layer,
    not in application services or controllers.
    """

    def test_pizza_requires_positive_price(self):
        """
        Test that pizza price must be positive.

        Expected Behavior:
            - Negative price raises ValueError
            - Zero price raises ValueError
            - Positive price is accepted

        Business Rule: Pizzas cannot be free or have negative prices
        """
        with pytest.raises(ValueError, match="price must be positive"):
            Pizza("Invalid", Decimal("-5.00"), PizzaSize.MEDIUM)

        with pytest.raises(ValueError, match="price must be positive"):
            Pizza("Invalid", Decimal("0.00"), PizzaSize.MEDIUM)

        # Positive price OK
        pizza = Pizza("Valid", Decimal("0.01"), PizzaSize.SMALL)
        assert pizza.state.base_price == Decimal("0.01")

    def test_pizza_requires_name(self):
        """
        Test that pizza must have a name.

        Business Rule: Every pizza must be identifiable by name
        """
        with pytest.raises(ValueError, match="must have a name"):
            Pizza("", Decimal("12.99"), PizzaSize.MEDIUM)

        with pytest.raises(ValueError, match="must have a name"):
            Pizza("   ", Decimal("12.99"), PizzaSize.MEDIUM)

    def test_topping_requires_positive_price(self):
        """
        Test that topping price must be positive.

        Business Rule: Topping prices follow same rules as base prices
        """
        pizza = Pizza("Test", Decimal("10.00"), PizzaSize.MEDIUM)

        with pytest.raises(ValueError, match="price must be positive"):
            pizza.add_topping("invalid", Decimal("-1.00"))

        with pytest.raises(ValueError, match="price must be positive"):
            pizza.add_topping("invalid", Decimal("0.00"))

    def test_order_requires_customer(self):
        """
        Test that order must have a customer.

        Business Rule: Anonymous orders are not allowed
        """
        with pytest.raises(ValueError, match="must have a customer"):
            Order("")

        with pytest.raises(ValueError, match="must have a customer"):
            Order(None)

    def test_cannot_add_pizza_to_non_pending_order(self):
        """
        Test that pizzas can only be added to pending orders.

        Business Rule: Once confirmed, order contents are locked

        Related: samples/mario-pizzeria/domain/entities/order.py
        """
        order = Order(str(uuid4()))
        order.add_pizza("Margherita", PizzaSize.MEDIUM)
        order.confirm()

        # Now confirmed, can't add more pizzas
        with pytest.raises(ValueError, match="Cannot add pizzas"):
            order.add_pizza("Pepperoni", PizzaSize.LARGE)

    def test_cannot_confirm_order_without_pizzas(self):
        """
        Test that orders must have at least one pizza.

        Business Rule: Empty orders cannot be confirmed
        """
        order = Order(str(uuid4()))

        with pytest.raises(ValueError, match="no pizzas"):
            order.confirm()


class TestDomainLogic:
    """
    Test business logic implementation in domain entities.

    Domain entities should contain the core business logic,
    not just data storage.
    """

    def test_pizza_calculates_price_with_size_multiplier(self):
        """
        Test that pizza price varies by size.

        Business Logic:
            - SMALL: base price (1.0x)
            - MEDIUM: base price * 1.3
            - LARGE: base price * 1.6

        Related: samples/mario-pizzeria/domain/entities/pizza.py
        """
        base_price = Decimal("10.00")

        small = Pizza("Test", base_price, PizzaSize.SMALL)
        assert small.total_price == Decimal("10.00")

        medium = Pizza("Test", base_price, PizzaSize.MEDIUM)
        assert medium.total_price == Decimal("13.00")

        large = Pizza("Test", base_price, PizzaSize.LARGE)
        assert large.total_price == Decimal("16.00")

    def test_pizza_includes_topping_costs(self):
        """
        Test that toppings increase pizza price.

        Business Logic: Each topping adds $1.50 to total
        """
        pizza = Pizza("Margherita", Decimal("10.00"), PizzaSize.SMALL)

        # Base price only
        assert pizza.total_price == Decimal("10.00")

        # Add one topping
        pizza.add_topping("extra_cheese", Decimal("1.50"))
        assert pizza.total_price == Decimal("11.50")

        # Add another topping
        pizza.add_topping("mushrooms", Decimal("1.50"))
        assert pizza.total_price == Decimal("13.00")

    def test_pizza_combines_size_and_topping_pricing(self):
        """
        Test complex pricing: size multiplier + toppings.

        Business Logic:
            1. Apply size multiplier to base price
            2. Add topping costs ($1.50 each)
        """
        pizza = Pizza("Supreme", Decimal("10.00"), PizzaSize.LARGE)
        pizza.add_topping("olives", Decimal("1.50"))
        pizza.add_topping("peppers", Decimal("1.50"))

        # Base: $10 * 1.6 (LARGE) = $16
        # Toppings: 2 * $1.50 = $3
        # Total: $19
        assert pizza.total_price == Decimal("19.00")

    def test_order_tracks_pizza_additions(self):
        """
        Test that order maintains list of pizzas.

        Business Logic: Order aggregates pizza selections
        """
        order = Order(str(uuid4()))

        assert len(order.state.pizza_names) == 0

        order.add_pizza("Margherita", PizzaSize.MEDIUM, quantity=2)
        assert len(order.state.pizza_names) == 2

        order.add_pizza("Pepperoni", PizzaSize.LARGE)
        assert len(order.state.pizza_names) == 3

    def test_order_status_transitions(self):
        """
        Test order status lifecycle.

        Business Logic:
            PENDING -> CONFIRMED (via confirm())

        Related: samples/mario-pizzeria/domain/entities/order.py
        """
        order = Order(str(uuid4()))
        assert order.state.status == OrderStatus.PENDING

        order.add_pizza("Margherita", PizzaSize.MEDIUM)
        order.confirm()

        assert order.state.status == OrderStatus.CONFIRMED
        assert order.state.confirmed_time is not None


class TestEventSourcing:
    """
    Test event sourcing capabilities.

    Event sourcing allows rebuilding aggregate state from events,
    providing full audit trail and time-travel debugging.
    """

    def test_aggregate_state_can_be_reconstructed_from_events(self):
        """
        Test that aggregate can be rebuilt from event stream.

        Expected Behavior:
            1. Create aggregate and perform operations
            2. Extract event stream
            3. Create new instance and replay events
            4. New instance has same state as original

        Related Documentation:
            - docs/patterns/event-driven.md
            - docs/features/data-access.md (Event Store)
        """
        # Original aggregate with operations
        original = Pizza("Margherita", Decimal("12.99"), PizzaSize.MEDIUM, "Classic")
        original.add_topping("extra_cheese")
        original.add_topping("mushrooms")

        # Extract events
        events = original.get_uncommitted_events()

        # Reconstruct from events
        reconstructed = Pizza.__new__(Pizza)
        reconstructed.state = PizzaState()
        reconstructed._uncommitted_events = []

        for event in events:
            reconstructed.state.on(event)

        # States should match
        assert reconstructed.state.name == original.state.name
        assert reconstructed.state.base_price == original.state.base_price
        assert reconstructed.state.size == original.state.size
        assert reconstructed.state.toppings == original.state.toppings

    def test_events_provide_audit_trail(self):
        """
        Test that events provide complete history of changes.

        Expected Behavior:
            - Every state change has corresponding event
            - Events contain sufficient data for audit
            - Events are immutable once raised

        Use Case: Compliance, debugging, analytics
        """
        pizza = Pizza("Supreme", Decimal("17.99"), PizzaSize.LARGE)
        pizza.add_topping("olives")
        pizza.add_topping("peppers")

        events = pizza.get_uncommitted_events()

        # Audit trail
        assert len(events) == 3  # Created + 2 toppings

        # Each event has timestamp
        for event in events:
            assert hasattr(event, "timestamp")
            assert isinstance(event.timestamp, datetime)

        # Events contain business data
        creation_event = events[0]
        assert creation_event.name == "Supreme"
        assert creation_event.base_price == Decimal("17.99")

        topping_events = events[1:]
        topping_names = [e.topping for e in topping_events]
        assert "olives" in topping_names
        assert "peppers" in topping_names


# =============================================================================
# Integration with Test Fixtures
# =============================================================================


class TestWithFixtures:
    """
    Demonstrate using test fixtures for realistic scenarios.

    These tests show how to leverage the test data factories
    for complex test scenarios.
    """

    def test_create_pizza_from_fixture_data(self):
        """
        Test creating pizza using fixture factory.

        Demonstrates: Using test_data factories for consistent test data

        Related: tests/fixtures/test_data.py
        """
        pizza_data = create_margherita_pizza(size=PizzaSize.LARGE)

        pizza = Pizza(pizza_data["name"], pizza_data["base_price"], pizza_data["size"], pizza_data["description"])

        for topping in pizza_data["toppings"][:3]:  # Add first 3 toppings
            pizza.add_topping(topping)

        assert pizza.state.name == "Margherita"
        assert pizza.state.size == PizzaSize.LARGE
        assert len(pizza.state.toppings) >= 3

    def test_create_order_workflow_with_fixtures(self):
        """
        Test complete order workflow using fixtures.

        Demonstrates: End-to-end domain logic testing

        Related: tests/fixtures/test_data.py, samples/mario-pizzeria/
        """
        # Create customer
        customer_data = create_customer()
        customer_id = customer_data["id"]

        # Create order
        order = Order(customer_id)
        assert order.state.status == OrderStatus.PENDING

        # Add pizzas
        order.add_pizza("Margherita", PizzaSize.MEDIUM, quantity=2)
        order.add_pizza("Pepperoni", PizzaSize.LARGE, quantity=1)

        # Confirm order
        order.confirm(estimated_minutes=30)

        # Validate final state
        assert order.state.status == OrderStatus.CONFIRMED
        assert len(order.state.pizza_names) == 3
        assert order.state.customer_id == customer_id
        assert order.state.confirmed_time is not None

        # Check events
        events = order.get_uncommitted_events()
        assert len(events) == 4  # Created + 2 pizza adds + confirmed
