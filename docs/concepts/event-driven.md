# Event-Driven Architecture

**Time to read: 14 minutes**

Event-Driven Architecture uses **events** to communicate between parts of a system. When something happens, an event is published, and interested parties react - without knowing about each other.

## ❌ The Problem: Tight Coupling Through Direct Calls

Without events, components directly call each other:

```python
# ❌ Order service directly calls email and kitchen services
class OrderService:
    def __init__(self,
                 email_service: EmailService,
                 kitchen_service: KitchenService,
                 inventory_service: InventoryService,
                 analytics_service: AnalyticsService):
        # Depends on all services!
        self.email_service = email_service
        self.kitchen_service = kitchen_service
        self.inventory_service = inventory_service
        self.analytics_service = analytics_service

    async def confirm_order(self, order_id: str):
        order = await self.repository.get(order_id)
        order.status = "confirmed"
        await self.repository.save(order)

        # Directly calls all services
        await self.email_service.send_confirmation(order)
        await self.kitchen_service.start_preparing(order)
        await self.inventory_service.update_stock(order)
        await self.analytics_service.record_sale(order)

        # What if we need to add notification service?
        # What if email fails? Should order still confirm?
```

**Problems:**

1. **Tight coupling**: OrderService knows about all other services
2. **Hard to extend**: Adding feature requires changing OrderService
3. **Synchronous**: All operations block each other
4. **Cascading failures**: Email failure prevents order confirmation
5. **Hard to test**: Need to mock all services

## ✅ The Solution: Events as Communication

Components publish events, others subscribe and react:

```
┌─────────────────────────────────────────────┐
│          Event-Driven Flow                  │
│                                             │
│  ┌──────────┐                              │
│  │  Order   │                              │
│  │ Service  │                              │
│  └────┬─────┘                              │
│       │                                     │
│       │ Publishes "OrderConfirmed" Event   │
│       ▼                                     │
│  ┌──────────┐                              │
│  │ Event    │                              │
│  │   Bus    │                              │
│  └─────┬────┘                              │
│        │                                    │
│        │ Notifies subscribers               │
│        │                                    │
│   ┌────┼────┬────────┬─────────┐          │
│   ▼    ▼    ▼        ▼         ▼          │
│ Email Kitchen Inventory Analytics Notifications│
│ Handler Handler Handler Handler  Handler   │
│                                             │
│ Order doesn't know about handlers!         │
└─────────────────────────────────────────────┘
```

**Benefits:**

1. **Loose coupling**: Order doesn't know about subscribers
2. **Easy to extend**: Add handlers without changing Order
3. **Asynchronous**: Handlers run independently
4. **Resilient**: One handler failure doesn't affect others
5. **Easy to test**: Test Order without handlers

## 🏗️ Types of Events

### 1. Domain Events (Internal)

**What happened in the domain**:

```python
@dataclass
class OrderConfirmedEvent:
    """Domain event - something happened in the business domain."""
    order_id: str
    customer_id: str
    total: Decimal
    confirmed_at: datetime

@dataclass
class OrderCancelledEvent:
    """Domain event - order was cancelled."""
    order_id: str
    customer_id: str
    reason: str
    cancelled_at: datetime
```

**Characteristics:**

- **Past tense**: `OrderConfirmed`, `PaymentProcessed`
- **Internal**: Within your application
- **Rich**: Contains all relevant data
- **Immutable**: Can't be changed after creation

### 2. Integration Events (External)

**Communication with other systems**:

```python
from neuroglia.eventing.cloud_events import CloudEvent

# CloudEvent - standardized external event
event = CloudEvent(
    source="mario-pizzeria/orders",
    type="com.mariopizzeria.order.confirmed.v1",
    data={
        "order_id": "123",
        "customer_id": "456",
        "total": 45.99
    }
)
```

**Characteristics:**

- **Standardized**: CloudEvents spec
- **External**: Between microservices
- **Versioned**: `v1`, `v2` in type
- **Schema**: Well-defined structure

## 🔧 Events in Neuroglia

### Raising Domain Events

Entities raise events when state changes:

```python
from neuroglia.core import AggregateRoot
from neuroglia.eventing import DomainEvent

@dataclass
class OrderConfirmedEvent(DomainEvent):
    order_id: str
    customer_id: str
    total: Decimal

class Order(AggregateRoot):
    """Aggregate root raises events."""

    def __init__(self, customer_id: str):
        super().__init__()
        self.customer_id = customer_id
        self.items = []
        self.status = OrderStatus.PENDING

        # Raise event
        self.raise_event(OrderCreatedEvent(
            order_id=self.id,
            customer_id=customer_id
        ))

    def confirm(self):
        """Confirm order - raises event."""
        if self.status != OrderStatus.PENDING:
            raise InvalidOperationError("Can only confirm pending orders")

        if not self.items:
            raise InvalidOperationError("Cannot confirm empty order")

        # Change state
        self.status = OrderStatus.CONFIRMED

        # Raise domain event
        self.raise_event(OrderConfirmedEvent(
            order_id=self.id,
            customer_id=self.customer_id,
            total=self.total()
        ))
```

### Event Handlers

React to events:

```python
from neuroglia.eventing import DomainEventHandler

class SendConfirmationEmailHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Handles OrderConfirmedEvent by sending email."""

    def __init__(self, email_service: IEmailService):
        self.email_service = email_service

    async def handle_async(self, event: OrderConfirmedEvent):
        """React to order confirmation."""
        await self.email_service.send_confirmation(
            customer_id=event.customer_id,
            order_id=event.order_id,
            total=event.total
        )

class StartCookingHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Handles OrderConfirmedEvent by notifying kitchen."""

    def __init__(self, kitchen_service: IKitchenService):
        self.kitchen_service = kitchen_service

    async def handle_async(self, event: OrderConfirmedEvent):
        """Start preparing the order."""
        await self.kitchen_service.start_preparing(event.order_id)

class UpdateInventoryHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Handles OrderConfirmedEvent by updating inventory."""

    def __init__(self, inventory_service: IInventoryService):
        self.inventory_service = inventory_service

    async def handle_async(self, event: OrderConfirmedEvent):
        """Update ingredient inventory."""
        await self.inventory_service.deduct_ingredients(event.order_id)

# Multiple handlers for same event!
# They run independently - one failure doesn't affect others
```

### Event Dispatch

Events dispatched automatically via Unit of Work:

```python
class OrderRepository:
    def __init__(self, unit_of_work: IUnitOfWork):
        self.unit_of_work = unit_of_work

    async def save_async(self, order: Order):
        # Save order
        await self.collection.insert_one(order.to_dict())

        # Dispatch events
        await self.unit_of_work.save_changes_async(order)
        # ↑ This publishes all uncommitted events from order
```

### Publishing Integration Events

For external systems:

```python
from neuroglia.eventing.cloud_events import CloudEvent, CloudEventPublisher

class PublishOrderConfirmedHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Publishes external integration event."""

    def __init__(self, publisher: CloudEventPublisher):
        self.publisher = publisher

    async def handle_async(self, event: OrderConfirmedEvent):
        """Publish CloudEvent for other microservices."""
        cloud_event = CloudEvent(
            source="mario-pizzeria/orders",
            type="com.mariopizzeria.order.confirmed.v1",
            data={
                "order_id": event.order_id,
                "customer_id": event.customer_id,
                "total": float(event.total),
                "confirmed_at": event.confirmed_at.isoformat()
            }
        )

        await self.publisher.publish_async(cloud_event)
```

## 🏗️ Real-World Example: Mario's Pizzeria

```python
# Domain Events
@dataclass
class OrderConfirmedEvent(DomainEvent):
    order_id: str
    customer_id: str
    items: List[OrderItemDto]
    total: Decimal
    delivery_address: DeliveryAddressDto

@dataclass
class CookingStartedEvent(DomainEvent):
    order_id: str
    cook_id: str
    estimated_completion: datetime

@dataclass
class OrderReadyEvent(DomainEvent):
    order_id: str
    preparation_time: timedelta

# Entity raises events
class Order(AggregateRoot):
    def confirm(self):
        self.status = OrderStatus.CONFIRMED
        self.raise_event(OrderConfirmedEvent(
            order_id=self.id,
            customer_id=self.customer_id,
            items=self.items,
            total=self.total(),
            delivery_address=self.delivery_address
        ))

# Multiple handlers react
class SendConfirmationEmailHandler(DomainEventHandler[OrderConfirmedEvent]):
    async def handle_async(self, event: OrderConfirmedEvent):
        await self.email_service.send_template(
            to=event.customer_email,
            template="order_confirmation",
            data={"order": event}
        )

class NotifyKitchenHandler(DomainEventHandler[OrderConfirmedEvent]):
    async def handle_async(self, event: OrderConfirmedEvent):
        await self.kitchen_api.create_preparation_ticket(
            order_id=event.order_id,
            items=event.items
        )

class UpdateAnalyticsHandler(DomainEventHandler[OrderConfirmedEvent]):
    async def handle_async(self, event: OrderConfirmedEvent):
        await self.analytics.record_sale(
            amount=event.total,
            customer_id=event.customer_id,
            items=event.items
        )

class DeductInventoryHandler(DomainEventHandler[OrderConfirmedEvent]):
    async def handle_async(self, event: OrderConfirmedEvent):
        for item in event.items:
            ingredients = await self.recipe_service.get_ingredients(item.pizza_name)
            await self.inventory.deduct(ingredients, item.quantity)

class PublishToExternalSystemsHandler(DomainEventHandler[OrderConfirmedEvent]):
    async def handle_async(self, event: OrderConfirmedEvent):
        cloud_event = CloudEvent(
            source="mario-pizzeria/orders",
            type="com.mariopizzeria.order.confirmed.v1",
            data=asdict(event)
        )
        await self.event_bus.publish_async(cloud_event)
```

## 🧪 Testing Event-Driven Systems

### Test Event Raising

```python
def test_order_confirm_raises_event():
    """Test that confirming order raises event."""
    order = Order(customer_id="123")
    order.add_item("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))

    # Confirm order
    order.confirm()

    # Check events
    events = order.get_uncommitted_events()

    assert len(events) == 2  # OrderCreated, OrderConfirmed
    assert isinstance(events[1], OrderConfirmedEvent)
    assert events[1].order_id == order.id
```

### Test Event Handlers

```python
async def test_email_handler():
    """Test email handler in isolation."""
    # Mock email service
    mock_email = Mock(spec=IEmailService)

    # Create handler
    handler = SendConfirmationEmailHandler(mock_email)

    # Create event
    event = OrderConfirmedEvent(
        order_id="123",
        customer_id="456",
        total=Decimal("45.99")
    )

    # Handle event
    await handler.handle_async(event)

    # Verify email was sent
    mock_email.send_confirmation.assert_called_once_with(
        customer_id="456",
        order_id="123",
        total=Decimal("45.99")
    )
```

### Test Event Flow

```python
async def test_order_confirmation_workflow():
    """Test complete event-driven workflow."""
    # Setup with real event bus
    services = ServiceCollection()
    services.add_scoped(IOrderRepository, InMemoryOrderRepository)
    services.add_scoped(IEmailService, FakeEmailService)
    services.add_scoped(IKitchenService, FakeKitchenService)
    services.add_scoped(SendConfirmationEmailHandler)
    services.add_scoped(StartCookingHandler)
    services.add_event_bus()

    provider = services.build_provider()

    # Create and confirm order
    order = Order(customer_id="123")
    order.add_item("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))
    order.confirm()

    # Save (triggers event dispatch)
    repository = provider.get_service(IOrderRepository)
    await repository.save_async(order)

    # Verify side effects
    email_service = provider.get_service(IEmailService)
    assert email_service.emails_sent == 1

    kitchen_service = provider.get_service(IKitchenService)
    assert kitchen_service.preparation_started
```

## ⚠️ Common Mistakes

### 1. Events with Commands

```python
# ❌ WRONG: Event tells what to do (command)
@dataclass
class SendEmailEvent:  # Imperative - command!
    to: str
    subject: str

# ✅ RIGHT: Event describes what happened
@dataclass
class OrderConfirmedEvent:  # Past tense - event!
    order_id: str
    customer_id: str
    # Handler decides to send email
```

### 2. Events That Are Too Generic

```python
# ❌ WRONG: Generic event
@dataclass
class OrderChangedEvent:
    order_id: str
    # What changed? Handlers don't know!

# ✅ RIGHT: Specific events
@dataclass
class OrderConfirmedEvent:
    order_id: str

@dataclass
class OrderCancelledEvent:
    order_id: str
    reason: str
```

### 3. Handler Modifies Original Aggregate

```python
# ❌ WRONG: Handler modifies order
class UpdateInventoryHandler(DomainEventHandler[OrderConfirmedEvent]):
    async def handle_async(self, event: OrderConfirmedEvent):
        order = await self.order_repo.get(event.order_id)
        order.inventory_updated = True  # NO! Modifying different aggregate
        await self.order_repo.save(order)

# ✅ RIGHT: Handler modifies its own aggregate
class UpdateInventoryHandler(DomainEventHandler[OrderConfirmedEvent]):
    async def handle_async(self, event: OrderConfirmedEvent):
        inventory = await self.inventory_repo.get(event.order_id)
        inventory.deduct_ingredients(event.items)  # Modifies Inventory aggregate
        await self.inventory_repo.save(inventory)
```

### 4. Synchronous Event Processing

```python
# ❌ WRONG: Blocking event processing
async def save_async(self, order: Order):
    await self.db.save(order)

    # Blocking - waits for all handlers
    for event in order.get_uncommitted_events():
        for handler in self.event_handlers:
            await handler.handle_async(event)  # Blocks!

# ✅ RIGHT: Async event processing
async def save_async(self, order: Order):
    await self.db.save(order)

    # Dispatch asynchronously (queue, message bus)
    await self.event_bus.publish_many_async(
        order.get_uncommitted_events()
    )
    # Handlers process in background
```

## 🚫 When NOT to Use Events

Events add complexity. Skip when:

1. **Simple Operations**: Direct call is clearer
2. **Strong Consistency Needed**: Events are eventually consistent
3. **Single Operation**: No side effects to trigger
4. **Prototypes**: Experimenting with ideas
5. **Synchronous Requirements**: Must happen immediately

For simple apps, direct service calls work fine.

## 📝 Key Takeaways

1. **Publish-Subscribe**: Publishers don't know subscribers
2. **Past Tense**: Events describe what happened
3. **Loose Coupling**: Add handlers without changing publishers
4. **Asynchronous**: Handlers run independently
5. **Resilient**: One handler failure doesn't affect others

## 🔄 Events + Other Patterns

```
Aggregate
    ↓ raises
Domain Event
    ↓ dispatched by
Unit of Work
    ↓ published to
Event Bus
    ↓ routes to
Event Handlers (multiple)
    ↓ may publish
Integration Events (CloudEvents)
```

## 🚀 Next Steps

- **Implement it**: [Tutorial Part 5](../tutorials/mario-pizzeria-05-events.md) builds event-driven system
- **Understand persistence**: [Repository Pattern](repository.md) for event dispatch
- **CloudEvents**: [CloudEvents documentation](../features/index.md) for integration

## 📚 Further Reading

- [Event-Driven Architecture (Martin Fowler)](https://martinfowler.com/articles/201701-event-driven.html)
- [CloudEvents Specification](https://cloudevents.io/)
- [Domain Events (Vernon)](https://www.dddcommunity.org/library/vernon_2010/)

---

**Previous:** [← Mediator Pattern](mediator.md) | **Next:** [Repository Pattern →](repository.md)
