# 🔄 Domain Events Flow - Complete Explanation

## 📋 Your Questions Answered

### Q1: "What are Domain Events used for in this case?"

**Yes, exactly!** Domain Events are used for **side effects that must happen AFTER the aggregate is persisted**.

Domain events represent **"something important happened in the domain"** and trigger reactions/side effects **without coupling** the aggregate to those reactions.

### Q2: "Does the aggregate need to register itself in a handler?"

**Yes**, but it's explicit and intentional. The handler must call:

```python
self.unit_of_work.register_aggregate(order)
```

This is NOT automatic - you must explicitly register each aggregate you want to collect events from.

### Q3: "How does the middleware ensure event dispatching?"

The `DomainEventDispatchingMiddleware` wraps **every command execution** and:

1. Lets the command handler execute
2. **If successful**, collects events from UnitOfWork
3. Dispatches events through the mediator
4. Clears the UnitOfWork

---

## 🎯 Complete Flow Walkthrough

Let me trace through a real example from Mario Pizzeria: **Creating an Order**

### Step 1: HTTP Request Arrives

```
POST /api/orders
{
  "customer_name": "John Doe",
  "customer_phone": "+1234567890",
  "pizzas": [{"name": "Margherita", "size": "large", "toppings": ["basil"]}]
}
```

### Step 2: Controller Dispatches Command

```python
# api/controllers/order_controller.py
class OrdersController(ControllerBase):
    @post("/", response_model=OrderDto, status_code=201)
    async def create_order(self, create_order_dto: CreateOrderDto) -> OrderDto:
        # Map DTO to command
        command = self.mapper.map(create_order_dto, PlaceOrderCommand)

        # Send command to mediator
        result = await self.mediator.execute_async(command)  # ← Entry point

        return self.process(result)
```

### Step 3: Mediator Pipeline Begins

The command enters the **mediation pipeline**, which looks like this:

```
Request
  ↓
[DomainEventDispatchingMiddleware] ← Wraps everything
  ↓
[ValidationMiddleware] ← Could have validation
  ↓
[LoggingMiddleware] ← Could have logging
  ↓
[CommandHandler] ← Your actual handler
```

**Key Point**: `DomainEventDispatchingMiddleware` is registered in `main.py`:

```python
# main.py - Middleware registration
services.add_scoped(
    PipelineBehavior,
    implementation_factory=lambda sp: DomainEventDispatchingMiddleware(
        sp.get_required_service(IUnitOfWork),
        sp.get_required_service(Mediator)
    ),
    lifetime=ServiceLifetime.SCOPED
)
```

### Step 4: DomainEventDispatchingMiddleware Intercepts

```python
# DomainEventDispatchingMiddleware.handle_async()
async def handle_async(self, request: Command, next_handler: Callable) -> OperationResult:
    command_name = type(request).__name__  # "PlaceOrderCommand"

    try:
        # 1. Execute the command through the rest of the pipeline
        result = await next_handler()  # ← Calls your handler

        # 2. Only dispatch events if successful
        if result.is_success:
            await self._dispatch_domain_events(command_name)
        else:
            log.debug(f"Command {command_name} failed, skipping event dispatch")

        return result

    finally:
        # 3. Always clear UnitOfWork (prevents event leakage between requests)
        if self.unit_of_work.has_changes():
            self.unit_of_work.clear()
```

### Step 5: Command Handler Executes

```python
# application/commands/place_order_command.py
class PlaceOrderCommandHandler(CommandHandler):
    def __init__(self,
                 order_repository: IOrderRepository,
                 customer_repository: ICustomerRepository,
                 mapper: Mapper,
                 unit_of_work: IUnitOfWork):  # ← UnitOfWork injected
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper
        self.unit_of_work = unit_of_work

    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
        try:
            # 1. Create customer
            customer = Customer(
                name=command.customer_name,
                phone=command.customer_phone,
                email=command.customer_email
            )
            # Customer raises: CustomerRegisteredEvent ← Event #1

            # 2. Create order
            order = Order(customer_id=customer.id)
            # Order raises: OrderCreatedEvent ← Event #2

            # 3. Add pizzas
            for pizza_dto in command.pizzas:
                pizza = Pizza(name=pizza_dto.name, size=pizza_dto.size, ...)
                order.add_pizza(pizza)  # Raises: PizzaAddedToOrderEvent ← Event #3, #4...

            # 4. Confirm order
            order.confirm_order()  # Raises: OrderConfirmedEvent ← Event #N

            # 5. Persist to database/files
            await self.customer_repository.add_async(customer)  # ← PERSIST STATE
            await self.order_repository.add_async(order)        # ← PERSIST STATE

            # 6. CRITICAL: Register aggregates for event collection
            self.unit_of_work.register_aggregate(order)    # ← Explicit registration
            self.unit_of_work.register_aggregate(customer) # ← Explicit registration

            # 7. Return success
            order_dto = OrderDto(...)
            return self.created(order_dto)

        except Exception as e:
            return self.bad_request(f"Failed: {str(e)}")
```

**Critical Point**: At step 6, the aggregates are **already persisted**. We register them so the middleware can collect their events.

### Step 6: Repository Persists STATE Only

When you do `await self.order_repository.add_async(order)`:

```python
# integration/repositories/file_order_repository.py
class FileOrderRepository(FileSystemRepository[Order, str]):

    async def add_async(self, order: Order) -> None:
        # With proper state separation:
        state_dict = {
            'id': order.state.id,                       # ← From state
            'customer_id': order.state.customer_id,     # ← From state
            'pizzas': order.state.pizzas,               # ← From state
            'status': order.state.status.value,         # ← From state
            'order_time': order.state.order_time,       # ← From state
            'state_version': order.state.state_version, # ← From state
            # ... all other STATE fields
        }

        # Serialize ONLY the state, not methods
        await self._save_to_file(state_dict)

        # Note: Events are NOT persisted here
        # Events are in order._pending_events, not in order.state
```

**Key Insight**:

- ✅ `order.state` gets persisted to MongoDB/files
- ❌ `order._pending_events` does NOT get persisted
- ✅ Events are collected by UnitOfWork and dispatched, then cleared

### Step 7: Handler Returns to Middleware

```python
# Back in DomainEventDispatchingMiddleware
async def handle_async(self, request: Command, next_handler: Callable) -> OperationResult:
    # Handler has completed and returned result
    result = await next_handler()  # ← Just returned from PlaceOrderCommandHandler

    # Check if successful
    if result.is_success:  # ← True! Order was created successfully
        # Dispatch domain events
        await self._dispatch_domain_events(command_name)  # ← Go to Step 8

    return result
```

### Step 8: Middleware Collects Events from UnitOfWork

```python
# DomainEventDispatchingMiddleware._dispatch_domain_events()
async def _dispatch_domain_events(self, command_name: str) -> None:
    # 1. Get all events from registered aggregates
    events = self.unit_of_work.get_domain_events()  # ← Collect events

    # Returns list:
    # [
    #   CustomerRegisteredEvent(aggregate_id='cust_123'),
    #   OrderCreatedEvent(aggregate_id='order_456'),
    #   PizzaAddedToOrderEvent(aggregate_id='order_456', pizza_id='pizza_789'),
    #   OrderConfirmedEvent(aggregate_id='order_456', total_amount=29.99)
    # ]

    if not events:
        log.debug(f"No domain events to dispatch for command {command_name}")
        return

    log.info(f"Dispatching {len(events)} domain events for command {command_name}")

    # 2. Dispatch each event through mediator
    for event in events:
        event_name = type(event).__name__
        log.debug(f"Dispatching domain event {event_name}")

        await self.mediator.publish_async(event)  # ← Go to Step 9
```

### Step 9: UnitOfWork Collects Events (How?)

```python
# src/neuroglia/data/unit_of_work.py
class UnitOfWork(IUnitOfWork):
    def __init__(self):
        self._aggregates: set[AggregateRoot] = set()  # ← Registered aggregates

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """Called by handler to register aggregates"""
        if aggregate is not None:
            self._aggregates.add(aggregate)  # ← Add to tracking

    def get_domain_events(self) -> list[DomainEvent]:
        """Called by middleware to collect events"""
        events: list[DomainEvent] = []

        for aggregate in self._aggregates:
            # Use duck typing to collect events from different aggregate types
            if hasattr(aggregate, "get_uncommitted_events"):
                aggregate_events = aggregate.get_uncommitted_events()
            elif hasattr(aggregate, "domain_events"):
                aggregate_events = aggregate.domain_events  # ← Used by Mario Pizzeria
            elif hasattr(aggregate, "_pending_events"):
                aggregate_events = aggregate._pending_events.copy()
            else:
                continue

            if aggregate_events:
                events.extend(aggregate_events)  # ← Collect all events

        return events  # ← Return to middleware
```

### Step 10: Mediator Publishes Events to Handlers

```python
# For each event, mediator finds registered handlers
await self.mediator.publish_async(OrderConfirmedEvent(...))

# Mediator looks up handlers:
# - OrderConfirmedEventHandler ← Found!
# - Any other handlers subscribed to OrderConfirmedEvent

# Calls each handler:
await handler.handle_async(event)
```

### Step 11: Event Handlers Execute (Side Effects)

```python
# application/event_handlers.py
class OrderConfirmedEventHandler(DomainEventHandler[OrderConfirmedEvent]):

    async def handle_async(self, event: OrderConfirmedEvent) -> Any:
        logger.info(f"🍕 Order {event.aggregate_id} confirmed! "
                   f"Total: ${event.total_amount}, Pizzas: {event.pizza_count}")

        # SIDE EFFECTS - things that happen AFTER persistence:

        # 1. Send SMS notification to customer
        await self.sms_service.send_confirmation(
            phone=customer.phone,
            order_id=event.aggregate_id,
            estimated_time="30 minutes"
        )

        # 2. Send email receipt
        await self.email_service.send_receipt(
            email=customer.email,
            order_details=...
        )

        # 3. Update kitchen display system
        await self.kitchen_display.add_order(
            order_id=event.aggregate_id,
            pizzas=event.pizza_count,
            priority="normal"
        )

        # 4. Update analytics database (read model)
        await self.analytics_repo.record_order_confirmed(
            order_id=event.aggregate_id,
            total=event.total_amount,
            timestamp=event.confirmed_time
        )

        # 5. Publish to message bus for other microservices
        await self.event_bus.publish(
            topic="orders.confirmed",
            payload=event
        )

        return None
```

**Important**: If event handler fails, it's logged but doesn't affect the command result. The order is already saved!

### Step 12: Middleware Clears UnitOfWork

```python
# Back in DomainEventDispatchingMiddleware
finally:
    if self.unit_of_work.has_changes():
        self.unit_of_work.clear()  # ← Clears aggregates and events
```

This prevents events from leaking to the next request.

### Step 13: Response Returns to Client

```json
HTTP 201 Created
{
  "id": "order_456",
  "customer_name": "John Doe",
  "customer_phone": "+1234567890",
  "status": "confirmed",
  "total_amount": 29.99,
  "estimated_ready_time": "2025-10-07T12:30:00Z"
}
```

---

## 🎯 Key Architectural Points

### 1. **Persistence Happens BEFORE Event Dispatching**

```
Order Flow:
1. Create aggregates (events raised)         ← Events in memory
2. Save aggregates to DB/files               ← STATE persisted
3. Register with UnitOfWork                  ← Events still in memory
4. Return success from handler               ← DB write committed
5. Middleware collects events                ← Events collected
6. Middleware dispatches events              ← Side effects execute
7. Clear UnitOfWork                          ← Events cleared from memory
```

**Why this order?**

- ✅ State is safely persisted before side effects
- ✅ If side effects fail, state is still saved
- ✅ Side effects can be retried independently
- ✅ Eventual consistency pattern

### 2. **State vs Events: What Gets Persisted?**

| Component               | Persisted?  | Where?        | Purpose                           |
| ----------------------- | ----------- | ------------- | --------------------------------- |
| `order.state.*`         | ✅ Yes      | MongoDB/Files | Current aggregate state           |
| `order._pending_events` | ❌ No       | Memory only   | Trigger side effects              |
| Event to EventStore     | ⚠️ Optional | Event Store   | Full audit trail (Event Sourcing) |

**Current Mario Pizzeria**:

- ✅ Persists state (order data)
- ✅ Dispatches events (side effects)
- ❌ Does NOT persist events (not using Event Sourcing)

**Full Event Sourcing** (optional future):

- ✅ Persists events to EventStore
- ✅ Dispatches events (side effects)
- ⚠️ State can be rebuilt from events

### 3. **Why Explicit Registration?**

```python
# Handler must explicitly register
self.unit_of_work.register_aggregate(order)
self.unit_of_work.register_aggregate(customer)
```

**Why not automatic?**

1. **Control**: Handler decides which aggregates' events to dispatch
2. **Performance**: Don't collect events from aggregates you don't care about
3. **Testability**: Easy to test with/without event dispatching
4. **Clarity**: Explicit is better than implicit (Python Zen)

**Example**: If you're just reading an aggregate, don't register it:

```python
# Query handler - no events needed
async def handle_async(self, query: GetOrderQuery) -> OrderDto:
    order = await self.order_repository.get_by_id_async(query.order_id)
    # No registration - no events dispatched
    return self.mapper.map(order, OrderDto)
```

### 4. **What Happens if Handler Fails?**

```python
async def handle_async(self, command: PlaceOrderCommand) -> OperationResult:
    order = Order(customer_id=command.customer_id)
    order.confirm_order()  # Raises OrderConfirmedEvent

    await self.order_repository.add_async(order)  # ← Throws exception!

    self.unit_of_work.register_aggregate(order)  # ← Never reached
    return self.created(...)
```

**Result**:

- ❌ Order NOT persisted (exception thrown)
- ❌ Events NOT dispatched (never registered)
- ❌ Side effects NOT triggered (no events)
- ✅ UnitOfWork cleared (in finally block)
- ✅ Error returned to client

This is correct! Events should not be dispatched if persistence fails.

### 5. **What Happens if Event Handler Fails?**

```python
# Event handler throws exception
class OrderConfirmedEventHandler(DomainEventHandler):
    async def handle_async(self, event: OrderConfirmedEvent) -> Any:
        await self.sms_service.send(...)  # ← SMS service is down!
```

**Result**:

- ✅ Order ALREADY persisted (happened before events)
- ⚠️ Event dispatch fails (logged as error)
- ✅ Command returns success (order was saved)
- ⚠️ Side effect failed (eventual consistency)

**Solution**: Implement retry logic, use message queue, or accept eventual consistency.

---

## 🔄 Comparison: With vs Without UnitOfWork

### ❌ WITHOUT UnitOfWork (Manual Event Dispatching)

```python
async def handle_async(self, command: PlaceOrderCommand) -> OperationResult:
    order = Order(customer_id=command.customer_id)
    order.confirm_order()  # Raises OrderConfirmedEvent

    await self.order_repository.add_async(order)

    # Manual event dispatching - UGLY!
    events = order.get_uncommitted_events()
    for event in events:
        await self.mediator.publish_async(event)  # ← Manual, repeated code
    order.clear_pending_events()  # ← Easy to forget

    return self.created(...)
```

**Problems**:

- 🔴 Repeated code in every handler
- 🔴 Easy to forget event dispatching
- 🔴 Easy to forget clearing events
- 🔴 Hard to test
- 🔴 No transaction coordination

### ✅ WITH UnitOfWork (Current Approach)

```python
async def handle_async(self, command: PlaceOrderCommand) -> OperationResult:
    order = Order(customer_id=command.customer_id)
    order.confirm_order()  # Raises OrderConfirmedEvent

    await self.order_repository.add_async(order)

    self.unit_of_work.register_aggregate(order)  # ← Simple, consistent

    return self.created(...)
    # Middleware handles event dispatching automatically
```

**Benefits**:

- ✅ Consistent pattern across all handlers
- ✅ Automatic event dispatching
- ✅ Automatic cleanup
- ✅ Easy to test
- ✅ Transaction-aware

---

## 📊 Complete Sequence Diagram

```
Client          Controller      Mediator       Middleware      Handler         Repository      UnitOfWork      EventHandlers
  |                 |              |              |              |                |               |               |
  |-- POST /orders ->|              |              |              |                |               |               |
  |                 |              |              |              |                |               |               |
  |                 |--execute_async(cmd)-------->|              |                |               |               |
  |                 |              |              |              |                |               |               |
  |                 |              |              |--next_handler()-------------->|               |               |
  |                 |              |              |              |                |               |               |
  |                 |              |              |              |--create Order--|               |               |
  |                 |              |              |              | (events raised)|               |               |
  |                 |              |              |              |                |               |               |
  |                 |              |              |              |--add_async(order)------------->|               |
  |                 |              |              |              |                | (state saved) |               |
  |                 |              |              |              |                |<--------------|               |
  |                 |              |              |              |                |               |               |
  |                 |              |              |              |--register_aggregate(order)---->|               |
  |                 |              |              |              |                |               | (track events)|
  |                 |              |              |              |                |               |               |
  |                 |              |              |              |--return success---------------->|               |
  |                 |              |              |              |                |               |               |
  |                 |              |              |<-result.is_success------------|               |               |
  |                 |              |              |              |                |               |               |
  |                 |              |              |--get_domain_events()--------->|               |               |
  |                 |              |              |              |                |--return events|               |
  |                 |              |              |<-------------|                |               |               |
  |                 |              |              |              |                |               |               |
  |                 |              |              |--publish_async(OrderConfirmedEvent)---------->|               |
  |                 |              |              |              |                |               |--handle------>|
  |                 |              |              |              |                |               |   (SMS sent)  |
  |                 |              |              |              |                |               |   (email sent)|
  |                 |              |              |              |                |               |<--------------|
  |                 |              |              |              |                |               |               |
  |                 |              |              |--clear()-----|                |-------------->|               |
  |                 |              |              |              |                | (events cleared)              |
  |                 |              |              |              |                |               |               |
  |                 |              |<--return result-------------|                |               |               |
  |                 |<--return OrderDto-----------|              |                |               |               |
  |<--201 Created---|              |              |              |                |               |               |
```

---

## 🎓 Summary: The Answers

### Q: "What are Domain Events used for?"

**A**: Side effects that must happen AFTER aggregate persistence:

- Sending notifications (SMS, email, push)
- Updating read models / analytics databases
- Publishing to message bus for other services
- Logging business events
- Triggering workflows in other bounded contexts

### Q: "How does that happen?"

**A**: Through the `DomainEventDispatchingMiddleware`:

1. Middleware wraps every command execution
2. Handler executes, persists state, registers aggregates
3. Handler returns success
4. Middleware collects events from registered aggregates
5. Middleware publishes events to event handlers
6. Event handlers execute side effects
7. Middleware clears UnitOfWork

### Q: "Does the aggregate need to register itself?"

**A**: Yes, explicitly in the handler:

```python
self.unit_of_work.register_aggregate(order)
```

This is intentional - gives you control over which aggregates' events get dispatched.

### Q: "What gets persisted to the repository?"

**A**: Only the aggregate's **state** (`order.state.*`), NOT events:

- ✅ `order.state` → Persisted to MongoDB/files
- ❌ `order._pending_events` → Collected and dispatched, then cleared
- ⚠️ Events CAN be persisted to EventStore (optional, for Event Sourcing)

---

## 🔗 Related Files in Mario Pizzeria

| File                                                                       | Purpose                                      |
| -------------------------------------------------------------------------- | -------------------------------------------- |
| `main.py`                                                                  | Registers `DomainEventDispatchingMiddleware` |
| `application/commands/place_order_command.py`                              | Handler that registers aggregates            |
| `application/event_handlers.py`                                            | Event handlers for side effects              |
| `domain/aggregate_root.py`                                                 | Base class with `raise_event()`              |
| `domain/entities/order.py`                                                 | Aggregate that raises events                 |
| `src/neuroglia/data/unit_of_work.py`                                       | Collects events from aggregates              |
| `src/neuroglia/mediation/behaviors/domain_event_dispatching_middleware.py` | Orchestrates event dispatching               |

---

This pattern gives you:
✅ Clean separation of concerns
✅ Automatic event dispatching
✅ Testable handlers
✅ Eventual consistency
✅ Extensible side effects (just add new event handlers!)
