# Part 4: REST API Controllers

**Time: 45 minutes** | **Prerequisites: [Part 3](mario-pizzeria-03-cqrs.md)**

In this tutorial, you'll create REST API controllers that expose your application's functionality over HTTP. You'll learn how Neuroglia integrates with FastAPI to provide clean, testable controllers.

## 🎯 What You'll Learn

- How to create REST controllers using `ControllerBase`
- Using FastAPI decorators for routing
- Creating DTOs (Data Transfer Objects) for API contracts
- Auto-generated OpenAPI documentation
- Error handling and response formatting

## 🌐 Understanding Controllers

### The Problem

Traditional FastAPI apps mix routing, validation, and business logic:

```python
# ❌ Mixed concerns - everything in one place
@app.post("/orders")
async def create_order(data: dict):
    # Validation
    if not data.get("customer_name"):
        raise HTTPException(400, "Name required")

    # Business logic
    order = Order(**data)

    # Persistence
    db.save(order)

    return order
```

**Problems:**

- Hard to test (depends on global `app`)
- No separation of concerns
- Difficult to reuse logic
- Can't mock dependencies

### The Solution: Controller Pattern

Controllers are **thin orchestration layers** that delegate to handlers:

```
┌──────────────┐
│  HTTP Request│
└──────┬───────┘
       ▼
┌──────────────┐
│  Controller  │  • Parse request
│              │  • Create command/query
└──────┬───────┘  • Send to mediator
       ▼          • Format response
┌──────────────┐
│   Mediator   │
└──────┬───────┘
       ▼
┌──────────────┐
│   Handler    │  • Business logic
└──────────────┘  • Domain operations
```

**Benefits:**

- Controllers stay thin (10-20 lines per endpoint)
- Easy dependency injection
- Testable without HTTP layer
- Reusable business logic

## 📦 Creating DTOs

DTOs define your **API contract** - what data goes in and out.

### Step 1: Create Request DTOs

Create `api/dtos/order_dtos.py`:

```python
"""Data Transfer Objects for Order API"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from neuroglia.utils import CamelModel


@dataclass
class CreatePizzaDto:
    """DTO for adding a pizza to an order"""
    name: str
    size: str  # "small", "medium", "large", "xlarge"
    toppings: list[str] = field(default_factory=list)


class CreateOrderDto(CamelModel):
    """
    DTO for creating a new order.

    CamelModel automatically converts:
    - customer_name → customerName in JSON
    - customer_phone → customerPhone in JSON
    """
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = None
    customer_email: Optional[str] = None
    pizzas: list[CreatePizzaDto] = field(default_factory=list)
    payment_method: str = "cash"
    notes: Optional[str] = None
```

**Why CamelModel?**

JavaScript/TypeScript clients expect `camelCase`, but Python uses `snake_case`. `CamelModel` handles conversion automatically:

```python
# Python code
dto = CreateOrderDto(
    customer_name="John Doe",
    customer_phone="555-1234"
)

# Serializes to JSON as:
{
    "customerName": "John Doe",
    "customerPhone": "555-1234"
}
```

### Step 2: Create Response DTOs

Continue in `api/dtos/order_dtos.py`:

```python
class PizzaDto(CamelModel):
    """DTO for pizza in an order response"""
    id: str
    name: str
    size: str
    toppings: list[str]
    base_price: Decimal
    total_price: Decimal


class OrderDto(CamelModel):
    """DTO for order response"""
    id: str
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = None
    pizzas: list[PizzaDto]
    status: str
    order_time: datetime
    confirmed_time: Optional[datetime] = None
    cooking_started_time: Optional[datetime] = None
    actual_ready_time: Optional[datetime] = None
    estimated_ready_time: Optional[datetime] = None
    notes: Optional[str] = None
    total_amount: Decimal
    pizza_count: int

    # Staff tracking
    chef_name: Optional[str] = None
    ready_by_name: Optional[str] = None
    delivery_name: Optional[str] = None


class UpdateOrderStatusDto(CamelModel):
    """DTO for updating order status"""
    status: str
    reason: Optional[str] = None
```

**DTO Best Practices:**

- **Immutable**: Use `@dataclass(frozen=True)` or Pydantic models
- **Validation**: Use Pydantic for automatic validation
- **No Business Logic**: DTOs are just data containers
- **Version Control**: Create new DTOs for API v2, don't modify existing

## 🎮 Creating Controllers

### Step 1: Create the Controller Class

Create `api/controllers/orders_controller.py`:

```python
"""Orders REST API Controller"""
from typing import List, Optional

from fastapi import HTTPException
from classy_fastapi import get, post, put

from neuroglia.mvc import ControllerBase
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator

from api.dtos import CreateOrderDto, OrderDto, UpdateOrderStatusDto
from application.commands import (
    PlaceOrderCommand,
    StartCookingCommand,
    CompleteOrderCommand,
)
from application.queries import (
    GetOrderByIdQuery,
    GetActiveOrdersQuery,
    GetOrdersByStatusQuery,
)


class OrdersController(ControllerBase):
    """
    Pizza order management endpoints.

    ControllerBase provides:
    - Dependency injection (service_provider, mapper, mediator)
    - Helper methods (process, ok, created, not_found, etc.)
    - Consistent error handling
    - Auto-registration with framework
    """

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator
    ):
        """
        Dependencies injected by framework.

        All controllers get these three by default.
        """
        super().__init__(service_provider, mapper, mediator)
```

### Step 2: Add GET Endpoints

Continue in `api/controllers/orders_controller.py`:

```python
    @get(
        "/{order_id}",
        response_model=OrderDto,
        responses=ControllerBase.error_responses
    )
    async def get_order(self, order_id: str):
        """
        Get order details by ID.

        Returns:
            OrderDto: Order details

        Raises:
            404: Order not found
        """
        query = GetOrderByIdQuery(order_id=order_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get(
        "/",
        response_model=List[OrderDto],
        responses=ControllerBase.error_responses
    )
    async def get_orders(self, status: Optional[str] = None):
        """
        Get orders, optionally filtered by status.

        Query Parameters:
            status: Filter by order status (pending, confirmed, cooking, etc.)

        Returns:
            List[OrderDto]: List of orders
        """
        if status:
            query = GetOrdersByStatusQuery(status=status)
        else:
            query = GetActiveOrdersQuery()

        result = await self.mediator.execute_async(query)
        return self.process(result)
```

**Key points:**

- `@get` decorator from `classy_fastapi` (cleaner than FastAPI's `@app.get`)
- `response_model` enables automatic serialization and OpenAPI docs
- `self.process()` handles `OperationResult` and converts to HTTP responses
- Query parameters automatically parsed by FastAPI

### Step 3: Add POST Endpoint

```python
    @post(
        "/",
        response_model=OrderDto,
        status_code=201,
        responses=ControllerBase.error_responses
    )
    async def place_order(self, request: CreateOrderDto):
        """
        Place a new pizza order.

        Body:
            CreateOrderDto: Order details with pizzas

        Returns:
            OrderDto: Created order with ID

        Status Codes:
            201: Order created successfully
            400: Invalid request (validation failed)
        """
        # Map DTO to command
        command = self.mapper.map(request, PlaceOrderCommand)

        # Execute via mediator
        result = await self.mediator.execute_async(command)

        # Process result (converts OperationResult to HTTP response)
        return self.process(result)
```

**The flow:**

1. FastAPI validates `CreateOrderDto` (automatic)
2. Controller maps DTO → Command
3. Mediator routes to handler
4. Handler executes business logic
5. Handler returns `OperationResult`
6. `self.process()` converts to HTTP response:
   - Success (200) → Return data
   - Created (201) → Return data with Location header
   - Not Found (404) → HTTPException
   - Bad Request (400) → HTTPException with error details

### Step 4: Add PUT Endpoints

```python
    @put(
        "/{order_id}/cook",
        response_model=OrderDto,
        responses=ControllerBase.error_responses
    )
    async def start_cooking(self, order_id: str):
        """
        Start cooking an order.

        Path Parameters:
            order_id: Order to start cooking

        Returns:
            OrderDto: Updated order

        Status Codes:
            200: Order cooking started
            404: Order not found
            400: Invalid state transition
        """
        command = StartCookingCommand(order_id=order_id)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put(
        "/{order_id}/ready",
        response_model=OrderDto,
        responses=ControllerBase.error_responses
    )
    async def complete_order(self, order_id: str):
        """
        Mark order as ready for pickup/delivery.

        Path Parameters:
            order_id: Order to mark as ready

        Returns:
            OrderDto: Updated order
        """
        command = CompleteOrderCommand(order_id=order_id)
        result = await self.mediator.execute_async(command)
        return self.process(result)
```

## 🔍 Understanding `self.process()`

The `process()` method converts `OperationResult` to HTTP responses:

```python
# In handler
return self.created(order_dto)  # OperationResult with status 201

# In controller
return self.process(result)  # Converts to HTTP response

# Result:
# - Status code: 201
# - Body: order_dto serialized to JSON
# - Headers: Location: /api/orders/{id}
```

**Built-in result helpers:**

```python
# Success responses
self.ok(data)           # 200 OK
self.created(data)      # 201 Created
self.accepted(data)     # 202 Accepted
self.no_content()       # 204 No Content

# Error responses
self.bad_request(msg)           # 400 Bad Request
self.unauthorized(msg)          # 401 Unauthorized
self.forbidden(msg)             # 403 Forbidden
self.not_found(entity, id)      # 404 Not Found
self.conflict(msg)              # 409 Conflict
self.internal_server_error(msg) # 500 Internal Server Error
```

## 📖 Auto-Generated Documentation

FastAPI automatically generates OpenAPI docs. Start your app and visit:

- **Swagger UI**: http://localhost:8080/api/docs
- **ReDoc**: http://localhost:8080/api/redoc
- **OpenAPI JSON**: http://localhost:8080/api/openapi.json

Your endpoints appear with:

- **Request schemas** (CreateOrderDto)
- **Response schemas** (OrderDto)
- **Status codes** (201, 400, 404, etc.)
- **Descriptions** from docstrings
- **Try it out** feature for testing

## 🧪 Testing Controllers

Create `tests/api/controllers/test_orders_controller.py`:

```python
"""Tests for OrdersController"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock

from main import create_pizzeria_app


@pytest.fixture
def test_client():
    """Create test client with mocked dependencies"""
    app = create_pizzeria_app()
    return TestClient(app)


def test_get_order_not_found(test_client):
    """Test 404 when order doesn't exist"""
    response = test_client.get("/api/orders/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_place_order_success(test_client):
    """Test successful order creation"""
    order_data = {
        "customerName": "John Doe",
        "customerPhone": "555-1234",
        "pizzas": [
            {
                "name": "Margherita",
                "size": "large",
                "toppings": ["basil", "mozzarella"]
            }
        ]
    }

    response = test_client.post("/api/orders/", json=order_data)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["customerName"] == "John Doe"
    assert data["status"] == "confirmed"
    assert len(data["pizzas"]) == 1


def test_place_order_validation_error(test_client):
    """Test validation with invalid data"""
    invalid_data = {
        # Missing required customerName
        "customerPhone": "555-1234"
    }

    response = test_client.post("/api/orders/", json=invalid_data)

    assert response.status_code == 422  # Validation error
```

Run tests:

```bash
poetry run pytest tests/api/ -v
```

## 📝 Key Takeaways

1. **Controllers are thin**: Delegate to mediator, don't contain business logic
2. **DTOs define contracts**: Use CamelModel for case conversion
3. **Mediator pattern**: Controllers don't know about handlers
4. **Consistent responses**: Use OperationResult → self.process() flow
5. **Auto-documentation**: FastAPI generates OpenAPI docs automatically
6. **Testable**: Use TestClient for integration tests

## 🚀 What's Next?

In [Part 5: Events & Integration](mario-pizzeria-05-events.md), you'll learn:

- How to publish and handle domain events
- Event-driven architecture patterns
- Integrating with external systems via events
- Background event processing

---

**Previous:** [← Part 3: Commands & Queries](mario-pizzeria-03-cqrs.md) | **Next:** [Part 5: Events & Integration →](mario-pizzeria-05-events.md)
