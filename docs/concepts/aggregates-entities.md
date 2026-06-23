# Aggregates & Entities

**Time to read: 12 minutes**

Aggregates are **clusters of domain objects** treated as a single unit for data changes. They're the key to maintaining consistency in complex domain models.

## ❌ The Problem: Inconsistent State

Without aggregates, related objects can become inconsistent:

```python
# ❌ No aggregate - objects can be inconsistent
order = Order(id="123")
order.status = "confirmed"

# Someone modifies items after confirmation
order.items.append(OrderItem("Pepperoni", 1))  # Breaks business rule!

# Someone changes delivery without validation
order.delivery_address = None  # Confirmed order with no address!

# Total out of sync with items
order.total = 50.0  # Items actually total $75!
```

**Problems:**

1. **No consistency**: Related objects can contradict each other
2. **No invariants**: Business rules not enforced
3. **No boundaries**: Anyone can modify anything
4. **Race conditions**: Concurrent changes cause conflicts
5. **Hard to reason about**: Too many moving parts

## ✅ The Solution: Aggregate Pattern

Group related objects with **one root** controlling access:

```
┌────────────────────────────────────────────┐
│ Order Aggregate (Consistency Boundary)     │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ Order (Aggregate Root)               │ │
│  │ - id, customer_id, status, created   │ │
│  │ - add_item(), confirm(), cancel()    │ │
│  └──────────────────────────────────────┘ │
│           │                                 │
│           ├─→ OrderItem (value object)     │
│           ├─→ OrderItem (value object)     │
│           └─→ DeliveryAddress (value obj)  │
│                                            │
└────────────────────────────────────────────┘

Rules:
1. External code ONLY accesses Order (root)
2. Order enforces ALL consistency rules
3. Order and items saved/loaded as ONE UNIT
4. Changes happen through Order methods only
```

**Benefits:**

1. **Guaranteed consistency**: Root enforces invariants
2. **Clear boundaries**: One entry point
3. **Transactional**: Aggregate saved as a unit
4. **Concurrency control**: Lock at aggregate level
5. **Easy to reason about**: Complexity contained

## 🏗️ Anatomy of an Aggregate

### Aggregate Root

The **single entry point** for the aggregate:

```python
class Order:  # AGGREGATE ROOT
    """
    Order aggregate root.
    - External code accesses order through this class
    - Order controls all its child objects
    - Order enforces business invariants
    """

    def __init__(self, customer_id: str):
        self.id = str(uuid.uuid4())
        self.customer_id = customer_id
        self._items: List[OrderItem] = []  # Private!
        self._status = OrderStatus.PENDING
        self._delivery_address: Optional[DeliveryAddress] = None

    # ✅ Public methods enforce rules
    def add_item(self, pizza_name: str, size: PizzaSize, quantity: int, price: Decimal):
        """Add item through root - rules enforced!"""
        if self._status != OrderStatus.PENDING:
            raise InvalidOperationError("Cannot modify confirmed orders")

        item = OrderItem(pizza_name, size, quantity, price)
        self._items.append(item)

    def set_delivery_address(self, address: DeliveryAddress):
        """Set address through root - validation enforced!"""
        if not address.street or not address.city:
            raise ValueError("Complete address required")

        self._delivery_address = address

    def confirm(self):
        """Confirm order - invariants checked!"""
        if not self._items:
            raise InvalidOperationError("Cannot confirm empty order")

        if not self._delivery_address:
            raise InvalidOperationError("Delivery address required")

        if self.total() < Decimal("10"):
            raise InvalidOperationError("Minimum order is $10")

        self._status = OrderStatus.CONFIRMED

    def total(self) -> Decimal:
        """Calculate total - always consistent with items!"""
        return sum(item.subtotal() for item in self._items)

    # Read-only access to children
    @property
    def items(self) -> List[OrderItem]:
        return self._items.copy()  # Return copy, not reference!

    @property
    def status(self) -> OrderStatus:
        return self._status
```

### Child Objects

**Internal to aggregate**, accessed through root:

```python
@dataclass(frozen=True)  # Immutable value object
class OrderItem:
    """Child object of Order aggregate."""
    pizza_name: str
    size: PizzaSize
    quantity: int
    price: Decimal

    def subtotal(self) -> Decimal:
        return self.price * self.quantity

@dataclass(frozen=True)
class DeliveryAddress:
    """Child object of Order aggregate."""
    street: str
    city: str
    zip_code: str
    delivery_instructions: Optional[str] = None
```

## 🔧 Aggregates in Neuroglia

### Using Entity and AggregateRoot

Neuroglia provides base classes:

```python
from neuroglia.core import Entity, AggregateRoot

class Order(AggregateRoot):
    """
    AggregateRoot provides:
    - Unique ID generation
    - Domain event collection
    - Event raising/retrieval
    """

    def __init__(self, customer_id: str):
        super().__init__()  # Generates ID, initializes events
        self.customer_id = customer_id
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING

        # Raise domain event
        self.raise_event(OrderCreatedEvent(
            order_id=self.id,
            customer_id=customer_id
        ))

    def add_item(self, pizza_name: str, size: PizzaSize, quantity: int, price: Decimal):
        # Validation
        if self.status != OrderStatus.PENDING:
            raise InvalidOperationError("Cannot modify confirmed orders")

        # Create value object
        item = OrderItem(pizza_name, size, quantity, price)
        self.items.append(item)

        # Raise domain event
        self.raise_event(ItemAddedToOrderEvent(
            order_id=self.id,
            pizza_name=pizza_name,
            quantity=quantity
        ))

    def confirm(self):
        # Business rules
        if not self.items:
            raise InvalidOperationError("Cannot confirm empty order")

        if self.total() < Decimal("10"):
            raise InvalidOperationError("Minimum order is $10")

        # State change
        self.status = OrderStatus.CONFIRMED

        # Raise domain event
        self.raise_event(OrderConfirmedEvent(
            order_id=self.id,
            customer_id=self.customer_id,
            total=self.total()
        ))

    def total(self) -> Decimal:
        return sum(item.subtotal() for item in self.items)

    # Get uncommitted events (for persistence)
    def get_uncommitted_events(self) -> List[DomainEvent]:
        return self._uncommitted_events.copy()
```

### Aggregate Boundaries

**Rule 1: One Aggregate Root per Aggregate**

```python
# ✅ CORRECT: Order is the only root
class Order(AggregateRoot):
    def __init__(self):
        self.items: List[OrderItem] = []  # Child objects

# ❌ WRONG: Making child an aggregate root too
class OrderItem(AggregateRoot):  # Don't do this!
    pass
```

**Rule 2: Reference Other Aggregates by ID**

```python
# ✅ CORRECT: Reference Customer by ID
class Order(AggregateRoot):
    def __init__(self, customer_id: str):
        self.customer_id = customer_id  # ID reference

# ❌ WRONG: Embedding entire Customer aggregate
class Order(AggregateRoot):
    def __init__(self, customer: Customer):
        self.customer = customer  # Entire object - NO!
```

**Rule 3: Small Aggregates**

```python
# ✅ GOOD: Small, focused aggregate
class Order(AggregateRoot):
    def __init__(self):
        self.items: List[OrderItem] = []  # 1-10 items typical
        self.delivery_address: DeliveryAddress = None

# ❌ BAD: Huge aggregate
class Order(AggregateRoot):
    def __init__(self):
        self.customer: Customer = None  # Entire customer!
        self.items: List[OrderItem] = []
        self.payments: List[Payment] = []  # Separate aggregate
        self.shipments: List[Shipment] = []  # Separate aggregate
        self.reviews: List[Review] = []  # Separate aggregate
# Too big! Contention, performance issues
```

### Event Sourcing with Aggregates

Neuroglia supports event-sourced aggregates:

```python
from neuroglia.core import AggregateState

class OrderState(AggregateState):
    """
    State rebuilt from events.
    Each event handler updates state.
    """

    def __init__(self):
        super().__init__()
        self.customer_id: Optional[str] = None
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING

    # Event handlers rebuild state
    def on_order_created(self, event: OrderCreatedEvent):
        self.customer_id = event.customer_id
        self.status = OrderStatus.PENDING

    def on_item_added(self, event: ItemAddedToOrderEvent):
        item = OrderItem(
            event.pizza_name,
            event.size,
            event.quantity,
            event.price
        )
        self.items.append(item)

    def on_order_confirmed(self, event: OrderConfirmedEvent):
        self.status = OrderStatus.CONFIRMED

class Order(AggregateRoot):
    """Event-sourced aggregate."""

    def __init__(self, state: OrderState):
        super().__init__()
        self.state = state

    def add_item(self, pizza_name: str, size: PizzaSize, quantity: int, price: Decimal):
        # Validate against current state
        if self.state.status != OrderStatus.PENDING:
            raise InvalidOperationError("Cannot modify confirmed orders")

        # Apply event (updates state + records event)
        self.apply_event(ItemAddedToOrderEvent(
            order_id=self.id,
            pizza_name=pizza_name,
            size=size,
            quantity=quantity,
            price=price
        ))
```

## 🧪 Testing Aggregates

### Test Invariants

```python
def test_cannot_add_item_to_confirmed_order():
    """Test aggregate enforces consistency."""
    order = Order(customer_id="123")
    order.add_item("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))
    order.confirm()

    # Attempt to violate invariant
    with pytest.raises(InvalidOperationError, match="confirmed orders"):
        order.add_item("Pepperoni", PizzaSize.MEDIUM, 1, Decimal("13.99"))

def test_cannot_confirm_order_without_items():
    """Test aggregate enforces business rules."""
    order = Order(customer_id="123")

    with pytest.raises(InvalidOperationError, match="empty order"):
        order.confirm()

def test_order_total_always_consistent():
    """Test calculated fields always match items."""
    order = Order(customer_id="123")
    order.add_item("Margherita", PizzaSize.LARGE, 2, Decimal("15.99"))
    order.add_item("Pepperoni", PizzaSize.MEDIUM, 1, Decimal("13.99"))

    # Total should always match items
    expected = (Decimal("15.99") * 2) + Decimal("13.99")
    assert order.total() == expected
```

### Test Domain Events

```python
def test_aggregate_raises_events():
    """Test domain events are raised."""
    order = Order(customer_id="123")
    order.add_item("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))
    order.confirm()

    events = order.get_uncommitted_events()

    assert len(events) == 3  # Created, ItemAdded, Confirmed
    assert isinstance(events[0], OrderCreatedEvent)
    assert isinstance(events[1], ItemAddedToOrderEvent)
    assert isinstance(events[2], OrderConfirmedEvent)
```

## ⚠️ Common Mistakes

### 1. Aggregates Too Large

```python
# ❌ WRONG: Everything in one aggregate
class Customer(AggregateRoot):
    def __init__(self):
        self.orders: List[Order] = []  # All orders!
        self.payments: List[Payment] = []  # All payments!
        self.reviews: List[Review] = []  # All reviews!
# Problem: Loading customer loads EVERYTHING

# ✅ RIGHT: Separate aggregates
class Customer(AggregateRoot):
    def __init__(self):
        self.name = ""
        self.email = ""
    # Orders are separate aggregates

class Order(AggregateRoot):
    def __init__(self):
        self.customer_id = ""  # Reference by ID
```

### 2. Public Mutable Collections

```python
# ❌ WRONG: Direct access to mutable list
class Order(AggregateRoot):
    def __init__(self):
        self.items: List[OrderItem] = []  # Public!

order.items.append(OrderItem(...))  # Bypasses validation!

# ✅ RIGHT: Private collection, controlled access
class Order(AggregateRoot):
    def __init__(self):
        self._items: List[OrderItem] = []  # Private

    def add_item(self, item: OrderItem):
        # Validation here
        self._items.append(item)

    @property
    def items(self) -> List[OrderItem]:
        return self._items.copy()  # Return copy
```

### 3. Violating Aggregate Boundaries

```python
# ❌ WRONG: Modifying another aggregate's internals
order = order_repository.get(order_id)
customer = customer_repository.get(order.customer_id)
customer.orders.append(order)  # Modifying Customer from Order!

# ✅ RIGHT: Each aggregate modifies itself
order = order_repository.get(order_id)
order.confirm()  # Order modifies itself

# Customer reacts via event
class OrderConfirmedHandler:
    async def handle(self, event: OrderConfirmedEvent):
        customer = await self.customer_repo.get(event.customer_id)
        customer.record_order(event.order_id)  # Customer modifies itself
```

### 4. Loading Multiple Aggregates in One Transaction

```python
# ❌ WRONG: Modifying two aggregates in one transaction
async def transfer_order(order_id: str, new_customer_id: str):
    order = await order_repo.get(order_id)
    old_customer = await customer_repo.get(order.customer_id)
    new_customer = await customer_repo.get(new_customer_id)

    old_customer.remove_order(order_id)
    new_customer.add_order(order_id)
    order.customer_id = new_customer_id

    await order_repo.save(order)
    await customer_repo.save(old_customer)
    await customer_repo.save(new_customer)
# Problem: What if one save fails?

# ✅ RIGHT: Use eventual consistency via events
async def transfer_order(order_id: str, new_customer_id: str):
    order = await order_repo.get(order_id)
    order.transfer_to_customer(new_customer_id)  # Raises event
    await order_repo.save(order)
    # Customers update via event handlers (eventually consistent)
```

## 🚫 When NOT to Use Aggregates

Aggregates add complexity. Skip when:

1. **Simple CRUD**: No business rules, just data entry
2. **Reporting**: Read-only queries don't need aggregates
3. **No Invariants**: If there are no consistency rules
4. **Single Entity**: If entity has no relationships
5. **Prototypes**: Quick experiments

For simple cases, plain entities work fine.

## 📝 Key Takeaways

1. **Aggregate Root**: Single entry point for aggregate
2. **Consistency Boundary**: Aggregate maintains invariants
3. **Transactional Unit**: Save/load aggregate as one unit
4. **Small Aggregates**: Keep aggregates focused and small
5. **ID References**: Reference other aggregates by ID, not object

## 🔄 Aggregates + Other Patterns

```
Aggregate Root (Entity)
  ↓ uses
Value Objects (immutable children)
  ↓ raises
Domain Events (state changes)
  ↓ persisted by
Repository (loads/saves aggregate)
  ↓ coordinated by
Unit of Work (transaction boundary)
```

## 🚀 Next Steps

- **See it implemented**: [Tutorial Part 2](../tutorials/mario-pizzeria-02-domain.md) builds Order aggregate
- **Understand persistence**: [Repository Pattern](repository.md) for saving aggregates
- **Event handling**: [Event-Driven Architecture](event-driven.md) for aggregate events

## 📚 Further Reading

- Vaughn Vernon's "Implementing Domain-Driven Design" (Chapter 10)
- Martin Fowler's ["DDD Aggregate"](https://martinfowler.com/bliki/DDD_Aggregate.html)
- [Effective Aggregate Design](https://www.dddcommunity.org/library/vernon_2011/) (Vernon)

---

**Previous:** [← Domain-Driven Design](domain-driven-design.md) | **Next:** [CQRS →](cqrs.md)
