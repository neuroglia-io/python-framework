# Part 2: Domain Model & Business Rules

**Time: 45 minutes** | **Prerequisites: [Part 1](mario-pizzeria-01-setup.md)**

In this tutorial, you'll learn how to model your business domain using Domain-Driven Design (DDD) principles. We'll create entities with business rules, understand aggregates, and use domain events.

## 🎯 What You'll Learn

- The difference between `Entity`, `AggregateRoot`, and `AggregateState`
- How to enforce business rules at the domain layer
- What domain events are and why they matter
- Value objects for type safety and validation

## 🧱 Domain-Driven Design Basics

### The Problem

Traditional "anemic" domain models have no behavior:

```python
# ❌ Anemic model - just data, no logic
class Order:
    def __init__(self):
        self.id = None
        self.items = []
        self.status = "pending"
        self.total = 0.0
```

All business logic ends up in services, making code hard to test and maintain.

### The Solution: Rich Domain Models

**Rich domain models** contain both data AND behavior:

```python
# ✅ Rich model - data + business rules
class Order(AggregateRoot):
    def add_item(self, pizza):
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")
        self.items.append(pizza)
        self.raise_event(PizzaAddedEvent(...))
```

Business rules live where they belong: **in the domain**.

## 📦 Creating Domain Entities

### Step 1: Define Enums and Value Objects

Create `domain/entities/enums.py`:

```python
"""Domain enumerations"""
from enum import Enum

class OrderStatus(str, Enum):
    """Order lifecycle states"""
    PENDING = "pending"         # Order created, not confirmed
    CONFIRMED = "confirmed"     # Customer confirmed order
    COOKING = "cooking"         # Kitchen is preparing
    READY = "ready"             # Ready for pickup/delivery
    DELIVERING = "delivering"   # Out for delivery
    DELIVERED = "delivered"     # Completed
    CANCELLED = "cancelled"     # Cancelled by customer/staff

class PizzaSize(str, Enum):
    """Available pizza sizes"""
    SMALL = "small"      # 10 inch
    MEDIUM = "medium"    # 12 inch
    LARGE = "large"      # 14 inch
    XLARGE = "xlarge"    # 16 inch
```

Create `domain/entities/order_item.py` (value object):

```python
"""OrderItem value object"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from .enums import PizzaSize

@dataclass
class OrderItem:
    """
    Value object representing a pizza in an order.

    Value objects:
    - Are immutable (no setters)
    - Are compared by value, not identity
    - Have no lifecycle (created/destroyed with aggregate)
    """
    line_item_id: str
    name: str
    size: PizzaSize
    quantity: int
    unit_price: Decimal

    @property
    def total_price(self) -> Decimal:
        """Calculate total price for this line item"""
        return self.unit_price * self.quantity

    @staticmethod
    def create(name: str, size: PizzaSize, quantity: int, unit_price: Decimal):
        """Factory method for creating order items"""
        return OrderItem(
            line_item_id=str(uuid4()),
            name=name,
            size=size,
            quantity=quantity,
            unit_price=unit_price
        )
```

**Why value objects?**

- **Type Safety**: Can't pass a string where an `OrderItem` is expected
- **Validation**: Business rules enforced at creation
- **Immutability**: No accidental modifications
- **Reusability**: Shared across aggregates

### Step 2: Define Domain Events

Create `domain/events/__init__.py`:

```python
"""Domain events for Mario's Pizzeria"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from neuroglia.eventing.domain_event import DomainEvent

@dataclass
class OrderCreatedEvent(DomainEvent):
    """Raised when a new order is created"""
    aggregate_id: str
    customer_id: str
    order_time: datetime

@dataclass
class PizzaAddedToOrderEvent(DomainEvent):
    """Raised when a pizza is added to an order"""
    aggregate_id: str
    line_item_id: str
    pizza_name: str
    pizza_size: str
    price: Decimal

@dataclass
class OrderConfirmedEvent(DomainEvent):
    """Raised when customer confirms the order"""
    aggregate_id: str
    confirmed_time: datetime

@dataclass
class CookingStartedEvent(DomainEvent):
    """Raised when kitchen starts cooking"""
    aggregate_id: str
    cooking_started_time: datetime
    user_id: str
    user_name: str

@dataclass
class OrderReadyEvent(DomainEvent):
    """Raised when order is ready for pickup/delivery"""
    aggregate_id: str
    ready_time: datetime
    user_id: str
    user_name: str

@dataclass
class OrderCancelledEvent(DomainEvent):
    """Raised when order is cancelled"""
    aggregate_id: str
    reason: str
```

**What are domain events?**

Domain events represent **things that happened** in your business domain. They:

- Enable **event-driven architecture** (other parts of the system can react)
- Provide **audit trails** (who did what, when)
- Enable **eventual consistency** (updates can be async)
- Decouple aggregates (Order doesn't need to know about Kitchen)

### Step 3: Create Aggregate State

Create `domain/entities/order.py`:

```python
"""Order entity for Mario's Pizzeria domain"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from multipledispatch import dispatch

from neuroglia.data.abstractions import AggregateRoot, AggregateState

from .enums import OrderStatus
from .order_item import OrderItem
from domain.events import (
    OrderCreatedEvent,
    PizzaAddedToOrderEvent,
    PizzaRemovedFromOrderEvent,
    OrderConfirmedEvent,
    CookingStartedEvent,
    OrderReadyEvent,
    OrderCancelledEvent,
)

class OrderState(AggregateState[str]):
    """
    State for Order aggregate - contains all persisted data.

    AggregateState:
    - Holds the current state of the aggregate
    - Updates via event handlers (on() methods)
    - Separated from business logic (in AggregateRoot)
    """

    # Type annotations for JSON serialization
    customer_id: Optional[str]
    order_items: list[OrderItem]
    status: OrderStatus
    order_time: Optional[datetime]
    confirmed_time: Optional[datetime]
    cooking_started_time: Optional[datetime]
    actual_ready_time: Optional[datetime]
    estimated_ready_time: Optional[datetime]
    notes: Optional[str]

    def __init__(self):
        super().__init__()
        self.customer_id = None
        self.order_items = []
        self.status = OrderStatus.PENDING
        self.order_time = None
        self.confirmed_time = None
        self.cooking_started_time = None
        self.actual_ready_time = None
        self.estimated_ready_time = None
        self.notes = None

    @dispatch(OrderCreatedEvent)
    def on(self, event: OrderCreatedEvent) -> None:
        """Handle order creation event"""
        self.id = event.aggregate_id
        self.customer_id = event.customer_id
        self.order_time = event.order_time
        self.status = OrderStatus.PENDING

    @dispatch(PizzaAddedToOrderEvent)
    def on(self, event: PizzaAddedToOrderEvent) -> None:
        """Handle pizza added - state updated by business logic"""
        pass  # Items added directly in aggregate

    @dispatch(OrderConfirmedEvent)
    def on(self, event: OrderConfirmedEvent) -> None:
        """Handle order confirmation"""
        self.status = OrderStatus.CONFIRMED
        self.confirmed_time = event.confirmed_time

    @dispatch(CookingStartedEvent)
    def on(self, event: CookingStartedEvent) -> None:
        """Handle cooking started"""
        self.status = OrderStatus.COOKING
        self.cooking_started_time = event.cooking_started_time

    @dispatch(OrderReadyEvent)
    def on(self, event: OrderReadyEvent) -> None:
        """Handle order ready"""
        self.status = OrderStatus.READY
        self.actual_ready_time = event.ready_time

    @dispatch(OrderCancelledEvent)
    def on(self, event: OrderCancelledEvent) -> None:
        """Handle order cancellation"""
        self.status = OrderStatus.CANCELLED
        if event.reason:
            self.notes = f"Cancelled: {event.reason}"
```

**Why separate state from aggregate?**

- **Event Sourcing Ready**: State rebuilds from events
- **Testability**: Can test state changes independently
- **Persistence**: State is what gets saved to database
- **Clarity**: Clear separation between data and behavior

### Step 4: Create Aggregate Root

Continue in `domain/entities/order.py`:

```python
class Order(AggregateRoot[OrderState, str]):
    """
    Order aggregate root with business rules and lifecycle management.

    AggregateRoot:
    - Enforces business rules
    - Raises domain events
    - Controls state transitions
    - Transaction boundary (save/load as a unit)
    """

    def __init__(self, customer_id: str, estimated_ready_time: Optional[datetime] = None):
        super().__init__()

        # Raise and apply creation event
        self.state.on(
            self.register_event(
                OrderCreatedEvent(
                    aggregate_id=str(uuid4()),
                    customer_id=customer_id,
                    order_time=datetime.now(timezone.utc)
                )
            )
        )

        if estimated_ready_time:
            self.state.estimated_ready_time = estimated_ready_time

    # Properties for calculated values
    @property
    def total_amount(self) -> Decimal:
        """Calculate total order amount"""
        return sum(
            (item.total_price for item in self.state.order_items),
            Decimal("0.00")
        )

    @property
    def pizza_count(self) -> int:
        """Get total number of pizzas"""
        return len(self.state.order_items)

    # Business operations
    def add_order_item(self, order_item: OrderItem) -> None:
        """
        Add a pizza to the order.

        Business Rule: Can only modify pending orders
        """
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")

        # Update state
        self.state.order_items.append(order_item)

        # Raise event
        self.state.on(
            self.register_event(
                PizzaAddedToOrderEvent(
                    aggregate_id=self.id(),
                    line_item_id=order_item.line_item_id,
                    pizza_name=order_item.name,
                    pizza_size=order_item.size.value,
                    price=order_item.total_price
                )
            )
        )

    def remove_pizza(self, line_item_id: str) -> None:
        """
        Remove a pizza from the order.

        Business Rule: Can only modify pending orders
        """
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")

        # Remove from state
        self.state.order_items = [
            item for item in self.state.order_items
            if item.line_item_id != line_item_id
        ]

        # Raise event
        self.state.on(
            self.register_event(
                PizzaRemovedFromOrderEvent(
                    aggregate_id=self.id(),
                    line_item_id=line_item_id
                )
            )
        )

    def confirm_order(self) -> None:
        """
        Confirm the order.

        Business Rules:
        - Only pending orders can be confirmed
        - Must have at least one item
        """
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be confirmed")

        if len(self.state.order_items) == 0:
            raise ValueError("Cannot confirm empty order")

        # Update state and raise event
        self.state.on(
            self.register_event(
                OrderConfirmedEvent(
                    aggregate_id=self.id(),
                    confirmed_time=datetime.now(timezone.utc)
                )
            )
        )

    def start_cooking(self, user_id: str, user_name: str) -> None:
        """
        Start cooking the order.

        Business Rule: Only confirmed orders can be cooked
        """
        if self.state.status != OrderStatus.CONFIRMED:
            raise ValueError("Only confirmed orders can be cooked")

        self.state.on(
            self.register_event(
                CookingStartedEvent(
                    aggregate_id=self.id(),
                    cooking_started_time=datetime.now(timezone.utc),
                    user_id=user_id,
                    user_name=user_name
                )
            )
        )

    def mark_ready(self, user_id: str, user_name: str) -> None:
        """
        Mark order as ready.

        Business Rule: Only cooking orders can be marked ready
        """
        if self.state.status != OrderStatus.COOKING:
            raise ValueError("Only cooking orders can be marked ready")

        self.state.on(
            self.register_event(
                OrderReadyEvent(
                    aggregate_id=self.id(),
                    ready_time=datetime.now(timezone.utc),
                    user_id=user_id,
                    user_name=user_name
                )
            )
        )

    def cancel_order(self, reason: str) -> None:
        """
        Cancel the order.

        Business Rule: Cannot cancel delivered orders
        """
        if self.state.status == OrderStatus.DELIVERED:
            raise ValueError("Cannot cancel delivered orders")

        self.state.on(
            self.register_event(
                OrderCancelledEvent(
                    aggregate_id=self.id(),
                    reason=reason
                )
            )
        )
```

## 🧪 Testing Your Domain Model

Create `tests/domain/test_order.py`:

```python
"""Tests for Order domain entity"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from domain.entities import Order, OrderItem, PizzaSize, OrderStatus
from domain.events import OrderCreatedEvent, PizzaAddedToOrderEvent, OrderConfirmedEvent

def test_create_order():
    """Test order creation"""
    order = Order(customer_id="cust-123")

    assert order.state.customer_id == "cust-123"
    assert order.state.status == OrderStatus.PENDING
    assert order.pizza_count == 0

    # Check event was raised
    events = order.get_uncommitted_events()
    assert len(events) == 1
    assert isinstance(events[0], OrderCreatedEvent)

def test_add_pizza_to_order():
    """Test adding pizza to order"""
    order = Order(customer_id="cust-123")

    item = OrderItem.create(
        name="Margherita",
        size=PizzaSize.LARGE,
        quantity=1,
        unit_price=Decimal("12.99")
    )

    order.add_order_item(item)

    assert order.pizza_count == 1
    assert order.total_amount == Decimal("12.99")

    # Check event
    events = order.get_uncommitted_events()
    assert any(isinstance(e, PizzaAddedToOrderEvent) for e in events)

def test_cannot_modify_confirmed_order():
    """Test business rule: cannot modify confirmed orders"""
    order = Order(customer_id="cust-123")

    item = OrderItem.create(
        name="Pepperoni",
        size=PizzaSize.MEDIUM,
        quantity=1,
        unit_price=Decimal("10.99")
    )

    order.add_order_item(item)
    order.confirm_order()

    # Should raise error
    with pytest.raises(ValueError, match="Cannot modify confirmed orders"):
        order.add_order_item(item)

def test_cannot_confirm_empty_order():
    """Test business rule: cannot confirm empty order"""
    order = Order(customer_id="cust-123")

    with pytest.raises(ValueError, match="Cannot confirm empty order"):
        order.confirm_order()

def test_order_lifecycle():
    """Test complete order lifecycle"""
    order = Order(customer_id="cust-123")

    # Add pizza
    item = OrderItem.create("Margherita", PizzaSize.LARGE, 1, Decimal("12.99"))
    order.add_order_item(item)

    # Confirm
    order.confirm_order()
    assert order.state.status == OrderStatus.CONFIRMED

    # Start cooking
    order.start_cooking(user_id="chef-1", user_name="Mario")
    assert order.state.status == OrderStatus.COOKING

    # Mark ready
    order.mark_ready(user_id="chef-1", user_name="Mario")
    assert order.state.status == OrderStatus.READY
```

Run tests:

```bash
poetry run pytest tests/domain/ -v
```

## 📝 Key Takeaways

1. **Rich Domain Models**: Business logic lives in the domain, not services
2. **Aggregate Pattern**: `AggregateRoot` + `AggregateState` for encapsulation
3. **Domain Events**: Track what happened, enable event-driven architecture
4. **Value Objects**: Immutable, validated, compared by value
5. **Business Rules**: Enforced in domain methods with clear error messages

## 🚀 What's Next?

In [Part 3: Commands & Queries](mario-pizzeria-03-cqrs.md), you'll learn:

- How to implement CQRS (Command Query Responsibility Segregation)
- Creating commands and queries
- Writing command/query handlers
- Using the mediator to route requests

---

**Previous:** [← Part 1: Project Setup](mario-pizzeria-01-setup.md) | **Next:** [Part 3: Commands & Queries →](mario-pizzeria-03-cqrs.md)
