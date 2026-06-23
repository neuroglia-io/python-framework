# 🎯 CQRS with Mediator Pattern

_Estimated reading time: 12 minutes_

## 🎯 What & Why

**CQRS (Command Query Responsibility Segregation)** separates write operations (Commands) from read operations (Queries). The **Mediator Pattern** decouples request senders from handlers, creating a clean, testable architecture.

### The Problem Without CQRS

```python
# ❌ Without CQRS - business logic mixed in controller
@app.post("/orders")
async def create_order(order_data: dict, db: Database):
    # Validation in controller
    if not order_data.get("customer_id"):
        return {"error": "Customer required"}, 400

    # Business logic in controller
    order = Order(**order_data)
    order.calculate_total()

    # Data access in controller
    await db.orders.insert_one(order.__dict__)

    # Side effects in controller
    await send_email(order.customer_email, "Order confirmed")

    return {"id": order.id}, 201
```

**Problems:**

- Controller has too many responsibilities
- Business logic can't be reused
- Testing requires mocking HTTP layer
- Difficult to add behaviors (logging, validation, caching)

### The Solution With CQRS + Mediator

```python
# ✅ With CQRS - clean separation of concerns
@app.post("/orders")
async def create_order(dto: CreateOrderDto):
    command = CreateOrderCommand(
        customer_id=dto.customer_id,
        items=dto.items
    )
    result = await self.mediator.execute_async(command)
    return self.process(result)

# Business logic in handler (testable, reusable)
class CreateOrderHandler(CommandHandler):
    async def handle_async(self, command: CreateOrderCommand):
        # Validation, business logic, persistence all in one place
        ...
```

**Benefits:**

- Controllers are thin (orchestration only)
- Business logic is isolated and testable
- Easy to add cross-cutting concerns (validation, logging, caching)
- Handlers are reusable across different entry points

## 🚀 Getting Started

### Basic Setup

```python
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator, Command, Query, CommandHandler, QueryHandler
from neuroglia.core.operation_result import OperationResult

# Step 1: Create application builder
builder = WebApplicationBuilder()

# Step 2: Configure mediator (auto-discovers handlers in specified modules)
Mediator.configure(builder, ["application.commands", "application.queries"])

# Step 3: Build app
app = builder.build()
```

### Your First Command and Handler

```python
from dataclasses import dataclass
from neuroglia.mediation import Command, CommandHandler
from neuroglia.core.operation_result import OperationResult

# Define the command (what you want to do)
@dataclass
class CreatePizzaCommand(Command[OperationResult[dict]]):
    customer_id: str
    pizza_type: str
    size: str

# Implement the handler (how to do it)
class CreatePizzaHandler(CommandHandler[CreatePizzaCommand, OperationResult[dict]]):
    async def handle_async(self, command: CreatePizzaCommand) -> OperationResult[dict]:
        # Validation
        if command.size not in ["small", "medium", "large"]:
            return self.bad_request("Invalid pizza size")

        # Business logic
        pizza = {
            "id": str(uuid.uuid4()),
            "customer_id": command.customer_id,
            "type": command.pizza_type,
            "size": command.size,
            "price": self.calculate_price(command.size)
        }

        # Return result
        return self.created(pizza)

    def calculate_price(self, size: str) -> float:
        prices = {"small": 10.0, "medium": 15.0, "large": 20.0}
        return prices[size]

# Use in controller
class PizzaController(ControllerBase):
    @post("/pizzas")
    async def create_pizza(self, dto: CreatePizzaDto):
        command = self.mapper.map(dto, CreatePizzaCommand)
        result = await self.mediator.execute_async(command)
        return self.process(result)  # Automatically converts to HTTP response
```

## 🏗️ Core Components

### 0. RequestHandler Helper Methods

All command and query handlers inherit from `RequestHandler`, which provides **12 helper methods** for creating standardized `OperationResult` responses:

#### Success Methods (2xx)

| Method           | Status         | Use Case               | Example                          |
| ---------------- | -------------- | ---------------------- | -------------------------------- |
| `ok(data)`       | 200 OK         | Standard success       | `return self.ok(user_dto)`       |
| `created(data)`  | 201 Created    | Resource creation      | `return self.created(order_dto)` |
| `accepted(data)` | 202 Accepted   | Async operation queued | `return self.accepted(job_id)`   |
| `no_content()`   | 204 No Content | Successful delete/void | `return self.no_content()`       |

#### Client Error Methods (4xx)

| Method                         | Status            | Use Case         | Example                                                  |
| ------------------------------ | ----------------- | ---------------- | -------------------------------------------------------- |
| `bad_request(detail)`          | 400 Bad Request   | Validation error | `return self.bad_request("Email required")`              |
| `unauthorized(detail)`         | 401 Unauthorized  | Auth required    | `return self.unauthorized("Invalid token")`              |
| `forbidden(detail)`            | 403 Forbidden     | Access denied    | `return self.forbidden("Insufficient permissions")`      |
| `not_found(type, key)`         | 404 Not Found     | Resource missing | `return self.not_found(User, user_id)`                   |
| `conflict(message)`            | 409 Conflict      | State conflict   | `return self.conflict("Email already exists")`           |
| `unprocessable_entity(detail)` | 422 Unprocessable | Semantic error   | `return self.unprocessable_entity("Invalid date range")` |

#### Server Error Methods (5xx)

| Method                          | Status          | Use Case         | Example                                                     |
| ------------------------------- | --------------- | ---------------- | ----------------------------------------------------------- |
| `internal_server_error(detail)` | 500 Internal    | Unexpected error | `return self.internal_server_error("DB connection failed")` |
| `service_unavailable(detail)`   | 503 Unavailable | Service down     | `return self.service_unavailable("Maintenance mode")`       |

**Important:** Always use these helper methods instead of constructing `OperationResult` manually:

```python
# ✅ CORRECT - Use helper methods
return self.ok(user_dto)
return self.created(order_dto)
return self.bad_request("Invalid input")

# ❌ WRONG - Don't construct manually
result = OperationResult("OK", 200)  # Don't do this!
result.data = user_dto
return result
```

### 1. Commands (Write Operations)

Commands represent **intentions to change state**:

```python
from dataclasses import dataclass
from neuroglia.mediation import Command
from neuroglia.core.operation_result import OperationResult

# Command naming: <Verb><Noun>Command
@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    customer_id: str
    items: list[OrderItemDto]
    delivery_address: str
    payment_method: str

@dataclass
class CancelOrderCommand(Command[OperationResult[OrderDto]]):
    order_id: str
    reason: str

@dataclass
class UpdateOrderStatusCommand(Command[OperationResult[OrderDto]]):
    order_id: str
    new_status: str
```

**Command Characteristics:**

- Represent user intentions ("Place an order", "Cancel order")
- May fail (validation, business rules)
- Should not return data (use queries for reading)
- Named with verbs: `PlaceOrder`, `CancelOrder`, `UpdateInventory`

### 2. Queries (Read Operations)

Queries represent **requests for data**:

```python
# Query naming: <Verb><Noun>Query or Get<Noun>Query
@dataclass
class GetOrderQuery(Query[OperationResult[OrderDto]]):
    order_id: str

@dataclass
class ListCustomerOrdersQuery(Query[OperationResult[list[OrderDto]]]):
    customer_id: str
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20

@dataclass
class SearchPizzasQuery(Query[OperationResult[list[PizzaDto]]]):
    search_term: str
    category: Optional[str] = None
```

**Query Characteristics:**

- Never modify state (idempotent)
- Always succeed or return empty results
- Named with questions: `GetOrder`, `ListOrders`, `SearchPizzas`
- Can be cached aggressively

### 3. Command Handlers

Command handlers contain write-side business logic:

```python
from neuroglia.mediation import CommandHandler
from neuroglia.core.operation_result import OperationResult

class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        inventory_service: InventoryService,
        payment_service: PaymentService,
        mapper: Mapper
    ):
        super().__init__()
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.inventory_service = inventory_service
        self.payment_service = payment_service
        self.mapper = mapper

    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
        # Step 1: Validation
        customer = await self.customer_repository.get_by_id_async(command.customer_id)
        if not customer:
            return self.not_found("Customer", command.customer_id)

        if not command.items:
            return self.bad_request("Order must have at least one item")

        # Step 2: Business Rules
        if not await self.inventory_service.check_availability(command.items):
            return self.bad_request("Some items are out of stock")

        # Step 3: Calculate totals
        subtotal = sum(item.price * item.quantity for item in command.items)
        tax = subtotal * 0.08
        total = subtotal + tax

        # Step 4: Process payment
        payment_result = await self.payment_service.charge_async(
            customer.payment_method,
            total
        )

        if not payment_result.success:
            return self.bad_request(f"Payment failed: {payment_result.error}")

        # Step 5: Create order entity
        order = Order(
            customer_id=command.customer_id,
            items=command.items,
            delivery_address=command.delivery_address,
            subtotal=subtotal,
            tax=tax,
            total=total,
            payment_transaction_id=payment_result.transaction_id
        )

        # Step 6: Reserve inventory
        await self.inventory_service.reserve_items(command.items, order.id)

        # Step 7: Persist
        await self.order_repository.save_async(order)

        # Step 8: Return result
        return self.created(self.mapper.map(order, OrderDto))
```

### 4. Query Handlers

Query handlers contain read-side logic:

```python
from neuroglia.mediation import QueryHandler

class ListCustomerOrdersHandler(QueryHandler[ListCustomerOrdersQuery, OperationResult[list[OrderDto]]]):
    def __init__(
        self,
        order_repository: IOrderRepository,
        mapper: Mapper
    ):
        super().__init__()
        self.order_repository = order_repository
        self.mapper = mapper

    async def handle_async(self, query: ListCustomerOrdersQuery) -> OperationResult[list[OrderDto]]:
        # Queries use optimized read models
        orders = await self.order_repository.list_by_customer_async(
            customer_id=query.customer_id,
            status=query.status,
            page=query.page,
            page_size=query.page_size
        )

        # Map to DTOs
        dtos = [self.mapper.map(order, OrderDto) for order in orders]

        return self.ok(dtos)
```

## 💡 Real-World Example: Mario's Pizzeria

Complete CQRS implementation for pizza ordering:

### Domain Layer

```python
import asyncio

async def main():
    # Create app with ultra-simple setup
    provider = create_simple_app(
        CreateTaskHandler,
        GetTaskHandler,
        CompleteTaskHandler,
        repositories=[InMemoryRepository[Task]]
    )

    mediator = provider.get_service(Mediator)

    # Create a task
    create_result = await mediator.execute_async(
        CreateTaskCommand("Learn Neuroglia CQRS")
    )

    if create_result.is_success:
        print(f"✅ Created: {create_result.data.title}")
        task_id = create_result.data.id

        # Complete the task
        complete_result = await mediator.execute_async(
            CompleteTaskCommand(task_id)
        )

        if complete_result.is_success:
            print(f"✅ Completed: {complete_result.data.title}")

        # Get the task
        get_result = await mediator.execute_async(GetTaskQuery(task_id))

        if get_result.is_success:
            task = get_result.data
            print(f"📋 Task: {task.title} (completed: {task.completed})")

if __name__ == "__main__":
    asyncio.run(main())
```

## 💡 Key Patterns

### Validation and Error Handling

Use helper methods for consistent error responses:

```python
async def handle_async(self, request: CreateUserCommand) -> OperationResult[UserDto]:
    # Input validation → 400 Bad Request
    if not request.email:
        return self.bad_request("Email is required")

    if "@" not in request.email:
        return self.bad_request("Invalid email format")

    # Business validation → 409 Conflict
    existing_user = await self.repository.get_by_email_async(request.email)
    if existing_user:
        return self.conflict(f"User with email {request.email} already exists")

    # Authorization check → 403 Forbidden
    if not request.user_context.has_permission("users:create"):
        return self.forbidden("Insufficient permissions to create users")

    # Success path → 201 Created
    user = User(str(uuid.uuid4()), request.name, request.email)
    await self.repository.save_async(user)

    dto = UserDto(user.id, user.name, user.email)
    return self.created(dto)
```

### Using All Helper Methods

```python
class OrderHandler(CommandHandler):
    async def handle_async(self, command: ProcessOrderCommand) -> OperationResult[OrderDto]:
        # 400 - Validation errors
        if not command.items:
            return self.bad_request("Order must contain items")

        # 401 - Authentication required
        if not command.auth_token:
            return self.unauthorized("Authentication required")

        # 403 - Authorization failed
        if not await self.has_permission(command.user_id, "orders:create"):
            return self.forbidden("Cannot create orders for other users")

        # 404 - Resource not found
        customer = await self.customer_repo.get_async(command.customer_id)
        if not customer:
            return self.not_found(Customer, command.customer_id)

        # 409 - Conflict
        if customer.account_suspended:
            return self.conflict("Customer account is suspended")

        # 422 - Semantic validation
        if command.delivery_date < datetime.now():
            return self.unprocessable_entity("Delivery date cannot be in the past")

        # 500 - Unexpected error (in try/catch)
        try:
            order = await self.process_order(command)
            return self.created(order)  # 201 Created
        except Exception as e:
            log.error(f"Order processing failed: {e}")
            return self.internal_server_error("Failed to process order")
```

### Repository Patterns

```python
# Simple in-memory repository (for testing/prototyping)
from neuroglia.mediation import InMemoryRepository

class UserRepository(InMemoryRepository[User]):
    async def get_by_email_async(self, email: str) -> Optional[User]:
        for user in self._storage.values():
            if user.email == email:
                return user
        return None
```

### Query Result Patterns

```python
# Single item query
@dataclass
class GetUserQuery(Query[OperationResult[UserDto]]):
    user_id: str

# List query
@dataclass
class ListUsersQuery(Query[OperationResult[List[UserDto]]]):
    include_inactive: bool = False

# Search query
@dataclass
class SearchUsersQuery(Query[OperationResult[List[UserDto]]]):
    search_term: str
    page: int = 1
    page_size: int = 10
```

## 🔧 Configuration Options

### Simple Application Settings

Instead of the full `ApplicationSettings`, use `SimpleApplicationSettings` for basic apps:

```python
from neuroglia.mediation import SimpleApplicationSettings

@dataclass
class MyAppSettings(SimpleApplicationSettings):
    app_name: str = "Task Manager"
    max_tasks_per_user: int = 100
    enable_notifications: bool = True
```

### Environment Integration

```python
import os

settings = SimpleApplicationSettings(
    app_name=os.getenv("APP_NAME", "My App"),
    debug=os.getenv("DEBUG", "false").lower() == "true",
    database_url=os.getenv("DATABASE_URL")
)
```

## 🧪 Testing Patterns

### Unit Testing Handlers

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_create_task_success():
    # Arrange
    repository = AsyncMock(spec=InMemoryRepository[Task])
    handler = CreateTaskHandler(repository)
    command = CreateTaskCommand("Test task")

    # Act
    result = await handler.handle_async(command)

    # Assert
    assert result.is_success
    assert result.data.title == "Test task"
    repository.save_async.assert_called_once()

@pytest.mark.asyncio
async def test_create_task_empty_title():
    # Arrange
    repository = AsyncMock(spec=InMemoryRepository[Task])
    handler = CreateTaskHandler(repository)
    command = CreateTaskCommand("")

    # Act
    result = await handler.handle_async(command)

    # Assert
    assert not result.is_success
    assert result.status_code == 400
    assert "empty" in result.error_message.lower()
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_complete_workflow():
    # Create application
    provider = create_simple_app(
        CreateTaskHandler,
        GetTaskHandler,
        CompleteTaskHandler,
        repositories=[InMemoryRepository[Task]]
    )

    mediator = provider.get_service(Mediator)

    # Test complete workflow
    create_result = await mediator.execute_async(CreateTaskCommand("Test"))
    assert create_result.is_success

    task_id = create_result.data.id

    get_result = await mediator.execute_async(GetTaskQuery(task_id))
    assert get_result.is_success
    assert not get_result.data.completed

    complete_result = await mediator.execute_async(CompleteTaskCommand(task_id))
    assert complete_result.is_success
    assert complete_result.data.completed
```

## 🚀 When to Upgrade

Consider upgrading to the full Neuroglia framework features when you need:

### Event Sourcing

```python
# Upgrade to event sourcing when you need:
# - Complete audit trails
# - Event replay capabilities
# - Complex business workflows
# - Temporal queries ("what was the state at time X?")
```

### Cloud Events

```python
# Upgrade to cloud events when you need:
# - Microservice integration
# - Event-driven architecture
# - Cross-system communication
# - Reliable event delivery
```

### Domain Events

```python
# Upgrade to domain events when you need:
# - Side effects from business operations
# - Decoupled business logic
# - Complex business rules
# - Integration events
```

## 🔗 Related Documentation

- [Getting Started](../getting-started.md) - Framework overview
- [CQRS & Mediation](../patterns/cqrs.md) - Advanced CQRS patterns
- [Dependency Injection](../patterns/dependency-injection.md) - Advanced DI patterns
- [Data Access](data-access.md) - Repository patterns and persistence
