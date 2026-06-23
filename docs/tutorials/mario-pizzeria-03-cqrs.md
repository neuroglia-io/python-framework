# Part 3: Commands & Queries (CQRS)

**Time: 1 hour** | **Prerequisites: [Part 2](mario-pizzeria-02-domain.md)**

In this tutorial, you'll implement CQRS (Command Query Responsibility Segregation), the architectural pattern that separates read and write operations for better scalability and maintainability.

## 🎯 What You'll Learn

- What CQRS is and why it matters
- The difference between commands and queries
- How to create command/query handlers
- Using the mediator pattern to route requests
- Testing CQRS components

## 🤔 Understanding CQRS

### The Problem

Traditional applications mix reads and writes in the same models:

```python
# ❌ Mixed concerns - same service handles reads and writes
class OrderService:
    def create_order(self, data):  # Write
        order = Order(**data)
        self.db.save(order)
        return order

    def get_order(self, order_id):  # Read
        return self.db.get(order_id)

    def list_orders(self, filters):  # Read
        return self.db.query(filters)
```

**Problems:**

- Read and write models often have different requirements
- Difficult to optimize separately
- Security: reads and writes mixed together
- Scaling: can't scale reads independently

### The Solution: CQRS

**CQRS separates commands (writes) from queries (reads):**

```
┌─────────────┐       ┌──────────────┐
│  Commands   │       │   Queries    │
│  (Writes)   │       │   (Reads)    │
└──────┬──────┘       └──────┬───────┘
       │                     │
       ▼                     ▼
┌─────────────┐       ┌──────────────┐
│  Command    │       │    Query     │
│  Handlers   │       │   Handlers   │
└──────┬──────┘       └──────┬───────┘
       │                     │
       ▼                     ▼
┌─────────────────────────────────┐
│       Domain / Repository       │
└─────────────────────────────────┘
```

**Benefits:**

- **Separation**: Different models for reads vs writes
- **Optimization**: Query handlers can use denormalized views
- **Security**: Easy to apply different permissions
- **Scalability**: Scale read and write sides independently
- **Clarity**: Clear intent (is this changing state or just reading?)

## 📝 Creating Commands

Commands represent **intentions to change state**.

### Step 1: Define the Command

Create `application/commands/place_order_command.py`:

```python
"""Place Order Command"""
from dataclasses import dataclass, field
from typing import Optional

from api.dtos import CreatePizzaDto, OrderDto
from neuroglia.core import OperationResult
from neuroglia.mediation import Command


@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    """
    Command to place a new pizza order.

    Commands:
    - Represent an intention to do something
    - Have imperative names (Place, Create, Update, Delete)
    - Return a result (success/failure)
    - Are validated before execution
    """
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = None
    customer_email: Optional[str] = None
    pizzas: list[CreatePizzaDto] = field(default_factory=list)
    payment_method: str = "cash"
    notes: Optional[str] = None
```

**Command characteristics:**

- **Intention**: "Place an order" (verb + noun)
- **Generic return type**: `Command[OperationResult[OrderDto]]` tells mediator what to expect
- **Immutable**: Uses `@dataclass` with no setters
- **Validated**: Framework can automatically validate before handler executes

### Step 2: Create the Command Handler

Continue in `application/commands/place_order_command.py`:

```python
from domain.entities import Customer, Order, OrderItem, PizzaSize
from domain.repositories import IOrderRepository, ICustomerRepository
from neuroglia.mapping import Mapper
from neuroglia.mediation import CommandHandler
from uuid import uuid4
from decimal import Decimal


class PlaceOrderCommandHandler(
    CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]
):
    """
    Handler for placing pizza orders.

    Handler responsibilities:
    - Validate the command
    - Coordinate domain operations
    - Persist changes via repositories
    - Return result

    The handler IS the transaction boundary.
    """

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        """
        Dependencies injected by framework's DI container.

        Notice: Handler doesn't create its own dependencies!
        """
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(
        self,
        request: PlaceOrderCommand
    ) -> OperationResult[OrderDto]:
        """
        Execute the command.

        Pattern: Try to execute, return OperationResult with success/failure
        """
        try:
            # 1️⃣ Get or create customer
            customer = await self._get_or_create_customer(request)

            # 2️⃣ Create order (domain logic)
            order = Order(customer_id=customer.id())
            if request.notes:
                order.state.notes = request.notes

            # 3️⃣ Add pizzas to order
            for pizza_dto in request.pizzas:
                size = PizzaSize(pizza_dto.size.lower())

                # Business logic: Calculate price
                base_price = self._calculate_pizza_price(pizza_dto.name)

                # Create order item (value object)
                order_item = OrderItem(
                    line_item_id=str(uuid4()),
                    name=pizza_dto.name,
                    size=size,
                    quantity=1,
                    unit_price=base_price
                )

                # Add to order (business rules enforced here)
                order.add_order_item(order_item)

            # 4️⃣ Validate order has items
            if order.pizza_count == 0:
                return self.bad_request("Order must contain at least one pizza")

            # 5️⃣ Confirm order (raises domain event internally)
            order.confirm_order()

            # 6️⃣ Persist changes - repository publishes events automatically
            await self.order_repository.add_async(order)
            # Repository does:
            # - Saves order state to database
            # - Gets uncommitted events from order
            # - Publishes events to event bus
            # - Clears events from order

            # 7️⃣ Map to DTO and return success
            order_dto = self.mapper.map(order, OrderDto)
            return self.created(order_dto)

        except ValueError as e:
            # Business rule violation
            return self.bad_request(str(e))
        except Exception as e:
            # Unexpected error
            return self.internal_server_error(f"Failed to place order: {str(e)}")

    async def _get_or_create_customer(
        self,
        request: PlaceOrderCommand
    ) -> Customer:
        """Helper to find existing customer or create new one"""
        customers = await self.customer_repository.list_async()

        # Try to find by phone
        for customer in customers:
            if customer.state.phone == request.customer_phone:
                return customer

        # Create new customer
        customer = Customer(
            name=request.customer_name,
            phone=request.customer_phone,
            email=request.customer_email,
            address=request.customer_address
        )

        await self.customer_repository.add_async(customer)
        return customer

    def _calculate_pizza_price(self, pizza_name: str) -> Decimal:
        """Business logic: Calculate pizza base price"""
        prices = {
            "margherita": Decimal("12.99"),
            "pepperoni": Decimal("14.99"),
            "supreme": Decimal("17.99"),
        }
        return prices.get(pizza_name.lower(), Decimal("12.99"))

```

**Key points:**

- Handler does **orchestration**, not business logic (that's in domain)
- Uses **dependency injection** for repositories
- Returns **OperationResult** for consistent error handling
- **Validates** before persisting
- Uses **UnitOfWork** for transactional boundaries

## 🔍 Creating Queries

Queries represent **requests for information** without side effects.

### Step 1: Define the Query

Create `application/queries/get_order_by_id_query.py`:

```python
"""Get Order By ID Query"""
from dataclasses import dataclass

from api.dtos import OrderDto
from neuroglia.core import OperationResult
from neuroglia.mediation import Query


@dataclass
class GetOrderByIdQuery(Query[OperationResult[OrderDto]]):
    """
    Query to retrieve an order by ID.

    Queries:
    - Request information without side effects
    - Have question-like names (Get, Find, List, Search)
    - Return data (DTOs, view models)
    - Can be cached
    """
    order_id: str
```

### Step 2: Create the Query Handler

Continue in `application/queries/get_order_by_id_query.py`:

```python
from domain.repositories import IOrderRepository, ICustomerRepository
from neuroglia.mapping import Mapper
from neuroglia.mediation import QueryHandler


class GetOrderByIdQueryHandler(
    QueryHandler[GetOrderByIdQuery, OperationResult[OrderDto]]
):
    """
    Handler for retrieving orders by ID.

    Query handlers:
    - Read-only operations
    - Can use optimized read models
    - Should be fast (consider caching)
    - No business rule changes
    """

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(
        self,
        request: GetOrderByIdQuery
    ) -> OperationResult[OrderDto]:
        """Execute the query"""
        try:
            # 1️⃣ Get order from repository
            order = await self.order_repository.get_async(request.order_id)

            if not order:
                return self.not_found("Order", request.order_id)

            # 2️⃣ Get related data (customer)
            customer = None
            if order.state.customer_id:
                customer = await self.customer_repository.get_async(
                    order.state.customer_id
                )

            # 3️⃣ Map to DTO (with customer details)
            order_dto = self.mapper.map(order, OrderDto)

            if customer:
                order_dto.customer_name = customer.state.name
                order_dto.customer_phone = customer.state.phone

            # 4️⃣ Return success
            return self.ok(order_dto)

        except Exception as e:
            return self.bad_request(f"Failed to get order: {str(e)}")
```

**Query handler characteristics:**

- **Read-only**: No state changes
- **Fast**: Optimized for retrieval
- **Idempotent**: Same input = same output
- **Can use different storage**: Could query a read-optimized database

## 🚦 Using the Mediator

The mediator routes commands/queries to their handlers without controllers needing to know about handlers directly.

### How it Works

```python
# In controller
async def create_order(self, data: CreateOrderDto):
    # Create command
    command = self.mapper.map(data, PlaceOrderCommand)

    # Send to mediator (framework finds the handler)
    result = await self.mediator.execute_async(command)

    # Process result
    return self.process(result)
```

**The magic:**

1. Mediator inspects command type: `PlaceOrderCommand`
2. Looks up registered handler: `PlaceOrderCommandHandler`
3. Resolves handler dependencies from DI container
4. Executes `handler.handle_async(command)`
5. Returns result to caller

**Benefits:**

- Controllers don't depend on concrete handlers
- Easy to add middleware (logging, validation, transactions)
- Handlers can be tested independently
- Clear request → response flow

## 🧪 Testing CQRS Components

### Testing a Command Handler

Create `tests/application/commands/test_place_order_handler.py`:

```python
"""Tests for PlaceOrderCommandHandler"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

from application.commands.place_order_command import (
    PlaceOrderCommand,
    PlaceOrderCommandHandler
)
from api.dtos import CreatePizzaDto
from domain.entities import Customer, Order


@pytest.fixture
def mock_repositories():
    """Create mock repositories"""
    order_repo = AsyncMock()
    customer_repo = AsyncMock()
    return order_repo, customer_repo


@pytest.fixture
def handler(mock_repositories):
    """Create handler with mocked dependencies"""
    order_repo, customer_repo = mock_repositories
    mapper = Mock()
    unit_of_work = AsyncMock()

    return PlaceOrderCommandHandler(
        order_repository=order_repo,
        customer_repository=customer_repo,
        mapper=mapper,
        unit_of_work=unit_of_work
    )


@pytest.mark.asyncio
async def test_place_order_success(handler, mock_repositories):
    """Test successful order placement"""
    order_repo, customer_repo = mock_repositories

    # Setup: Mock customer exists
    mock_customer = Mock(spec=Customer)
    mock_customer.id.return_value = "cust-123"
    customer_repo.list_async.return_value = [mock_customer]

    # Execute command
    command = PlaceOrderCommand(
        customer_name="John Doe",
        customer_phone="555-1234",
        pizzas=[
            CreatePizzaDto(name="Margherita", size="large"),
        ]
    )

    result = await handler.handle_async(command)

    # Assert
    assert result.is_success
    assert result.status_code == 201  # Created
    handler.unit_of_work.save_changes_async.assert_called_once()


@pytest.mark.asyncio
async def test_place_order_empty_pizzas(handler, mock_repositories):
    """Test business rule: order must have pizzas"""
    order_repo, customer_repo = mock_repositories

    # Setup
    mock_customer = Mock(spec=Customer)
    mock_customer.id.return_value = "cust-123"
    customer_repo.list_async.return_value = [mock_customer]

    # Execute with no pizzas
    command = PlaceOrderCommand(
        customer_name="John Doe",
        customer_phone="555-1234",
        pizzas=[]  # Empty!
    )

    result = await handler.handle_async(command)

    # Assert
    assert not result.is_success
    assert result.status_code == 400
    assert "at least one pizza" in result.error_message.lower()
```

### Testing a Query Handler

Create `tests/application/queries/test_get_order_handler.py`:

```python
"""Tests for GetOrderByIdQueryHandler"""
import pytest
from unittest.mock import AsyncMock, Mock

from application.queries.get_order_by_id_query import (
    GetOrderByIdQuery,
    GetOrderByIdQueryHandler
)
from domain.entities import Order, OrderStatus


@pytest.mark.asyncio
async def test_get_order_success():
    """Test successful order retrieval"""
    # Setup mocks
    order_repo = AsyncMock()
    customer_repo = AsyncMock()
    mapper = Mock()

    mock_order = Mock(spec=Order)
    mock_order.state.customer_id = "cust-123"
    mock_order.state.status = OrderStatus.CONFIRMED

    order_repo.get_async.return_value = mock_order
    customer_repo.get_async.return_value = None

    # Create handler
    handler = GetOrderByIdQueryHandler(
        order_repository=order_repo,
        customer_repository=customer_repo,
        mapper=mapper
    )

    # Execute query
    query = GetOrderByIdQuery(order_id="order-123")
    result = await handler.handle_async(query)

    # Assert
    assert result.is_success
    order_repo.get_async.assert_called_once_with("order-123")


@pytest.mark.asyncio
async def test_get_order_not_found():
    """Test order not found scenario"""
    order_repo = AsyncMock()
    customer_repo = AsyncMock()
    mapper = Mock()

    order_repo.get_async.return_value = None  # Not found

    handler = GetOrderByIdQueryHandler(
        order_repository=order_repo,
        customer_repository=customer_repo,
        mapper=mapper
    )

    query = GetOrderByIdQuery(order_id="nonexistent")
    result = await handler.handle_async(query)

    assert not result.is_success
    assert result.status_code == 404
```

Run tests:

```bash
poetry run pytest tests/application/ -v
```

## 📝 Key Takeaways

1. **CQRS Separation**: Commands change state, queries read state
2. **Mediator Pattern**: Decouples controllers from handlers
3. **Dependency Injection**: Handlers receive dependencies, don't create them
4. **OperationResult**: Consistent error handling across handlers
5. **Testability**: Easy to mock dependencies and test handlers in isolation

## 🚀 What's Next?

In [Part 4: API Controllers](mario-pizzeria-04-api.md), you'll learn:

- How to create REST controllers using FastAPI
- Connecting controllers to mediator
- DTOs for API contracts
- OpenAPI documentation generation

---

**Previous:** [← Part 2: Domain Model](mario-pizzeria-02-domain.md) | **Next:** [Part 4: API Controllers →](mario-pizzeria-04-api.md)
