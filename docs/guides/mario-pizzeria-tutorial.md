# 🍕 Mario's Pizzeria Tutorial

Build a complete [pizza ordering system](../mario-pizzeria.md) that demonstrates all of Neuroglia's features in a familiar, easy-to-understand context. This comprehensive tutorial covers clean architecture, CQRS, event-driven design, and web development.

!!! info "🎯 What You'll Build"
A complete pizzeria application with REST API, web UI, authentication, file-based persistence, and event-driven architecture.

## 📋 What You'll Build

By the end of this guide, you'll have a complete pizzeria application with:

- 🌐 **REST API** with automatic Swagger documentation
- 🎨 **Simple Web UI** for customers and kitchen staff
- 🔐 **OAuth Authentication** for secure access
- 💾 **File-based persistence** using the repository pattern
- 📡 **Event-driven architecture** with domain events
- 🏗️ **Clean Architecture** with CQRS and dependency injection

## ⚡ Quick Setup

### Installation

```bash
pip install neuroglia-python[web]
```

### Project Structure

The actual Mario's Pizzeria implementation follows clean architecture principles:

**Source**: [`samples/mario-pizzeria/`](https://github.com/bvandewe/pyneuro/tree/main/samples/mario-pizzeria)

```text
mario-pizzeria/
├── main.py                       # Application entry point with DI setup
├── api/
│   ├── controllers/             # REST API endpoints
│   │   ├── orders_controller.py  # Order management
│   │   ├── menu_controller.py    # Pizza menu
│   │   └── kitchen_controller.py # Kitchen operations
│   └── dtos/                    # Data Transfer Objects
│       ├── order_dtos.py        # Order request/response models
│       ├── menu_dtos.py         # Menu item models
│       └── kitchen_dtos.py      # Kitchen status models
├── application/
│   ├── commands/                # CQRS Command handlers
│   │   ├── place_order_command.py
│   │   ├── start_cooking_command.py
│   │   └── complete_order_command.py
│   ├── queries/                 # CQRS Query handlers
│   │   ├── get_order_by_id_query.py
│   │   ├── get_orders_by_status_query.py
│   │   └── get_active_orders_query.py
│   └── mapping/                 # AutoMapper profiles
│       └── profile.py           # Entity-DTO mappings
├── domain/
│   ├── entities/                # Domain entities
│   │   ├── pizza.py            # Pizza entity with pricing
│   │   ├── order.py            # Order aggregate root
│   │   ├── customer.py         # Customer entity
│   │   ├── kitchen.py          # Kitchen entity
│   │   └── enums.py            # Domain enumerations
│   ├── events/                  # Domain events
│   │   └── order_events.py     # Order lifecycle events
│   └── repositories/            # Repository interfaces
│       └── __init__.py         # Repository abstractions
├── integration/
│   └── repositories/           # Repository implementations
│       ├── file_order_repository.py    # File-based order storage
│       ├── file_pizza_repository.py    # File-based pizza storage
│       ├── file_customer_repository.py # File-based customer storage
│       └── file_kitchen_repository.py  # File-based kitchen storage
└── tests/                      # Test suite
    ├── test_api.py             # API integration tests
    ├── test_integration.py     # Full integration tests
    └── test_data/              # Test data storage
```

## 🏗️ Step 1: Domain Model

The domain entities demonstrate sophisticated business logic with real pricing calculations and type safety.

**[domain/entities/pizza.py](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/domain/entities/pizza.py)** <span class="code-line-ref">(lines 1-63)</span>

```python title="samples/mario-pizzeria/domain/entities/pizza.py" linenums="1"
"""Pizza entity for Mario's Pizzeria domain"""

from decimal import Decimal
from typing import Optional
from uuid import uuid4

from api.dtos import PizzaDto

from neuroglia.data.abstractions import Entity
from neuroglia.mapping.mapper import map_from, map_to

from .enums import PizzaSize


@map_from(PizzaDto)
@map_to(PizzaDto)
class Pizza(Entity[str]):
    """Pizza entity with pricing and toppings"""

    def __init__(self, name: str, base_price: Decimal, size: PizzaSize, description: Optional[str] = None):
        super().__init__()
        self.id = str(uuid4())
        self.name = name
        self.base_price = base_price
        self.size = size
        self.description = description or ""
        self.toppings: list[str] = []

    @property
    def size_multiplier(self) -> Decimal:
        """Get price multiplier based on pizza size"""
        multipliers = {
            PizzaSize.SMALL: Decimal("1.0"),
            PizzaSize.MEDIUM: Decimal("1.3"),
            PizzaSize.LARGE: Decimal("1.6"),
        }
        return multipliers[self.size]

    @property
    def topping_price(self) -> Decimal:
        """Calculate total price for all toppings"""
        return Decimal(str(len(self.toppings))) * Decimal("2.50")

    @property
    def total_price(self) -> Decimal:
        """Calculate total pizza price including size and toppings"""
        base_with_size = self.base_price * self.size_multiplier
        return base_with_size + self.topping_price

    def add_topping(self, topping: str) -> None:
        """Add a topping to the pizza"""
        if topping not in self.toppings:
            self.toppings.append(topping)

    def remove_topping(self, topping: str) -> None:
        """Remove a topping from the pizza"""
        if topping in self.toppings:
            self.toppings.remove(topping)
```

### Key Features

- **Size-based pricing**: Small (1.0x), Medium (1.3x), Large (1.6x) multipliers
- **Smart topping pricing**: $2.50 per topping with proper decimal handling
- **Auto-mapping decorators**: Seamless conversion to/from DTOs
- **Type safety**: Enum-based size validation with PizzaSize enum

**[domain/entities/order.py](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/domain/entities/order.py)** <span class="code-line-ref">(lines 1-106)</span>

```python title="samples/mario-pizzeria/domain/entities/order.py" linenums="1"
"""Order entity for Mario's Pizzeria domain"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from api.dtos import OrderDto

from neuroglia.data.abstractions import Entity
from neuroglia.mapping.mapper import map_from, map_to

from .enums import OrderStatus
from .pizza import Pizza


@map_from(OrderDto)
@map_to(OrderDto)
class Order(Entity[str]):
    """Order entity with pizzas and status management"""

    def __init__(self, customer_id: str, estimated_ready_time: Optional[datetime] = None):
        super().__init__()
        self.id = str(uuid4())
        self.customer_id = customer_id
        self.pizzas: list[Pizza] = []
        self.status = OrderStatus.PENDING
        self.order_time = datetime.now(timezone.utc)
        self.confirmed_time: Optional[datetime] = None
        self.cooking_started_time: Optional[datetime] = None
        self.actual_ready_time: Optional[datetime] = None
        self.estimated_ready_time = estimated_ready_time
        self.notes: Optional[str] = None

    @property
    def total_amount(self) -> Decimal:
        """Calculate total order amount"""
        return sum((pizza.total_price for pizza in self.pizzas), Decimal("0.00"))

    @property
    def pizza_count(self) -> int:
        """Get total number of pizzas in the order"""
        return len(self.pizzas)

    def add_pizza(self, pizza: Pizza) -> None:
        """Add a pizza to the order"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")
        self.pizzas.append(pizza)

    def confirm_order(self) -> None:
        """Confirm the order and set confirmed time"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be confirmed")

        if not self.pizzas:
            raise ValueError("Cannot confirm order without pizzas")

        self.status = OrderStatus.CONFIRMED
        self.confirmed_time = datetime.now(timezone.utc)

    def start_cooking(self) -> None:
        """Start cooking the order"""
        if self.status != OrderStatus.CONFIRMED:
            raise ValueError("Only confirmed orders can start cooking")

        self.status = OrderStatus.COOKING
        self.cooking_started_time = datetime.now(timezone.utc)

    def mark_ready(self) -> None:
        """Mark order as ready for pickup/delivery"""
        if self.status != OrderStatus.COOKING:
            raise ValueError("Only cooking orders can be marked ready")

        self.status = OrderStatus.READY
        self.actual_ready_time = datetime.now(timezone.utc)
```

### Key Features

- **Status management**: OrderStatus enum with PENDING → CONFIRMED → COOKING → READY workflow
- **Time tracking**: order_time, confirmed_time, cooking_started_time, actual_ready_time
- **Business validation**: Cannot modify confirmed orders, cannot confirm empty orders
- **Auto-mapping decorators**: Seamless conversion to/from DTOs
- **Computed properties**: Dynamic total_amount and pizza_count calculations

**OrderStatus Enum** ([enums.py](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/domain/entities/enums.py)):

```python title="samples/mario-pizzeria/domain/entities/enums.py" linenums="14"
class OrderStatus(Enum):
    """Order lifecycle statuses"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    COOKING = "cooking"
    READY = "ready"
```

Notice how the `Order` entity encapsulates the business logic around order management, including validation rules and state transitions.

**Domain Events** (optional extension):

```python title="Domain Events Example" linenums="1"
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from neuroglia.data.abstractions import DomainEvent

@dataclass
class OrderPlacedEvent(DomainEvent):
    """Event raised when a new order is placed"""
    order_id: str
    customer_name: str
    total_amount: Decimal
    estimated_ready_time: datetime

    def __post_init__(self):
        super().__init__(self.order_id)
```

## 🎯 Step 2: Commands and Queries

Neuroglia implements the CQRS (Command Query Responsibility Segregation) pattern, separating write operations (commands) from read operations (queries).

### Commands (Write Operations)

**[place_order_command.py](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/application/commands/place_order_command.py)** <span class="code-line-ref">(lines 17-29)</span>

```python title="samples/mario-pizzeria/application/commands/place_order_command.py" linenums="17"
@dataclass
@map_from(CreateOrderDto)
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    """Command to place a new pizza order"""

    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = None
    customer_email: Optional[str] = None
    pizzas: list[CreatePizzaDto] = field(default_factory=list)
    payment_method: str = "cash"
    notes: Optional[str] = None
```

**Command Handler Implementation** ([lines 31-95](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/application/commands/place_order_command.py#L31-L95)):

```python title="samples/mario-pizzeria/application/commands/place_order_command.py" linenums="31"
class PlaceOrderCommandHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    """Handler for placing new pizza orders"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: PlaceOrderCommand) -> OperationResult[OrderDto]:
        try:
            # First create or get customer
            customer = await self._create_or_get_customer(request)

            # Create order with customer_id
            order = Order(customer_id=customer.id)
            if request.notes:
                order.notes = request.notes

            # Add pizzas to order with dynamic pricing
            for pizza_item in request.pizzas:
                size = PizzaSize(pizza_item.size.lower())

                # Dynamic base pricing by pizza type
                base_price = Decimal("12.99")  # Default
                if pizza_item.name.lower() == "margherita":
                    base_price = Decimal("12.99")
                elif pizza_item.name.lower() == "pepperoni":
                    base_price = Decimal("14.99")
                elif pizza_item.name.lower() == "supreme":
                    base_price = Decimal("17.99")

                pizza = Pizza(name=pizza_item.name, base_price=base_price, size=size)

                # Add toppings
                for topping in pizza_item.toppings:
                    pizza.add_topping(topping)

                order.add_pizza(pizza)

            # Validate and confirm order
            if not order.pizzas:
                return self.bad_request("Order must contain at least one pizza")

            order.confirm_order()  # Raises domain event
            await self.order_repository.add_async(order)

            return self.created(self._build_order_dto(order, customer))
```

### Queries (Read Operations)

**[get_order_by_id_query.py](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/application/queries/get_order_by_id_query.py)** <span class="code-line-ref">(lines 13-17)</span>

```python title="samples/mario-pizzeria/application/queries/get_order_by_id_query.py" linenums="13"
@dataclass
class GetOrderByIdQuery(Query[OperationResult[OrderDto]]):
    """Query to get an order by ID"""

    order_id: str
```

**Query Handler Implementation** ([lines 20-63](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/application/queries/get_order_by_id_query.py#L20-L63)):

```python title="samples/mario-pizzeria/application/queries/get_order_by_id_query.py" linenums="20"
class GetOrderByIdQueryHandler(QueryHandler[GetOrderByIdQuery, OperationResult[OrderDto]]):
    """Handler for getting an order by ID"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: GetOrderByIdQuery) -> OperationResult[OrderDto]:
        try:
            order = await self.order_repository.get_async(request.order_id)
            if not order:
                return self.not_found("Order", request.order_id)

            # Get customer details
            customer = await self.customer_repository.get_async(order.customer_id)

            # Create OrderDto with customer information
            order_dto = OrderDto(
                id=order.id,
                customer_name=customer.name if customer else "Unknown",
                customer_phone=customer.phone if customer else "Unknown",
                customer_address=customer.address if customer else "Unknown",
                pizzas=[self.mapper.map(pizza, PizzaDto) for pizza in order.pizzas],
                status=order.status.value,
                order_time=order.order_time,
                confirmed_time=order.confirmed_time,
                cooking_started_time=order.cooking_started_time,
                actual_ready_time=order.actual_ready_time,
                estimated_ready_time=order.estimated_ready_time,
                total_amount=order.total_amount,
                notes=order.notes,
            )

            return self.ok(order_dto)
        except Exception as e:
            return self.internal_server_error(f"Failed to get order: {str(e)}")
```

### Key CQRS Features

- **Command/Query Separation**: Clear distinction between write (commands) and read (queries) operations
- **Auto-mapping**: @map_from decorators for seamless DTO conversion
- **Repository Pattern**: Abstracted data access through IOrderRepository and ICustomerRepository
- **Business Logic**: Domain validation and business rules in command handlers
- **Error Handling**: Comprehensive error handling with OperationResult pattern

## 💾 Step 3: File-Based Repository

**[file_order_repository.py](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/integration/repositories/file_order_repository.py)** <span class="code-line-ref">(lines 1-37)</span>

```python title="samples/mario-pizzeria/integration/repositories/file_order_repository.py" linenums="1"
"""File-based implementation of order repository using generic FileSystemRepository"""

from datetime import datetime

from domain.entities import Order, OrderStatus
from domain.repositories import IOrderRepository

from neuroglia.data.infrastructure.filesystem import FileSystemRepository


class FileOrderRepository(FileSystemRepository[Order, str], IOrderRepository):
    """File-based implementation of order repository using generic FileSystemRepository"""

    def __init__(self, data_directory: str = "data"):
        super().__init__(data_directory=data_directory, entity_type=Order, key_type=str)

    async def get_by_customer_phone_async(self, phone: str) -> list[Order]:
        """Get all orders for a customer by phone number"""
        # Note: This would require a relationship lookup in a real implementation
        # For now, we'll return empty list as Order entity doesn't directly store phone
        return []

    async def get_orders_by_status_async(self, status: OrderStatus) -> list[Order]:
        """Get all orders with a specific status"""
        all_orders = await self.get_all_async()
        return [order for order in all_orders if order.status == status]

    async def get_orders_by_date_range_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """Get orders within a date range"""
        all_orders = await self.get_all_async()
        return [order for order in all_orders if start_date <= order.created_at <= end_date]

    async def get_active_orders_async(self) -> list[Order]:
        """Get all active orders (not delivered or cancelled)"""
        all_orders = await self.get_all_async()
        active_statuses = {OrderStatus.CONFIRMED, OrderStatus.COOKING}
        return [order for order in all_orders if order.status in active_statuses]
```

### Key Repository Features

- **Generic Base Class**: Inherits from `FileSystemRepository[Order, str]` for common CRUD operations
- **Domain Interface**: Implements `IOrderRepository` for business-specific methods
- **Status Filtering**: `get_orders_by_status_async()` for filtering by OrderStatus enum
- **Date Range Queries**: `get_orders_by_date_range_async()` for reporting functionality
- **Business Logic**: `get_active_orders_async()` returns orders in CONFIRMED or COOKING status
- **JSON Persistence**: Built-in serialization through FileSystemRepository base class
- **Type Safety**: Strongly typed with Order entity and string keys

## 🌐 Step 4: REST API Controllers

**[orders_controller.py](https://github.com/bvandewe/pyneuro/blob/main/samples/mario-pizzeria/api/controllers/orders_controller.py)** <span class="code-line-ref">(lines 1-83)</span>

```python title="samples/mario-pizzeria/api/controllers/orders_controller.py" linenums="1"
from typing import List, Optional
from fastapi import HTTPException

from neuroglia.mvc import ControllerBase
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from classy_fastapi import get, post, put

from api.dtos import (
    OrderDto,
    CreateOrderDto,
    UpdateOrderStatusDto,
)
from application.commands import PlaceOrderCommand, StartCookingCommand, CompleteOrderCommand
from application.queries import (
    GetOrderByIdQuery,
    GetOrdersByStatusQuery,
    GetActiveOrdersQuery,
)


class OrdersController(ControllerBase):
    """Mario's pizza order management endpoints"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/{order_id}", response_model=OrderDto, responses=ControllerBase.error_responses)
    async def get_order(self, order_id: str):
        """Get order details by ID"""
        query = GetOrderByIdQuery(order_id=order_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/", response_model=List[OrderDto], responses=ControllerBase.error_responses)
    async def get_orders(self, status: Optional[str] = None):
        """Get orders, optionally filtered by status"""
        if status:
            query = GetOrdersByStatusQuery(status=status)
        else:
            query = GetActiveOrdersQuery()

        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/", response_model=OrderDto, status_code=201, responses=ControllerBase.error_responses)
    async def place_order(self, request: CreateOrderDto):
        """Place a new pizza order"""
        command = self.mapper.map(request, PlaceOrderCommand)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{order_id}/cook", response_model=OrderDto, responses=ControllerBase.error_responses)
    async def start_cooking(self, order_id: str):
        """Start cooking an order"""
        command = StartCookingCommand(order_id=order_id)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{order_id}/ready", response_model=OrderDto, responses=ControllerBase.error_responses)
    async def complete_order(self, order_id: str):
        """Mark order as ready for pickup/delivery"""
        command = CompleteOrderCommand(order_id=order_id)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{order_id}/status", response_model=OrderDto, responses=ControllerBase.error_responses)
    async def update_order_status(self, order_id: str, request: UpdateOrderStatusDto):
        """Update order status (general endpoint)"""
        # Route to appropriate command based on status
        if request.status.lower() == "cooking":
            command = StartCookingCommand(order_id=order_id)
        elif request.status.lower() == "ready":
            command = CompleteOrderCommand(order_id=order_id)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported status transition: {request.status}"
            )

        result = await self.mediator.execute_async(command)
        return self.process(result)
```

### Key Controller Features

- **Full CRUD Operations**: Complete order lifecycle management from creation to completion
- **RESTful Design**: Proper HTTP methods (GET, POST, PUT) and status codes (200, 201, 400, 404)
- **Mediator Pattern**: All business logic delegated to command/query handlers
- **Type Safety**: Strong typing with Pydantic models for requests and responses
- **Error Handling**: Consistent error responses using ControllerBase.error_responses
- **Status Management**: Multiple endpoints for different order status transitions
- **Auto-mapping**: Seamless DTO to command conversion using mapper.map()
- **Clean Architecture**: Controllers are thin orchestrators, business logic stays in handlers

## 🔐 Step 5: OAuth Authentication

**src/infrastructure/auth.py**

```python
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from neuroglia.core import OperationResult

# Simple OAuth configuration
OAUTH_SCOPES = {
    "orders:read": "Read order information",
    "orders:write": "Create and modify orders",
    "kitchen:manage": "Manage kitchen operations",
    "admin": "Full administrative access"
}

# Simple token validation (in production, use proper OAuth provider)
VALID_TOKENS = {
    "customer_token": {"user": "customer", "scopes": ["orders:read", "orders:write"]},
    "staff_token": {"user": "kitchen_staff", "scopes": ["orders:read", "kitchen:manage"]},
    "admin_token": {"user": "admin", "scopes": ["admin"]}
}

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate token and return user info"""
    token = credentials.credentials

    if token not in VALID_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return VALID_TOKENS[token]

def require_scope(required_scope: str):
    """Decorator to require specific OAuth scope"""
    def check_scope(current_user: dict = Depends(get_current_user)):
        user_scopes = current_user.get("scopes", [])
        if required_scope not in user_scopes and "admin" not in user_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        return current_user
    return check_scope
```

## 🎨 Step 6: Simple Web UI

**src/web/static/index.html**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mario's Pizzeria</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
      }
      .pizza-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
      }
      .order-form {
        background: #f5f5f5;
        padding: 20px;
        border-radius: 8px;
        margin: 20px 0;
      }
      button {
        background: #e74c3c;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
      }
      button:hover {
        background: #c0392b;
      }
      input,
      select {
        padding: 8px;
        margin: 5px;
        border: 1px solid #ddd;
        border-radius: 4px;
      }
    </style>
  </head>
  <body>
    <h1>🍕 Welcome to Mario's Pizzeria</h1>

    <div id="menu-section">
      <h2>Our Menu</h2>
      <div id="menu-items"></div>
    </div>

    <div class="order-form">
      <h2>Place Your Order</h2>
      <form id="order-form">
        <div>
          <input type="text" id="customer-name" placeholder="Your Name" required />
          <input type="tel" id="customer-phone" placeholder="Phone Number" required />
        </div>
        <div id="pizza-selection"></div>
        <button type="submit">Place Order</button>
      </form>
    </div>

    <div id="order-status" style="display: none;">
      <h2>Order Status</h2>
      <div id="status-details"></div>
    </div>

    <script>
      // Load menu on page load
      document.addEventListener("DOMContentLoaded", loadMenu);

      async function loadMenu() {
        try {
          const response = await fetch("/api/menu");
          const menu = await response.json();
          displayMenu(menu);
        } catch (error) {
          console.error("Failed to load menu:", error);
        }
      }

      function displayMenu(menu) {
        const menuContainer = document.getElementById("menu-items");
        menuContainer.innerHTML = menu
          .map(
            pizza => `
                <div class="pizza-card">
                    <h3>${pizza.name}</h3>
                    <p>Base Price: $${pizza.base_price}</p>
                    <p>Prep Time: ${pizza.preparation_time_minutes} minutes</p>
                    <button onclick="addToOrder('${pizza.id}', '${pizza.name}')">Add to Order</button>
                </div>
            `
          )
          .join("");
      }

      function addToOrder(pizzaId, pizzaName) {
        const selection = document.getElementById("pizza-selection");
        selection.innerHTML += `
                <div class="pizza-selection">
                    <span>${pizzaName}</span>
                    <select name="size">
                        <option value="small">Small</option>
                        <option value="medium">Medium</option>
                        <option value="large">Large</option>
                    </select>
                    <select name="toppings" multiple>
                        <option value="pepperoni">Pepperoni</option>
                        <option value="mushrooms">Mushrooms</option>
                        <option value="bell_peppers">Bell Peppers</option>
                    </select>
                    <input type="hidden" name="pizza_id" value="${pizzaId}">
                </div>
            `;
      }

      document.getElementById("order-form").addEventListener("submit", async e => {
        e.preventDefault();

        const formData = new FormData(e.target);
        const order = {
          customer_name: formData.get("customer-name"),
          customer_phone: formData.get("customer-phone"),
          pizza_items: Array.from(document.querySelectorAll(".pizza-selection")).map(item => ({
            pizza_id: item.querySelector('[name="pizza_id"]').value,
            size: item.querySelector('[name="size"]').value,
            toppings: Array.from(item.querySelectorAll('[name="toppings"] option:checked')).map(opt => opt.value),
          })),
        };

        try {
          const response = await fetch("/api/orders", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(order),
          });

          const result = await response.json();
          showOrderStatus(result);
        } catch (error) {
          alert("Failed to place order: " + error.message);
        }
      });

      function showOrderStatus(order) {
        document.getElementById("order-status").style.display = "block";
        document.getElementById("status-details").innerHTML = `
                <p><strong>Order ID:</strong> ${order.order_id}</p>
                <p><strong>Total:</strong> $${order.total_amount}</p>
                <p><strong>Estimated Ready Time:</strong> ${new Date(
                  order.estimated_ready_time
                ).toLocaleTimeString()}</p>
            `;
      }
    </script>
  </body>
</html>
```

## 🚀 Step 7: Application Setup

The main application file demonstrates sophisticated multi-app architecture with dependency injection configuration.

**[main.py](https://github.com/neuroglia-io/python-framework/blob/main/samples/mario-pizzeria/main.py)** <span class="code-line-ref">(lines 1-226)</span>

```python title="samples/mario-pizzeria/main.py" linenums="1"
#!/usr/bin/env python3
"""
Mario's Pizzeria - Main Application Entry Point

This is the complete sample application demonstrating all major Neuroglia framework features.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Set up debug logging early
logging.basicConfig(level=logging.DEBUG)

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Domain repository interfaces
from domain.repositories import (
    ICustomerRepository,
    IKitchenRepository,
    IOrderRepository,
    IPizzaRepository,
)
from integration.repositories import (
    FileCustomerRepository,
    FileKitchenRepository,
    FileOrderRepository,
    FilePizzaRepository,
)

# Framework imports (must be after path manipulation)
from neuroglia.hosting.enhanced_web_application_builder import (
    EnhancedWebApplicationBuilder,
)
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator


def create_pizzeria_app(data_dir: Optional[str] = None, port: int = 8000):
    """
    Create Mario's Pizzeria application with multi-app architecture.

    Creates separate apps for:
    - API backend (/api prefix)
    - Future UI frontend (/ prefix)
    """
    # Determine data directory
    data_dir_path = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    data_dir_path.mkdir(exist_ok=True)

    print(f"💾 Data stored in: {data_dir_path}")

    # Create enhanced web application builder
    builder = EnhancedWebApplicationBuilder()

    # Register repositories with file-based implementations
    builder.services.add_singleton(
        IPizzaRepository,
        implementation_factory=lambda _: FilePizzaRepository(str(data_dir_path / "menu")),
    )
    builder.services.add_singleton(
        ICustomerRepository,
        implementation_factory=lambda _: FileCustomerRepository(str(data_dir_path / "customers")),
    )
    builder.services.add_singleton(
        IOrderRepository,
        implementation_factory=lambda _: FileOrderRepository(str(data_dir_path / "orders")),
    )
    builder.services.add_singleton(
        IKitchenRepository,
        implementation_factory=lambda _: FileKitchenRepository(str(data_dir_path / "kitchen")),
    )

    # Configure mediator with auto-discovery from command and query modules
    Mediator.configure(builder, ["application.commands", "application.queries"])

    # Configure auto-mapper with custom profile
    Mapper.configure(builder, ["application.mapping", "api.dtos", "domain.entities"])

    # Configure JSON serialization with type discovery
    from neuroglia.serialization.json import JsonSerializer

    # Configure JsonSerializer with domain modules for enum discovery
    JsonSerializer.configure(
        builder,
        type_modules=[
            "domain.entities.enums",  # Mario Pizzeria enum types
            "domain.entities",  # Also scan entities module for embedded enums
        ],
    )

    # Build the service provider (not the full app yet)
    service_provider = builder.services.build()

    # Create the main FastAPI app directly
    from fastapi import FastAPI

    app = FastAPI(
        title="Mario's Pizzeria",
        description="Complete pizza ordering and management system",
        version="1.0.0",
        debug=True,
    )

    # Make DI services available to the app
    app.state.services = service_provider

    # Create separate API app for backend REST API
    api_app = FastAPI(
        title="Mario's Pizzeria API",
        description="Pizza ordering and management API",
        version="1.0.0",
        docs_url="/docs",
        debug=True,
    )

    # IMPORTANT: Make services available to API app as well
    api_app.state.services = service_provider

    # Register API controllers to the API app
    builder.add_controllers(["api.controllers"], app=api_app)

    # Add exception handling to API app
    builder.add_exception_handling(api_app)

    # Mount the apps
    app.mount("/api", api_app, name="api")
    app.mount("/ui", ui_app, name="ui")

    return app
```

### Key Implementation Features

**Multi-App Architecture** <span class="code-line-ref">(lines 102-125)</span>

The application uses a sophisticated multi-app setup:

- **Main App**: Root FastAPI application with welcome endpoint
- **API App**: Dedicated backend API mounted at `/api` with Swagger documentation
- **UI App**: Future frontend application mounted at `/ui`

**Repository Registration Pattern** <span class="code-line-ref">(lines 64-82)</span>

Uses interface-based dependency injection with file-based implementations:

```python title="Repository Registration Pattern" linenums="64"
builder.services.add_singleton(
    IPizzaRepository,
    implementation_factory=lambda _: FilePizzaRepository(str(data_dir_path / "menu")),
)
```

**Auto-Discovery Configuration** <span class="code-line-ref">(lines 84-98)</span>

Framework components use module scanning for automatic registration:

```python title="Auto-Discovery Setup" linenums="84"
# Configure mediator with auto-discovery from command and query modules
Mediator.configure(builder, ["application.commands", "application.queries"])

# Configure auto-mapper with custom profile
Mapper.configure(builder, ["application.mapping", "api.dtos", "domain.entities"])

# Configure JsonSerializer with domain modules for enum discovery
JsonSerializer.configure(
    builder,
    type_modules=[
        "domain.entities.enums",  # Mario Pizzeria enum types
        "domain.entities",  # Also scan entities module for embedded enums
    ],
)
```

## 🎯 Running the Application

The main entry point provides comprehensive application bootstrapping and startup logic:

**[Application Startup](https://github.com/neuroglia-io/python-framework/blob/main/samples/mario-pizzeria/main.py)** <span class="code-line-ref">(lines 198-226)</span>

```python title="Application Entry Point" linenums="198"
def main():
    """Main entry point when running as a script"""
    import uvicorn

    # Parse command line arguments
    port = 8000
    host = "127.0.0.1"
    data_dir = None

    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
            elif arg == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
            elif arg == "--data-dir" and i + 1 < len(sys.argv):
                data_dir = sys.argv[i + 1]

    # Create the application
    app = create_pizzeria_app(data_dir=data_dir, port=port)

    print(f"🍕 Starting Mario's Pizzeria on http://{host}:{port}")
    print(f"📖 API Documentation available at http://{host}:{port}/api/docs")
    print(f"🌐 UI will be available at http://{host}:{port}/ui (coming soon)")

    # Run the server
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
```

## 🎉 You're Done

Run your pizzeria:

```bash
cd samples/mario-pizzeria
python main.py
```

Visit your application:

- **Web UI**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Endpoints**: [http://localhost:8000/api](http://localhost:8000/api)

## 🔍 What You've Built

- ✅ **Complete Web Application** with UI and API
- ✅ **Clean Architecture** with domain, application, and infrastructure layers
- ✅ **CQRS Pattern** with commands and queries
- ✅ **Event-Driven Design** with domain events
- ✅ **File-Based Persistence** using the repository pattern
- ✅ **OAuth Authentication** for secure endpoints
- ✅ **Enhanced Web Application Builder** with multi-app support
- ✅ **Automatic API Documentation** with Swagger UI

## 🚀 Next Steps

Now that you've built a complete application, explore advanced Neuroglia features:

### 🏛️ Architecture Deep Dives

- Clean architecture principles and layer separation
- **[CQRS & Mediation](../patterns/cqrs.md)** - Advanced command/query patterns and pipeline behaviors
- **[Dependency Injection](../patterns/dependency-injection.md)** - Advanced DI patterns and service lifetimes

### 🚀 Advanced Features

- **[Event Sourcing](../patterns/event-sourcing.md)** - Complete event-driven architecture with event stores
- **[Data Access](../features/data-access.md)** - MongoDB and other persistence options beyond file storage
- **[MVC Controllers](../features/mvc-controllers.md)** - Advanced controller patterns and API design

### 📋 Sample Applications

- **[OpenBank Sample](../samples/openbank.md)** - Banking domain with event sourcing
- **[API Gateway Sample](../samples/api_gateway.md)** - Microservice gateway patterns
- **[Desktop Controller Sample](../samples/desktop_controller.md)** - Background services and system integration

## 🔗 Related Documentation

- **[⚡ 3-Minute Bootstrap](3-min-bootstrap.md)** - Quick hello world setup
- **[🛠️ Local Development Setup](local-development.md)** - Complete development environment
- **[🎯 Getting Started Overview](../getting-started.md)** - Choose your learning path

---

!!! success "🎉 Congratulations!"
You've built a complete, production-ready application using Neuroglia! All other documentation examples use this same pizzeria domain for consistency - you'll feel right at home exploring advanced features.
