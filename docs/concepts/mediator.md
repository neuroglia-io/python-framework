# Mediator Pattern

**Time to read: 10 minutes**

The Mediator pattern provides a **central dispatcher** that routes requests (commands and queries) to their handlers. Instead of controllers directly calling services, they send messages through the mediator.

## ❌ The Problem: Tight Coupling

Without mediator, controllers directly depend on all handlers:

```python
# ❌ Controller depends on every handler
class OrdersController:
    def __init__(self,
                 place_order_handler: PlaceOrderHandler,
                 confirm_order_handler: ConfirmOrderHandler,
                 cancel_order_handler: CancelOrderHandler,
                 get_order_handler: GetOrderByIdHandler,
                 get_customer_orders_handler: GetCustomerOrdersHandler):
        # Too many dependencies!
        self.place_order_handler = place_order_handler
        self.confirm_order_handler = confirm_order_handler
        self.cancel_order_handler = cancel_order_handler
        self.get_order_handler = get_order_handler
        self.get_customer_orders_handler = get_customer_orders_handler

    async def create_order(self, dto: CreateOrderDto):
        command = PlaceOrderCommand(...)
        return await self.place_order_handler.handle_async(command)

    async def confirm_order(self, order_id: str):
        command = ConfirmOrderCommand(order_id)
        return await self.confirm_order_handler.handle_async(command)
    # ... more methods, more handlers
```

**Problems:**

1. **Tight coupling**: Controller knows about all handlers
2. **Hard to test**: Need to mock every handler
3. **Hard to extend**: Adding handler requires changing controller
4. **Violates OCP**: Open/Closed Principle - controller changes for new operations
5. **Repetitive**: Same pattern everywhere

## ✅ The Solution: Central Mediator

Mediator routes requests to handlers without controllers knowing about them:

```
┌─────────────────────────────────────────────────┐
│                 Controller                      │
│                      │                          │
│                      ▼                          │
│              ┌──────────────┐                   │
│              │   Mediator   │                   │
│              └──────┬───────┘                   │
│                     │                           │
│         Routes based on request type            │
│                     │                           │
│     ┌───────────────┼───────────────┐          │
│     ▼               ▼               ▼          │
│ ┌────────┐     ┌────────┐     ┌────────┐      │
│ │Handler1│     │Handler2│     │Handler3│      │
│ └────────┘     └────────┘     └────────┘      │
│                                                 │
│ Controller → Mediator → Right Handler          │
│ (no direct coupling to handlers)               │
└─────────────────────────────────────────────────┘
```

**Benefits:**

1. **Loose coupling**: Controller only knows mediator
2. **Easy to test**: Mock one mediator instead of many handlers
3. **Easy to extend**: Add handlers without changing controllers
4. **Follows OCP**: Controllers closed for modification, open for extension
5. **Consistent**: Same pattern everywhere

## 🔧 Mediator in Neuroglia

### Basic Usage

```python
from neuroglia.mediation import Mediator, Command, Query, CommandHandler, QueryHandler

# 1. Define request (Command or Query)
@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    customer_id: str
    items: List[OrderItemDto]

# 2. Define handler
class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    def __init__(self, repository: IOrderRepository):
        self.repository = repository

    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
        order = Order(command.customer_id)
        for item in command.items:
            order.add_item(item.pizza_name, item.size, item.quantity, item.price)

        await self.repository.save_async(order)
        return self.created(order_dto)

# 3. Controller uses mediator
class OrdersController:
    def __init__(self, mediator: Mediator):
        self.mediator = mediator  # Only dependency!

    @post("/orders")
    async def create_order(self, dto: CreateOrderDto):
        # Create command
        command = PlaceOrderCommand(
            customer_id=dto.customer_id,
            items=dto.items
        )

        # Send through mediator
        result = await self.mediator.execute_async(command)

        return self.process(result)  # Mediator found and called PlaceOrderHandler
```

### Registration

Neuroglia auto-discovers handlers:

```python
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator

builder = WebApplicationBuilder()

# Configure mediator with handler discovery
Mediator.configure(builder, ["application.commands", "application.queries"])
```

### Request Types

**Commands** - Write operations:

```python
@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    """Command returns OperationResult."""
    customer_id: str
    items: List[OrderItemDto]

@dataclass
class ConfirmOrderCommand(Command[OperationResult]):
    """Command can return just OperationResult (no data)."""
    order_id: str
```

**Queries** - Read operations:

```python
@dataclass
class GetOrderByIdQuery(Query[OrderDto]):
    """Query returns data directly."""
    order_id: str

@dataclass
class GetCustomerOrdersQuery(Query[List[OrderDto]]):
    """Query can return collections."""
    customer_id: str
```

### Pipeline Behaviors

Add cross-cutting concerns that run for every request:

```python
from neuroglia.mediation import PipelineBehavior

class LoggingBehavior(PipelineBehavior):
    """Logs all commands/queries."""

    async def handle_async(self, request, next_handler):
        logger.info(f"Executing {request.__class__.__name__}")

        result = await next_handler()

        logger.info(f"Completed {request.__class__.__name__}")
        return result

class ValidationBehavior(PipelineBehavior):
    """Validates all commands."""

    async def handle_async(self, request, next_handler):
        # Validate before handling
        if isinstance(request, Command):
            errors = self.validate(request)
            if errors:
                return OperationResult.bad_request(errors)

        return await next_handler()

class TracingBehavior(PipelineBehavior):
    """Adds distributed tracing to requests."""

    def __init__(self, tracer):
        self.tracer = tracer

    async def handle_async(self, request, next_handler):
        with self.tracer.start_span(f"Handle {request.__class__.__name__}"):
            return await next_handler()

# Register behaviors (run in order)
services.add_scoped(PipelineBehavior, LoggingBehavior)
services.add_scoped(PipelineBehavior, ValidationBehavior)
services.add_scoped(PipelineBehavior, TracingBehavior)
```

**Pipeline execution:**

```
Request → LoggingBehavior → ValidationBehavior → TracingBehavior → Handler → Result
```

```

**Pipeline execution:**

```

Request → LoggingBehavior → ValidationBehavior → TransactionBehavior → Handler → Result
(logs) (validates) (transaction) (logic)

````

## 🏗️ Real-World Example: Mario's Pizzeria

```python
# Commands
@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    customer_id: str
    items: List[OrderItemDto]
    delivery_address: DeliveryAddressDto

@dataclass
class ConfirmOrderCommand(Command[OperationResult]):
    order_id: str

# Queries
@dataclass
class GetOrderByIdQuery(Query[OrderDto]):
    order_id: str

@dataclass
class GetOrdersByStatusQuery(Query[List[OrderDto]]):
    status: OrderStatus

# Handlers
class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: PlaceOrderCommand):
        # Create order, save, return result
        pass

class ConfirmOrderHandler(CommandHandler[ConfirmOrderCommand, OperationResult]):
    async def handle_async(self, command: ConfirmOrderCommand):
        # Confirm order, save, return result
        pass

class GetOrderByIdHandler(QueryHandler[GetOrderByIdQuery, OrderDto]):
    async def handle_async(self, query: GetOrderByIdQuery):
        # Retrieve order, return DTO
        pass

# Controller
class OrdersController(ControllerBase):
    # Only depends on mediator!
    def __init__(self, service_provider, mapper, mediator):
        super().__init__(service_provider, mapper, mediator)

    @post("/orders")
    async def create_order(self, dto: CreateOrderDto):
        command = self.mapper.map(dto, PlaceOrderCommand)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/orders/{order_id}/confirm")
    async def confirm_order(self, order_id: str):
        command = ConfirmOrderCommand(order_id=order_id)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @get("/orders/{order_id}")
    async def get_order(self, order_id: str):
        query = GetOrderByIdQuery(order_id=order_id)
        result = await self.mediator.execute_async(query)
        return result

    @get("/orders")
    async def get_orders_by_status(self, status: OrderStatus):
        query = GetOrdersByStatusQuery(status=status)
        result = await self.mediator.execute_async(query)
        return result
````

## 🧪 Testing with Mediator

### Unit Tests: Mock Mediator

```python
from unittest.mock import Mock, AsyncMock

async def test_create_order_controller():
    """Test controller with mocked mediator."""
    # Mock mediator
    mock_mediator = Mock(spec=Mediator)
    mock_mediator.execute_async = AsyncMock(
        return_value=OperationResult.created(OrderDto(...))
    )

    # Create controller
    controller = OrdersController(None, None, mock_mediator)

    # Call endpoint
    dto = CreateOrderDto(customer_id="123", items=[...])
    result = await controller.create_order(dto)

    # Verify
    assert result.status_code == 201
    mock_mediator.execute_async.assert_called_once()

    # Verify correct command was sent
    call_args = mock_mediator.execute_async.call_args[0][0]
    assert isinstance(call_args, PlaceOrderCommand)
    assert call_args.customer_id == "123"
```

### Integration Tests: Real Mediator

```python
async def test_order_workflow():
    """Test complete workflow through mediator."""
    # Setup real mediator with handlers
    builder = WebApplicationBuilder()

    # Configure mediator
    Mediator.configure(builder, ["application.commands", "application.queries"])

    # Register repositories
    builder.services.add_scoped(IOrderRepository, InMemoryOrderRepository)

    provider = builder.services.build_provider()
    mediator = provider.get_service(Mediator)

    # Place order
    place_command = PlaceOrderCommand(customer_id="123", items=[...])
    place_result = await mediator.execute_async(place_command)

    assert place_result.is_success
    order_id = place_result.data.order_id

    # Retrieve order
    get_query = GetOrderByIdQuery(order_id=order_id)
    get_result = await mediator.execute_async(get_query)

    assert get_result is not None
    assert get_result.order_id == order_id
```

## ⚠️ Common Mistakes

### 1. Bypassing Mediator

```python
# ❌ WRONG: Controller calls handler directly
class OrdersController:
    def __init__(self, mediator: Mediator, handler: PlaceOrderHandler):
        self.mediator = mediator
        self.handler = handler

    async def create_order(self, dto: CreateOrderDto):
        return await self.handler.handle_async(command)  # Bypasses mediator!

# ✅ RIGHT: Always use mediator
class OrdersController:
    def __init__(self, mediator: Mediator):
        self.mediator = mediator

    async def create_order(self, dto: CreateOrderDto):
        return await self.mediator.execute_async(command)  # Through mediator
```

### 2. Multiple Handlers for Same Request

```python
# ❌ WRONG: Two handlers for same command
class PlaceOrderHandler1(CommandHandler[PlaceOrderCommand, OperationResult]):
    pass

class PlaceOrderHandler2(CommandHandler[PlaceOrderCommand, OperationResult]):
    pass
# Mediator won't know which to use!

# ✅ RIGHT: One handler per request type
class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult]):
    pass
```

### 3. Handlers with Business Logic

```python
# ❌ WRONG: Handler has complex business logic
class PlaceOrderHandler(CommandHandler):
    async def handle_async(self, command):
        # Lots of business logic here
        if command.total < 10:
            raise ValueError()
        if not command.items:
            raise ValueError()
        # ... 100 lines of logic

# ✅ RIGHT: Handler orchestrates, domain has logic
class PlaceOrderHandler(CommandHandler):
    async def handle_async(self, command):
        order = Order(command.customer_id)  # Domain object
        for item in command.items:
            order.add_item(item)  # Domain logic in Order
        await self.repository.save_async(order)
        return self.created(order_dto)
```

## 🚫 When NOT to Use Mediator

Mediator adds indirection. Skip when:

1. **Tiny Apps**: < 5 operations, single controller
2. **Scripts/Tools**: No web API, direct service calls fine
3. **Prototypes**: Experimenting with ideas
4. **No CQRS**: If not separating commands/queries
5. **Performance Critical**: Direct calls slightly faster (rare concern)

For simple CRUD apps, traditional service layer is fine.

## 📝 Key Takeaways

1. **Central Dispatcher**: One mediator routes all requests
2. **Loose Coupling**: Controllers don't know handlers
3. **Pipeline Behaviors**: Cross-cutting concerns (logging, validation, transactions)
4. **Testability**: Mock mediator instead of many handlers
5. **Extensibility**: Add handlers without changing controllers

## 🔄 Mediator + Other Patterns

```
Controller
    ↓ sends Command/Query
Mediator
    ↓ routes to
Handler
    ↓ uses
Domain Model / Repository
    ↓ raises
Domain Events
    ↓ dispatched by
Event Bus (another mediator!)
```

## 🚀 Next Steps

- **See it in action**: [Tutorial Part 3](../tutorials/mario-pizzeria-03-cqrs.md) uses mediator
- **Add behaviors**: [Validation](../features/enhanced-model-validation.md) as pipeline behavior
- **Event handling**: [Event-Driven Architecture](event-driven.md) for domain events

## 📚 Further Reading

- [Mediator Pattern (GoF)](https://en.wikipedia.org/wiki/Mediator_pattern)
- [MediatR Library (.NET)](https://github.com/jbogard/MediatR) - inspiration for Neuroglia's mediator
- [CQRS with MediatR](https://github.com/jbogard/MediatR/wiki)

---

**Previous:** [← CQRS](cqrs.md) | **Next:** [Event-Driven Architecture →](event-driven.md)
