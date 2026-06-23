# 🔄 Unit of Work Pattern

> **⚠️ DEPRECATED**: This pattern has been superseded by **repository-based event publishing** where the command handler serves as the transaction boundary. See [Persistence Patterns](persistence-patterns.md) for the current recommended approach.
>
> **Migration Note**: The framework no longer requires explicit UnitOfWork usage. Domain events are now automatically published by repositories when persisting aggregates, eliminating the need for manual event registration and coordination.

---

## 📚 Historical Context

_This documentation is preserved for reference and migration purposes._

_Estimated reading time: 25 minutes_

The Unit of Work pattern maintained a list of objects affected by a business transaction and coordinated writing out changes while resolving concurrency problems. In earlier versions of Neuroglia, it provided automatic domain event collection and dispatching.

## 🔄 Current Approach (Recommended)

**Instead of Unit of Work, use the repository-based pattern:**

```python
# ✅ CURRENT PATTERN: Repository handles event publishing
class CreateOrderHandler(CommandHandler[CreateOrderCommand, OperationResult[OrderDto]]):
    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, command: CreateOrderCommand):
        # 1. Create order (raises domain events internally)
        order = Order.create(command.customer_id, command.items)

        # 2. Save order - repository automatically publishes events
        await self.order_repository.save_async(order)
        # Repository does:
        # ✅ Saves order state
        # ✅ Gets uncommitted events
        # ✅ Publishes events to event bus
        # ✅ Clears events from aggregate

        return self.created(order)
```

See [Persistence Patterns](persistence-patterns.md) for detailed documentation.

---

## 💡 What & Why (Historical)

### ❌ The Problem: Manual Event Management and Inconsistent Transactions

Without Unit of Work, managing domain events and transactional consistency is manual and error-prone:

```python
# ❌ PROBLEM: Manual event management and inconsistent transactions
class CreateOrderHandler(CommandHandler[CreateOrderCommand, OperationResult[OrderDto]]):
    def __init__(self,
                 order_repository: OrderRepository,
                 event_bus: EventBus):
        self.order_repository = order_repository
        self.event_bus = event_bus

    async def handle_async(self, command: CreateOrderCommand):
        # Create order (raises domain events)
        order = Order.create(command.customer_id, command.items)

        # Save order
        await self.order_repository.save_async(order)

        # PROBLEM: Must manually extract and publish events!
        events = order.get_uncommitted_events()
        for event in events:
            await self.event_bus.publish_async(event)
        order.mark_events_as_committed()

        # PROBLEMS:
        # ❌ What if save succeeds but event publishing fails?
        # ❌ Events published even if transaction rolls back!
        # ❌ Must remember to publish events in EVERY handler!
        # ❌ Easy to forget to mark events as committed!
        # ❌ No coordination between multiple aggregates!

        return self.created(order)

# Another handler with the SAME manual code!
class ConfirmOrderHandler(CommandHandler[ConfirmOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: ConfirmOrderCommand):
        order = await self.order_repository.get_by_id_async(command.order_id)
        order.confirm()
        await self.order_repository.save_async(order)

        # Copy-pasted event management code - DUPLICATION!
        events = order.get_uncommitted_events()
        for event in events:
            await self.event_bus.publish_async(event)
        order.mark_events_as_committed()

        return self.ok(order)

# Multi-aggregate scenario is even WORSE!
class TransferInventoryHandler(CommandHandler[TransferInventoryCommand, OperationResult]):
    async def handle_async(self, command: TransferInventoryCommand):
        source = await self.warehouse_repository.get_by_id_async(command.source_id)
        target = await self.warehouse_repository.get_by_id_async(command.target_id)

        # Modify both aggregates
        source.remove_inventory(command.product_id, command.quantity)
        target.add_inventory(command.product_id, command.quantity)

        # Save both
        await self.warehouse_repository.save_async(source)
        await self.warehouse_repository.save_async(target)

        # PROBLEM: Must manually collect events from BOTH aggregates!
        all_events = []
        all_events.extend(source.get_uncommitted_events())
        all_events.extend(target.get_uncommitted_events())

        for event in all_events:
            await self.event_bus.publish_async(event)

        source.mark_events_as_committed()
        target.mark_events_as_committed()

        # This is TEDIOUS and ERROR-PRONE!
        return self.ok()
```

**Problems with Manual Event Management:**

- ❌ **Event Publishing Scattered**: Every handler must remember to publish events
- ❌ **Duplication**: Same event management code copy-pasted everywhere
- ❌ **Inconsistency Risk**: Events published even if transaction fails
- ❌ **Multi-Aggregate Complexity**: Collecting events from multiple aggregates is tedious
- ❌ **Easy to Forget**: Developers forget to publish events or mark as committed
- ❌ **No Coordination**: No central mechanism to track modified aggregates

### ✅ The Solution: Unit of Work for Automatic Event Coordination

Unit of Work automatically tracks aggregates and coordinates event dispatching:

```python
# ✅ SOLUTION: Unit of Work handles event coordination automatically
from neuroglia.data.abstractions import IUnitOfWork

class CreateOrderHandler(CommandHandler[CreateOrderCommand, OperationResult[OrderDto]]):
    def __init__(self,
                 order_repository: OrderRepository,
                 unit_of_work: IUnitOfWork):
        self.order_repository = order_repository
        self.unit_of_work = unit_of_work

    async def handle_async(self, command: CreateOrderCommand):
        # 1. Create order (raises domain events)
        order = Order.create(command.customer_id, command.items)

        # 2. Save order
        await self.order_repository.save_async(order)

        # 3. Register aggregate with Unit of Work
        self.unit_of_work.register_aggregate(order)

        # That's IT! Pipeline behavior handles the rest:
        # - Extracts events from registered aggregates
        # - Publishes events ONLY if transaction succeeds
        # - Marks events as committed automatically
        # - Clears unit of work for next request

        return self.created(order)

# Multi-aggregate scenario is SIMPLE!
class TransferInventoryHandler(CommandHandler[TransferInventoryCommand, OperationResult]):
    async def handle_async(self, command: TransferInventoryCommand):
        source = await self.warehouse_repository.get_by_id_async(command.source_id)
        target = await self.warehouse_repository.get_by_id_async(command.target_id)

        # Modify both aggregates
        source.remove_inventory(command.product_id, command.quantity)
        target.add_inventory(command.product_id, command.quantity)

        # Save both
        await self.warehouse_repository.save_async(source)
        await self.warehouse_repository.save_async(target)

        # Register both aggregates
        self.unit_of_work.register_aggregate(source)
        self.unit_of_work.register_aggregate(target)

        # Unit of Work collects events from BOTH automatically!
        return self.ok()

# Pipeline Behavior handles event dispatching automatically
class DomainEventDispatcherBehavior(PipelineBehavior):
    def __init__(self,
                 unit_of_work: IUnitOfWork,
                 event_bus: EventBus):
        self.unit_of_work = unit_of_work
        self.event_bus = event_bus

    async def handle_async(self, request, next_handler):
        # Execute handler
        result = await next_handler()

        # Only publish events if handler succeeded
        if result.is_success:
            # Get ALL events from ALL registered aggregates
            events = self.unit_of_work.get_domain_events()

            # Publish events
            for event in events:
                await self.event_bus.publish_async(event)

            # Clear unit of work for next request
            self.unit_of_work.clear()

        return result

# Register in DI container
services = ServiceCollection()
services.add_scoped(IUnitOfWork, UnitOfWork)
services.add_scoped(PipelineBehavior, DomainEventDispatcherBehavior)
```

**Benefits of Unit of Work:**

- ✅ **Automatic Event Collection**: No manual event extraction needed
- ✅ **Centralized Coordination**: Single place to track modified aggregates
- ✅ **Consistent Event Publishing**: Events only published if transaction succeeds
- ✅ **Multi-Aggregate Support**: Easily handle multiple aggregates in one transaction
- ✅ **Reduced Duplication**: Event management code in one place (pipeline)
- ✅ **Hard to Forget**: Framework handles event lifecycle automatically
- ✅ **Testability**: Unit of Work can be mocked for testing

## 🎯 Pattern Overview

The Unit of Work pattern serves as a **coordination mechanism** between your domain aggregates and the infrastructure, ensuring that:

- **Transactional Consistency**: All changes within a business operation succeed or fail together
- **Event Coordination**: Domain events are collected and dispatched automatically after successful operations
- **Aggregate Tracking**: Modified entities are tracked during the request lifecycle
- **Clean Separation**: Domain logic remains pure while infrastructure handles persistence concerns

### 🏗️ Architecture Integration

```mermaid
graph TB
    subgraph "💼 Application Layer"
        CH[Command Handler]
        QH[Query Handler]
    end

    subgraph "🔄 Unit of Work"
        UOW[IUnitOfWork]
        AGG_LIST[Registered Aggregates]
        EVENT_COLL[Domain Event Collection]
    end

    subgraph "🏛️ Domain Layer"
        ENT1[Entity/Aggregate 1]
        ENT2[Entity/Aggregate 2]
        DE[Domain Events]
    end

    subgraph "🔧 Infrastructure"
        REPO[Repositories]
        DB[(Database)]
        MW[Pipeline Middleware]
    end

    CH --> UOW
    CH --> ENT1
    CH --> ENT2
    ENT1 --> DE
    ENT2 --> DE
    UOW --> AGG_LIST
    UOW --> EVENT_COLL
    CH --> REPO
    REPO --> DB
    MW --> UOW
    MW --> DE
```

## 🔧 Core Interface

The `IUnitOfWork` interface provides a simple contract for aggregate and event management:

```python
from abc import ABC, abstractmethod
from typing import List
from neuroglia.data.abstractions import AggregateRoot, DomainEvent

class IUnitOfWork(ABC):
    """Unit of Work pattern for coordinating aggregate changes and domain events."""

    @abstractmethod
    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """Registers an aggregate for event collection and tracking."""

    @abstractmethod
    def get_domain_events(self) -> List[DomainEvent]:
        """Gets all domain events from registered aggregates."""

    @abstractmethod
    def clear(self) -> None:
        """Clears all registered aggregates and collected events."""

    @abstractmethod
    def has_changes(self) -> bool:
        """Determines if any aggregates have pending changes."""
```

## 📦 Implementation Patterns

### 1. **Basic Usage in Command Handlers**

```python
class CreateOrderHandler(CommandHandler[CreateOrderCommand, OperationResult[OrderDto]]):
    def __init__(self,
                 order_repository: OrderRepository,
                 unit_of_work: IUnitOfWork):
        self.order_repository = order_repository
        self.unit_of_work = unit_of_work

    async def handle_async(self, command: CreateOrderCommand) -> OperationResult[OrderDto]:
        # 1. Create domain entity (raises domain events)
        order = Order.create(command.customer_id, command.items)

        # 2. Persist state
        await self.order_repository.save_async(order)

        # 3. Register for automatic event dispatching
        self.unit_of_work.register_aggregate(order)

        # 4. Return result - events dispatched automatically by middleware
        return self.created(OrderDto.from_entity(order))
```

### 2. **Multiple Aggregates in Single Transaction**

```python
class ProcessPaymentHandler(CommandHandler):
    async def handle_async(self, command: ProcessPaymentCommand) -> OperationResult:
        # Multiple aggregates modified in single business transaction

        # Update order
        order = await self.order_repository.get_by_id_async(command.order_id)
        order.mark_paid(command.payment_id)  # Raises OrderPaidEvent
        await self.order_repository.save_async(order)
        self.unit_of_work.register_aggregate(order)

        # Update customer account
        customer = await self.customer_repository.get_by_id_async(order.customer_id)
        customer.record_purchase(order.total_amount)  # Raises PurchaseRecordedEvent
        await self.customer_repository.save_async(customer)
        self.unit_of_work.register_aggregate(customer)

        # Update inventory
        for item in order.items:
            inventory = await self.inventory_repository.get_by_product_id(item.product_id)
            inventory.reduce_stock(item.quantity)  # Raises StockReducedEvent
            await self.inventory_repository.save_async(inventory)
            self.unit_of_work.register_aggregate(inventory)

        # All events from all aggregates dispatched together
        return self.ok({"order_id": order.id, "payment_processed": True})
```

## 🎭 Persistence Pattern Flexibility

The Unit of Work pattern supports **multiple persistence approaches** with the same infrastructure:

### **Pattern 1: Simple Entity with State Persistence**

_→ Complexity Level: ⭐⭐☆☆☆_

**Best for**: CRUD operations, simple domains, traditional persistence

```python
class Product(Entity):  # ← Just Entity, no AggregateRoot needed!
    """Simple entity with domain events for state-based persistence."""

    def __init__(self, name: str, price: float):
        super().__init__()
        self._id = str(uuid.uuid4())
        self.name = name
        self.price = price

        # Raise domain event
        self._raise_domain_event(ProductCreatedEvent(self.id, name, price))

    def update_price(self, new_price: float):
        """Business logic with domain event."""
        if new_price != self.price:
            old_price = self.price
            self.price = new_price
            self._raise_domain_event(PriceChangedEvent(self.id, old_price, new_price))

    # Minimal event infrastructure
    def _raise_domain_event(self, event: DomainEvent):
        if not hasattr(self, '_pending_events'):
            self._pending_events = []
        self._pending_events.append(event)

    @property
    def domain_events(self) -> List[DomainEvent]:
        return getattr(self, '_pending_events', []).copy()

    def clear_pending_events(self):
        if hasattr(self, '_pending_events'):
            self._pending_events.clear()

# Usage - Same UnitOfWork, simpler entity
class UpdateProductPriceHandler(CommandHandler):
    async def handle_async(self, command: UpdateProductPriceCommand):
        product = await self.product_repository.get_by_id_async(command.product_id)
        product.update_price(command.new_price)  # Raises PriceChangedEvent

        await self.product_repository.save_async(product)  # Save state to DB
        self.unit_of_work.register_aggregate(product)      # Auto-dispatch events

        return self.ok(ProductDto.from_entity(product))
```

**Characteristics**:

- ✅ Direct state persistence to database
- ✅ Simple entity inheritance (`Entity`)
- ✅ Automatic domain event dispatching
- ✅ No event store required
- ✅ Traditional database schemas
- ✅ Easy to understand and implement

### **Pattern 2: Aggregate Root with Event Sourcing**

_→ Complexity Level: ⭐⭐⭐⭐⭐_

**Best for**: Complex domains, audit requirements, temporal queries

```python
class OrderAggregate(AggregateRoot[OrderState, UUID]):
    """Complex aggregate with full event sourcing."""

    def place_order(self, customer_id: str, items: List[OrderItem]):
        """Rich business logic with event sourcing."""
        # Business rules validation
        if not items:
            raise DomainException("Order must have at least one item")

        total = sum(item.price * item.quantity for item in items)
        if total <= 0:
            raise DomainException("Order total must be positive")

        # Apply event to change state
        event = OrderPlacedEvent(
            order_id=self.id,
            customer_id=customer_id,
            items=items,
            total_amount=total,
            placed_at=datetime.utcnow()
        )

        # Event sourcing: event changes state + is stored for replay
        self.state.on(event)  # Apply to current state
        self.register_event(event)  # Register for persistence

    def add_item(self, product_id: str, quantity: int, price: Decimal):
        """Add item with business rule validation."""
        if self.state.status != OrderStatus.DRAFT:
            raise DomainException("Cannot modify confirmed order")

        event = ItemAddedEvent(self.id, product_id, quantity, price)
        self.state.on(event)
        self.register_event(event)

# Usage - Same UnitOfWork, event-sourced aggregate
class PlaceOrderHandler(CommandHandler):
    async def handle_async(self, command: PlaceOrderCommand):
        order = OrderAggregate()
        order.place_order(command.customer_id, command.items)  # Raises OrderPlacedEvent

        await self.order_repository.save_async(order)  # Save events to event store
        self.unit_of_work.register_aggregate(order)    # Auto-dispatch events

        return self.created(OrderDto.from_aggregate(order))
```

**Characteristics**:

- ✅ Complete event sourcing with event store
- ✅ Full aggregate pattern with `AggregateRoot[TState, TKey]`
- ✅ Rich business logic and invariant enforcement
- ✅ Temporal queries and audit trails
- ✅ Event replay and projection capabilities
- ✅ Complex consistency boundaries

### **Pattern 3: Hybrid Approach**

_→ Complexity Level: ⭐⭐⭐☆☆_

**Best for**: Mixed requirements, gradual migration, pragmatic solutions

```python
# Mix both patterns in the same application
class OrderProcessingHandler(CommandHandler):
    async def handle_async(self, command: ProcessOrderCommand):
        # Event-sourced aggregate for complex business logic
        order = await self.order_repository.get_by_id_async(command.order_id)
        order.process_payment(command.payment_info)  # Complex event-sourced logic
        await self.order_repository.save_async(order)
        self.unit_of_work.register_aggregate(order)

        # Simple entity for straightforward updates
        inventory = await self.inventory_repository.get_by_product_id(command.product_id)
        inventory.reduce_stock(command.quantity)  # Simple state-based persistence
        await self.inventory_repository.save_async(inventory)
        self.unit_of_work.register_aggregate(inventory)

        # Both patterns work together seamlessly
        return self.ok()
```

## 🔧 Infrastructure Integration

### **Pipeline Integration**

The Unit of Work integrates with the mediator's notification pipeline through the new
`DomainEventCloudEventBehavior`, which supersedes the legacy `DomainEventDispatchingMiddleware`:

```python
from neuroglia.eventing.cloud_events.infrastructure import CloudEventPublisher
from neuroglia.mediation.behaviors.domain_event_cloudevent_behavior import DomainEventCloudEventBehavior

# Automatic setup with configuration methods
builder = WebApplicationBuilder()
Mediator.configure(builder, ["application.commands", "application.queries"])
UnitOfWork.configure(builder)
DomainEventCloudEventBehavior.configure(builder)  # Emits decorated domain events as CloudEvents
CloudEventPublisher.configure(builder)            # Optional: forward CloudEvents to external sinks

# Pipeline execution flow:
# 1. Command received
# 2. [Optional] Transaction begins
# 3. Command handler executes
# 4. Handler registers aggregates with UnitOfWork
# 5. Command completes successfully
# 6. Mediator publishes domain events
# 7. DomainEventCloudEventBehavior converts them to CloudEvents and pushes them to the bus
# 8. CloudEventPublisher (if configured) fans out to external transports
# 9. [Optional] Transaction commits
```

> ⚠️ `DomainEventDispatchingMiddleware` is deprecated and now acts as a no-op. Remove it from the
> pipeline to avoid duplicate registrations and rely on `DomainEventCloudEventBehavior` for CloudEvent
> emission.

### **CloudEvent Emission Requirements**

- Decorate domain events with `@cloudevent("my.event.type")` to opt-in to CloudEvent emission.
- `DomainEventCloudEventBehavior` listens to the mediator's notification pipeline and serializes the
  event payload (dataclass, Pydantic, or plain object) into a CloudEvent before pushing it to the
  in-memory `CloudEventBus`.
- `CloudEventPublishingOptions` lets you tune the CloudEvent `source`, optional `type_prefix`, and
  retry behaviour used by downstream publishers.
- Register `CloudEventPublisher` when you want the framework to fan out the generated CloudEvents to
  HTTP, message brokers, or observability pipelines.

### **Event Collection Mechanism**

The UnitOfWork uses **duck typing** to collect events from any object, supporting both patterns:

```python
def get_domain_events(self) -> List[DomainEvent]:
    """Flexible event collection supporting multiple patterns."""
    events = []

    for aggregate in self._aggregates:
        # Event-sourced aggregates (AggregateRoot)
        if hasattr(aggregate, 'get_uncommitted_events'):
            events.extend(aggregate.get_uncommitted_events())

        # State-based entities (Entity + domain_events)
        elif hasattr(aggregate, 'domain_events'):
            events.extend(aggregate.domain_events)

        # Fallback to internal events
        elif hasattr(aggregate, '_pending_events'):
            events.extend(aggregate._pending_events)

    return events
```

## 📋 Complexity Comparison

| **Aspect**                | **Entity + State Persistence** | **AggregateRoot + Event Sourcing** |
| ------------------------- | ------------------------------ | ---------------------------------- |
| **Learning Curve**        | ⭐⭐☆☆☆ Simple                 | ⭐⭐⭐⭐⭐ Complex                 |
| **Setup Complexity**      | ⭐⭐☆☆☆ Minimal                | ⭐⭐⭐⭐☆ Significant              |
| **Database Requirements** | Any SQL/NoSQL database         | Event store + projections          |
| **Query Capabilities**    | Direct database queries        | Event replay + projections         |
| **Business Logic**        | Method-based                   | Event-driven state machines        |
| **Audit & History**       | Manual implementation          | Built-in temporal queries          |
| **Performance**           | Direct database access         | Event replay overhead              |
| **Scalability**           | Traditional scaling            | Event-driven scaling               |

## 🎯 When to Use Each Pattern

### **Choose Entity + State Persistence When**

- ✅ Building CRUD-heavy applications
- ✅ Team is new to DDD/event sourcing
- ✅ Simple business rules and workflows
- ✅ Traditional database infrastructure
- ✅ Performance is critical
- ✅ Quick prototyping and development

### **Choose AggregateRoot + Event Sourcing When**

- ✅ Complex business domains with rich logic
- ✅ Audit trails and compliance requirements
- ✅ Temporal queries and historical analysis
- ✅ Event-driven integrations
- ✅ High consistency requirements
- ✅ Long-term maintainability over complexity

### **Choose Hybrid Approach When**

- ✅ Mixed complexity across domain areas
- ✅ Migrating from traditional to event-sourced systems
- ✅ Different persistence requirements per bounded context
- ✅ Pragmatic balance between complexity and capability

## 🔗 Integration with Other Patterns

### **CQRS Integration**

The Unit of Work pattern works seamlessly with [CQRS](../features/simple-cqrs.md):

```python
# Commands use UnitOfWork for writes
class CreateProductHandler(CommandHandler):
    async def handle_async(self, command):
        product = Product(command.name, command.price)
        await self.repository.save_async(product)
        self.unit_of_work.register_aggregate(product)  # Events dispatched
        return self.created(product)

# Queries bypass UnitOfWork for reads
class GetProductHandler(QueryHandler):
    async def handle_async(self, query):
        return await self.repository.get_by_id_async(query.product_id)
        # No UnitOfWork needed for read operations
```

### **Pipeline Behaviors Integration**

Unit of Work integrates with [Pipeline Behaviors](pipeline-behaviors.md):

```python
# Transaction behavior + Domain event emission
services.add_scoped(PipelineBehavior, TransactionBehavior)        # 1st: Manages DB transactions
services.add_scoped(PipelineBehavior, DomainEventCloudEventBehavior)  # 2nd: Emits domain events as CloudEvents
services.add_scoped(PipelineBehavior, LoggingBehavior)            # 3rd: Logs execution

# Execution order ensures events only dispatch after successful transaction commit
```

### **Repository Pattern Integration**

Unit of Work coordinates with [Repository Pattern](repository.md):

```python
# Repository handles persistence, UnitOfWork handles events
class OrderHandler(CommandHandler):
    async def handle_async(self, command):
        order = Order.create(command.data)     # Domain logic
        await self.repository.save_async(order)  # Repository persistence
        self.unit_of_work.register_aggregate(order)  # UnitOfWork event coordination
        return self.created(order)
```

## 🧪 Testing Strategies

### **Unit Testing Domain Events**

```python
def test_product_creation_raises_event():
    """Test domain events are raised correctly."""
    product = Product("Laptop", 999.99)

    events = product.domain_events
    assert len(events) == 1
    assert isinstance(events[0], ProductCreatedEvent)
    assert events[0].name == "Laptop"
    assert events[0].price == 999.99

def test_price_update_raises_event():
    """Test business operations raise appropriate events."""
    product = Product("Laptop", 999.99)
    product.clear_pending_events()  # Clear creation event

    product.update_price(899.99)

    events = product.domain_events
    assert len(events) == 1
    assert isinstance(events[0], PriceChangedEvent)
    assert events[0].old_price == 999.99
    assert events[0].new_price == 899.99
```

### **Integration Testing with UnitOfWork**

```python
@pytest.mark.asyncio
async def test_command_handler_registers_aggregates():
    """Test complete command handler workflow with UnitOfWork."""
    # Setup
    unit_of_work = UnitOfWork()
    repository = InMemoryProductRepository()
    handler = CreateProductHandler(repository, unit_of_work)

    # Execute
    command = CreateProductCommand("Laptop", 999.99)
    result = await handler.handle_async(command)

    # Verify
    assert result.is_success
    assert unit_of_work.has_changes()

    events = unit_of_work.get_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], ProductCreatedEvent)

from decimal import Decimal

import pytest

from neuroglia.core import OperationResult
from neuroglia.data.abstractions import DomainEvent
from neuroglia.data.unit_of_work import UnitOfWork
from neuroglia.eventing.cloud_events.cloud_event import CloudEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mediation.behaviors.domain_event_cloudevent_behavior import DomainEventCloudEventBehavior


@cloudevent("inventory.product.created.v1")
class ProductCreatedEvent(DomainEvent[str]):
    def __init__(self, aggregate_id: str, name: str, price: Decimal):
        super().__init__(aggregate_id)
        self.name = name
        self.price = price


@pytest.mark.asyncio
async def test_domain_events_emit_cloudevents():
    """Test automatic CloudEvent emission for decorated domain events."""
    unit_of_work = UnitOfWork()
    product = Product("Laptop", 999.99)
    unit_of_work.register_aggregate(product)

    # Simulate mediator publishing collected domain events
    bus = CloudEventBus()
    captured: list[CloudEvent] = []
    bus.output_stream.subscribe(captured.append)

    behavior = DomainEventCloudEventBehavior(
        bus,
        CloudEventPublishingOptions(source="/tests/integration"),
    )

    async def next_handler() -> OperationResult:
        return OperationResult("OK", 200)

    # In production code iterate over unit_of_work.get_domain_events().
    # The fallback below keeps the example self-contained.
    events = unit_of_work.get_domain_events() or [
        ProductCreatedEvent(product.id, product.name, Decimal("999.99"))
    ]

    for event in events:
        await behavior.handle_async(event, next_handler)

    assert captured
    cloud_event = captured[0]
    assert cloud_event.subject == product.id
    assert cloud_event.type == "inventory.product.created.v1"
```

## 🚨 Best Practices

### **Entity Design Patterns**

```python
# ✅ Good: Business-focused methods with events
class Order(Entity):
    def place_order(self, items: List[OrderItem]):
        self._validate_order_items(items)
        self.status = OrderStatus.PLACED
        self._raise_event(OrderPlacedEvent(self.id, items))

    def add_item(self, item: OrderItem):
        if self.status != OrderStatus.DRAFT:
            raise DomainException("Cannot modify placed order")

        self.items.append(item)
        self._raise_event(ItemAddedEvent(self.id, item))

# ❌ Avoid: Property setters that bypass business rules
class Order(Entity):
    @property
    def status(self, value):
        self._status = value  # No validation, no events!
```

### **Event Design Patterns**

```python
# ✅ Good: Rich, immutable events with business context
@dataclass(frozen=True)
class OrderPlacedEvent(DomainEvent):
    order_id: str
    customer_id: str
    items: List[OrderItem]
    total_amount: Decimal
    placed_at: datetime

# ❌ Avoid: Anemic events without context
@dataclass
class OrderEvent(DomainEvent):
    order_id: str  # Too generic, lacks business meaning
```

### **UnitOfWork Usage Patterns**

```python
# ✅ Good: Register aggregates after business operations
async def handle_async(self, command):
    order = Order.create(command.items)        # Business logic first
    await self.repository.save_async(order)    # Persistence second
    self.unit_of_work.register_aggregate(order)  # Event coordination last
    return self.created(order)

# ❌ Avoid: Registering before business operations complete
async def handle_async(self, command):
    order = Order()
    self.unit_of_work.register_aggregate(order)  # Too early!
    order.add_items(command.items)              # Business logic after registration
    return self.created(order)
```

## ⚠️ Common Mistakes

### 1. **Forgetting to Register Aggregates**

```python
# ❌ WRONG: Forget to register aggregate (events never dispatched!)
async def handle_async(self, command: CreateOrderCommand):
    order = Order.create(command.customer_id, command.items)
    await self.repository.save_async(order)
    # Forgot to register! Events will NOT be published!
    return self.created(order)

# ✅ CORRECT: Always register aggregates that raise events
async def handle_async(self, command: CreateOrderCommand):
    order = Order.create(command.customer_id, command.items)
    await self.repository.save_async(order)
    self.unit_of_work.register_aggregate(order)  # Events will be published!
    return self.created(order)
```

### 2. **Registering Aggregates Before Operations Complete**

```python
# ❌ WRONG: Register too early (captures partial state)
async def handle_async(self, command: CreateOrderCommand):
    order = Order(command.customer_id)
    self.unit_of_work.register_aggregate(order)  # TOO EARLY!

    # These events won't be captured by unit of work!
    order.add_items(command.items)
    order.apply_discount(command.discount_code)

    await self.repository.save_async(order)
    return self.created(order)

# ✅ CORRECT: Register after all business operations
async def handle_async(self, command: CreateOrderCommand):
    order = Order(command.customer_id)
    order.add_items(command.items)
    order.apply_discount(command.discount_code)

    await self.repository.save_async(order)
    self.unit_of_work.register_aggregate(order)  # Captures ALL events!
    return self.created(order)
```

### 3. **Not Clearing Unit of Work Between Requests**

```python
# ❌ WRONG: Reusing same Unit of Work without clearing
class MyPipelineBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        result = await next_handler()

        if result.is_success:
            events = self.unit_of_work.get_domain_events()
            for event in events:
                await self.event_bus.publish_async(event)
            # FORGOT to clear! Events accumulate across requests!

        return result

# ✅ CORRECT: Always clear after processing
class MyPipelineBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        try:
            result = await next_handler()

            if result.is_success:
                events = self.unit_of_work.get_domain_events()
                for event in events:
                    await self.event_bus.publish_async(event)

            return result
        finally:
            self.unit_of_work.clear()  # Always clear!
```

### 4. **Using Singleton Lifetime for Unit of Work**

```python
# ❌ WRONG: Singleton lifetime (shared across all requests!)
services.add_singleton(IUnitOfWork, UnitOfWork)
# All requests share the same Unit of Work - DISASTER!

# ✅ CORRECT: Scoped lifetime (one per request)
services.add_scoped(IUnitOfWork, UnitOfWork)
# Each request gets its own Unit of Work instance
```

### 5. **Publishing Events Before Transaction Commits**

```python
# ❌ WRONG: Publishing events before save completes
async def handle_async(self, command: CreateOrderCommand):
    order = Order.create(command.customer_id, command.items)

    # Publishing BEFORE save!
    events = order.get_uncommitted_events()
    for event in events:
        await self.event_bus.publish_async(event)

    # What if save fails? Events already published!
    await self.repository.save_async(order)
    return self.created(order)

# ✅ CORRECT: Let pipeline behavior publish AFTER save
async def handle_async(self, command: CreateOrderCommand):
    order = Order.create(command.customer_id, command.items)
    await self.repository.save_async(order)
    self.unit_of_work.register_aggregate(order)
    # Pipeline publishes events ONLY if handler succeeds
    return self.created(order)
```

### 6. **Not Handling Event Publishing Failures**

```python
# ❌ WRONG: No error handling for event publishing
class EventDispatcherBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        result = await next_handler()

        events = self.unit_of_work.get_domain_events()
        for event in events:
            await self.event_bus.publish_async(event)  # What if this fails?

        return result

# ✅ CORRECT: Handle publishing failures gracefully
class EventDispatcherBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        result = await next_handler()

        if not result.is_success:
            return result

        events = self.unit_of_work.get_domain_events()

        try:
            for event in events:
                await self.event_bus.publish_async(event)
        except Exception as ex:
            self.logger.error(f"Failed to publish events: {ex}")
            # Consider: retry, dead letter queue, or compensating transaction
            # For now, log and continue (events are stored with aggregate)
        finally:
            self.unit_of_work.clear()

        return result
```

## 🚫 When NOT to Use

### 1. **Simple CRUD Operations Without Domain Events**

```python
# Unit of Work is overkill for simple data updates
class UpdateCustomerEmailHandler:
    async def handle_async(self, command: UpdateEmailCommand):
        # Simple update, no domain events needed
        await self.db.customers.update_one(
            {"id": command.customer_id},
            {"$set": {"email": command.new_email}}
        )
        # No need for Unit of Work here
```

### 2. **Read-Only Queries**

```python
# Unit of Work is for WRITE operations, not queries
class GetOrderByIdHandler:
    async def handle_async(self, query: GetOrderByIdQuery):
        # Just reading data, no events to coordinate
        return await self.repository.get_by_id_async(query.order_id)
        # No Unit of Work needed
```

### 3. **Stateless Services Without Aggregates**

```python
# Services that don't work with domain aggregates
class PriceCalculationService:
    def calculate_total(self, items: List[OrderItem]) -> Decimal:
        # Pure calculation, no state changes, no events
        return sum(item.price * item.quantity for item in items)
        # No Unit of Work needed
```

### 4. **External API Integration**

```python
# Unit of Work is for domain aggregates, not external APIs
class SendEmailHandler:
    async def handle_async(self, command: SendEmailCommand):
        # Calling external API, not modifying aggregates
        await self.email_api.send_async(
            to=command.recipient,
            subject=command.subject,
            body=command.body
        )
        # No aggregates, no Unit of Work needed
```

### 5. **Background Jobs Without Domain Logic**

```python
# Simple background tasks without domain events
class CleanupOldLogsJob:
    async def execute_async(self):
        # Deleting old data, not raising domain events
        cutoff = datetime.now() - timedelta(days=90)
        await self.db.logs.delete_many({"created_at": {"$lt": cutoff}})
        # No domain events, no Unit of Work needed
```

## 📝 Key Takeaways

- **Unit of Work coordinates aggregate changes** and event dispatching
- **Automatically collects domain events** from registered aggregates
- **Ensures transactional consistency** by publishing events only after save succeeds
- **Reduces boilerplate** by eliminating manual event management in every handler
- **Supports multi-aggregate transactions** with centralized coordination
- **Always register aggregates** after business operations complete
- **Use scoped lifetime** (one Unit of Work per request)
- **Clear Unit of Work** after each request to prevent event accumulation
- **Pipeline behaviors** typically handle event dispatching automatically
- **Framework provides IUnitOfWork interface** and implementation

## 📚 Related Documentation

- **[🎯 Simple CQRS](../features/simple-cqrs.md)** - Command and Query handling patterns
- **[🔧 Pipeline Behaviors](pipeline-behaviors.md)** - Cross-cutting concern patterns
- **[🏛️ State-Based Persistence](../state-based-persistence.md)** - Detailed state persistence guide
- **[🏛️ Domain Driven Design](domain-driven-design.md)** - Comprehensive DDD patterns
- **[📦 Repository Pattern](repository.md)** - Data access abstraction patterns
- **[📡 Event-Driven Architecture](event-driven.md)** - Event handling and integration patterns

The Unit of Work pattern provides the coordination layer that makes domain-driven design practical and maintainable, supporting both simple and complex persistence scenarios within the same architectural framework.
