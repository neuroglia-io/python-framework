# Domain-Driven Design (DDD)

**Time to read: 15 minutes**

Domain-Driven Design is an approach to software where **code mirrors business concepts and language**. Instead of thinking in database tables and CRUD operations, you model the real-world domain.

## ❌ The Problem: Anemic Domain Models

Traditional approach treats entities as dumb data containers:

```python
# ❌ Anemic model - just getters/setters, no behavior
class Order:
    def __init__(self):
        self.id = None
        self.customer_id = None
        self.items = []
        self.status = "pending"
        self.total = 0.0

    def get_total(self):
        return self.total

    def set_total(self, value):
        self.total = value

# Business logic scattered in services
class OrderService:
    def confirm_order(self, order_id):
        order = self.repository.get(order_id)

        # Business rules in service (far from data)
        if order.status != "pending":
            raise ValueError("Can only confirm pending orders")

        if order.total < 10:
            raise ValueError("Minimum order is $10")

        order.set_status("confirmed")
        self.repository.save(order)
        self.email_service.send("Order confirmed")
```

**Problems:**

1. **Business logic scattered**: Rules in services, not entities
2. **No ubiquitous language**: Code doesn't match business terms
3. **Easy to break rules**: Anyone can set any property
4. **Hard to understand**: Need to read services to understand behavior
5. **No domain events**: Changes don't trigger reactions

## ✅ The Solution: Rich Domain Models

Put business logic where it belongs - in domain entities:

```python
# ✅ Rich model - behavior and rules in the entity
class Order:
    def __init__(self, customer_id: str):
        self.id = str(uuid.uuid4())
        self.customer_id = customer_id
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING
        self._events: List[DomainEvent] = []

    def add_pizza(self, pizza: Pizza, quantity: int):
        """Add pizza to order. Business logic here!"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        item = OrderItem(pizza, quantity)
        self.items.append(item)

    def confirm(self):
        """Confirm order. Business rules enforced!"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Can only confirm pending orders")

        if self.total() < 10:
            raise ValueError("Minimum order is $10")

        self.status = OrderStatus.CONFIRMED
        self._events.append(OrderConfirmedEvent(self.id))  # Domain event!

    def total(self) -> Decimal:
        """Calculate total. Pure business logic."""
        return sum(item.subtotal() for item in self.items)
```

**Benefits:**

1. **Logic with data**: Rules and data together
2. **Ubiquitous language**: Methods match business terms (`confirm`, `add_pizza`)
3. **Encapsulation**: Can't break rules (no public setters)
4. **Self-documenting**: Read entity to understand business
5. **Domain events**: Changes trigger reactions

## 🏗️ DDD Building Blocks

### 1. Entities

Objects with **identity** that persists over time:

```python
class Order:
    def __init__(self, order_id: str):
        self.id = order_id  # Identity
        self.customer_id = None
        self.items = []

    def __eq__(self, other):
        return isinstance(other, Order) and self.id == other.id

# Two orders with same data but different IDs are DIFFERENT
order1 = Order("123")
order2 = Order("456")
assert order1 != order2  # Different entities
```

**Key**: Identity matters, not attributes.

### 2. Value Objects

Objects defined by **attributes**, not identity:

```python
@dataclass(frozen=True)  # Immutable!
class OrderItem:
    pizza_name: str
    size: PizzaSize
    quantity: int
    price: Decimal

    def subtotal(self) -> Decimal:
        return self.price * self.quantity

# Two items with same attributes are THE SAME
item1 = OrderItem("Margherita", PizzaSize.LARGE, 2, Decimal("15.99"))
item2 = OrderItem("Margherita", PizzaSize.LARGE, 2, Decimal("15.99"))
assert item1 == item2  # Same value object
```

**Key**: Immutable, equality by attributes, no identity.

### 3. Aggregates

**Cluster of entities/value objects** treated as a unit:

```
┌─────────────────────────────────────┐
│ Order Aggregate                     │
│                                     │
│  Order (Aggregate Root)             │
│  ├─ OrderItem (Value Object)       │
│  ├─ OrderItem (Value Object)       │
│  └─ DeliveryAddress (Value Object) │
│                                     │
└─────────────────────────────────────┘

Rules:
- External code only accesses Order (root)
- Order ensures consistency of items/address
- Save entire aggregate as a unit
```

```python
class Order:  # Aggregate Root
    def __init__(self):
        self.items: List[OrderItem] = []  # Part of aggregate

    def add_item(self, item: OrderItem):
        # Order controls its items
        self.items.append(item)

    def remove_item(self, item: OrderItem):
        # Order maintains consistency
        if item in self.items:
            self.items.remove(item)

# ❌ WRONG: Modify items directly
order.items.append(OrderItem(...))  # Bypasses rules!

# ✅ RIGHT: Go through aggregate root
order.add_item(OrderItem(...))  # Rules enforced
```

### 4. Domain Events

**Something that happened** in the domain:

```python
@dataclass
class OrderConfirmedEvent:
    order_id: str
    customer_id: str
    total: Decimal
    confirmed_at: datetime

class Order:
    def confirm(self):
        self.status = OrderStatus.CONFIRMED
        self._events.append(OrderConfirmedEvent(
            order_id=self.id,
            customer_id=self.customer_id,
            total=self.total(),
            confirmed_at=datetime.utcnow()
        ))
```

**Use for**: Triggering side effects, auditing, integration events.

### 5. Repositories

**Collection-like interface** for retrieving aggregates:

```python
class IOrderRepository(ABC):
    @abstractmethod
    async def get_by_id_async(self, order_id: str) -> Optional[Order]:
        """Get order aggregate by ID."""
        pass

    @abstractmethod
    async def save_async(self, order: Order) -> None:
        """Save order aggregate."""
        pass
```

**Key**: Repository only for aggregate roots, not individual entities.

## 🔧 DDD in Neuroglia

### Rich Domain Entities

```python
from neuroglia.core import Entity
from neuroglia.eventing import DomainEvent

class Order(Entity):
    """Order aggregate root."""

    def __init__(self, customer_id: str):
        super().__init__()  # Generates ID
        self.customer_id = customer_id
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING

    def add_pizza(self, pizza_name: str, size: PizzaSize, quantity: int, price: Decimal):
        """Business operation: add pizza to order."""
        # Validation (business rules)
        if self.status != OrderStatus.PENDING:
            raise InvalidOperationError("Cannot modify confirmed orders")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # Create value object
        item = OrderItem(
            pizza_name=pizza_name,
            size=size,
            quantity=quantity,
            price=price
        )

        # Modify state
        self.items.append(item)

        # Raise domain event
        self.raise_event(PizzaAddedToOrderEvent(
            order_id=self.id,
            pizza_name=pizza_name,
            quantity=quantity
        ))

    def confirm(self):
        """Business operation: confirm order."""
        # Business rules
        if self.status != OrderStatus.PENDING:
            raise InvalidOperationError("Order already confirmed")

        if not self.items:
            raise InvalidOperationError("Cannot confirm empty order")

        if self.total() < Decimal("10"):
            raise InvalidOperationError("Minimum order is $10")

        # State change
        self.status = OrderStatus.CONFIRMED

        # Domain event
        self.raise_event(OrderConfirmedEvent(
            order_id=self.id,
            customer_id=self.customer_id,
            total=self.total()
        ))

    def total(self) -> Decimal:
        """Calculate order total."""
        return sum(item.subtotal() for item in self.items)
```

### Ubiquitous Language

Use business terms everywhere:

```python
# ❌ Technical language
order.set_status(2)  # What does 2 mean?
order.validate()     # Validate what?
order.persist()      # Too technical

# ✅ Ubiquitous language (matches business)
order.confirm()      # Business term!
order.cancel()       # Business term!
order.start_cooking()  # Business term!
```

**Rule**: Code should read like a conversation with domain experts.

### Bounded Contexts

Large domains split into smaller contexts:

```
Mario's Pizzeria Domain:
├─ Orders Context (order placement, tracking)
├─ Kitchen Context (cooking, preparation)
├─ Delivery Context (driver assignment, routing)
├─ Menu Context (pizzas, pricing)
└─ Customer Context (accounts, preferences)

Each context has its own models!
```

```python
# Orders context: Order is about customer order
class Order:
    customer_id: str
    items: List[OrderItem]
    status: OrderStatus

# Kitchen context: Order is about preparation
class KitchenOrder:
    order_id: str
    pizzas: List[Pizza]
    preparation_status: PreparationStatus
    assigned_cook: str

# Same real-world concept, different models per context!
```

## 🧪 Testing DDD

### Unit Tests: Test Business Rules

```python
def test_cannot_confirm_empty_order():
    order = Order(customer_id="123")

    with pytest.raises(InvalidOperationError, match="empty order"):
        order.confirm()

def test_cannot_modify_confirmed_order():
    order = Order(customer_id="123")
    order.add_pizza("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))
    order.confirm()

    with pytest.raises(InvalidOperationError, match="confirmed orders"):
        order.add_pizza("Pepperoni", PizzaSize.MEDIUM, 1, Decimal("13.99"))

def test_order_total_calculation():
    order = Order(customer_id="123")
    order.add_pizza("Margherita", PizzaSize.LARGE, 2, Decimal("15.99"))
    order.add_pizza("Pepperoni", PizzaSize.MEDIUM, 1, Decimal("13.99"))

    assert order.total() == Decimal("45.97")  # (15.99 * 2) + 13.99
```

### Integration Tests: Test Repositories

```python
async def test_save_and_retrieve_order():
    repo = MongoOrderRepository()

    # Create aggregate
    order = Order(customer_id="123")
    order.add_pizza("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))
    order.confirm()

    # Save
    await repo.save_async(order)

    # Retrieve
    retrieved = await repo.get_by_id_async(order.id)

    assert retrieved.id == order.id
    assert retrieved.status == OrderStatus.CONFIRMED
    assert retrieved.total() == Decimal("15.99")
```

## ⚠️ Common Mistakes

### 1. Anemic Domain Models

```python
# ❌ WRONG: Just data, no behavior
class Order:
    def __init__(self):
        self.status = "pending"

# Business logic in service
class OrderService:
    def confirm(self, order):
        if order.status != "pending":
            raise ValueError()
        order.status = "confirmed"

# ✅ RIGHT: Behavior in entity
class Order:
    def confirm(self):
        if self.status != OrderStatus.PENDING:
            raise InvalidOperationError()
        self.status = OrderStatus.CONFIRMED
```

### 2. Public Setters

```python
# ❌ WRONG: Public setters bypass rules
class Order:
    def __init__(self):
        self.status = OrderStatus.PENDING

    def set_status(self, status):
        self.status = status  # No validation!

order.set_status(OrderStatus.CONFIRMED)  # Bypasses rules!

# ✅ RIGHT: Named methods with rules
class Order:
    def __init__(self):
        self._status = OrderStatus.PENDING

    @property
    def status(self):
        return self._status

    def confirm(self):
        if self._status != OrderStatus.PENDING:
            raise InvalidOperationError()
        self._status = OrderStatus.CONFIRMED
```

### 3. Breaking Aggregate Boundaries

```python
# ❌ WRONG: Accessing child entities directly
order_item = order.items[0]
order_item.quantity = 5  # Bypasses order!

# ✅ RIGHT: Go through aggregate root
order.update_item_quantity(item_id, new_quantity=5)
```

### 4. Too Many Aggregates

```python
# ❌ WRONG: Every entity is an aggregate
class Order: pass
class OrderItem: pass  # Separate aggregate
class DeliveryAddress: pass  # Separate aggregate

# Now need to manage consistency across 3 aggregates!

# ✅ RIGHT: One aggregate
class Order:  # Aggregate root
    def __init__(self):
        self.items = []  # Part of aggregate
        self.delivery_address = None  # Part of aggregate
```

## 🚫 When NOT to Use DDD

DDD has learning curve and overhead. Skip when:

1. **CRUD Applications**: Simple data entry, no business logic
2. **Reporting/Analytics**: Read-only, no state changes
3. **Prototypes**: Quick experiments, throwaway code
4. **Simple Domains**: No complex business rules
5. **Small Teams**: DDD shines with multiple developers

For simple apps, anemic models with service layers work fine.

## 📝 Key Takeaways

1. **Rich Models**: Behavior and data together in entities
2. **Ubiquitous Language**: Code matches business terminology
3. **Aggregates**: Consistency boundaries around related entities
4. **Domain Events**: Communicate state changes
5. **Repositories**: Collection-like access to aggregates

## 🔄 DDD + Clean Architecture

DDD lives in the **domain layer** of clean architecture:

```
Domain Layer (DDD):
- Rich entities with business logic
- Value objects for immutability
- Domain events for communication
- Repository interfaces

Application Layer:
- Uses domain entities
- Orchestrates business operations
- Handles domain events

Infrastructure Layer:
- Implements repositories
- Persists aggregates
- Publishes domain events
```

## 🚀 Next Steps

- **See it in action**: [Tutorial Part 2](../tutorials/mario-pizzeria-02-domain.md) builds DDD models
- **Understand aggregates**: [Aggregates & Entities](aggregates-entities.md) deep dive
- **Event-driven**: [Event-Driven Architecture](event-driven.md) uses domain events

## 📚 Further Reading

- Eric Evans' "Domain-Driven Design" (book)
- Vaughn Vernon's "Implementing Domain-Driven Design" (book)
- [Martin Fowler - Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)

---

**Previous:** [← Dependency Injection](dependency-injection.md) | **Next:** [Aggregates & Entities →](aggregates-entities.md)
