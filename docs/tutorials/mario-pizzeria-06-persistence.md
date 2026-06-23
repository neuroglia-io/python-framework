# Part 6: Persistence & Repositories

**Time: 45 minutes** | **Prerequisites: [Part 5](mario-pizzeria-05-events.md)**

In this tutorial, you'll implement data persistence using the Repository pattern with MongoDB. You'll learn how to abstract data access and maintain clean separation between domain and infrastructure.

## 🎯 What You'll Learn

- The Repository pattern and why it matters
- MongoDB integration with Motor (async driver)
- Implementing repositories for aggregates
- Data persistence with repository pattern and automatic event publishing
- Testing data access layers

## 💾 Understanding the Repository Pattern

### The Problem

Without repositories, domain logic is polluted with database code:

```python
# ❌ Domain entity knows about MongoDB
class Order(AggregateRoot):
    async def save(self):
        collection = mongo_client.db.orders
        await collection.insert_one(self.__dict__)  # 😱
```

**Problems:**

- Domain depends on infrastructure (MongoDB)
- Can't test without database
- Can't swap database implementations
- Violates clean architecture

### The Solution: Repository Pattern

Repositories **abstract data access** behind interfaces:

```
┌──────────────┐
│   Domain     │  Uses interface
│   (Order)    │──────────┐
└──────────────┘          │
                          ▼
                 ┌────────────────┐
                 │  IOrderRepo    │  (interface)
                 │  - get()       │
                 │  - add()       │
                 │  - list()      │
                 └────────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│MongoOrderRepo│  │  FileRepo    │  │ InMemoryRepo │
│              │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Benefits:**

- **Testability**: Use in-memory repo for tests
- **Flexibility**: Swap implementations without changing domain
- **Clean Architecture**: Domain doesn't depend on infrastructure
- **Consistency**: Standard interface for all data access

## 📝 Defining Repository Interfaces

### Step 1: Create Repository Interface

Create `domain/repositories/__init__.py`:

```python
"""Repository interfaces for domain entities"""
from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities import Order


class IOrderRepository(ABC):
    """
    Interface for Order persistence.

    Domain defines the contract, infrastructure implements it.
    """

    @abstractmethod
    async def get_async(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        pass

    @abstractmethod
    async def add_async(self, order: Order) -> None:
        """Add new order"""
        pass

    @abstractmethod
    async def update_async(self, order: Order) -> None:
        """Update existing order"""
        pass

    @abstractmethod
    async def delete_async(self, order_id: str) -> None:
        """Delete order"""
        pass

    @abstractmethod
    async def list_async(self) -> List[Order]:
        """Get all orders"""
        pass

    @abstractmethod
    async def find_by_status_async(self, status: str) -> List[Order]:
        """Find orders by status"""
        pass
```

**Key points:**

- **Interface only**: No implementation details
- **Domain types**: Works with `Order` entities, not dicts/documents
- **Async**: All methods async for non-blocking I/O
- **Business queries**: `find_by_status_async` reflects business needs

## 🗄️ MongoDB Implementation

### Step 1: Install Motor

Motor is the async MongoDB driver:

```bash
poetry add motor pymongo
```

### Step 2: Implement MongoDB Repository

Create `integration/repositories/mongo_order_repository.py`:

```python
"""MongoDB implementation of IOrderRepository"""
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from domain.entities import Order, OrderStatus
from domain.repositories import IOrderRepository
from neuroglia.data.infrastructure.mongo import MotorRepository


class MongoOrderRepository(
    MotorRepository[Order, str],
    IOrderRepository
):
    """
    MongoDB implementation of order repository.

    MotorRepository provides:
    - Automatic serialization/deserialization
    - CRUD operations
    - Query helpers
    """

    def __init__(self, collection: AsyncIOMotorCollection):
        """
        Initialize with MongoDB collection.

        Collection is injected by DI container.
        """
        super().__init__(collection, Order, str)

    async def find_by_status_async(
        self,
        status: str
    ) -> List[Order]:
        """Find orders by status"""
        # Convert status string to enum
        order_status = OrderStatus(status.lower())

        # Query MongoDB
        cursor = self.collection.find({"state.status": order_status.value})

        # Deserialize to Order entities
        orders = []
        async for doc in cursor:
            order = await self._deserialize_async(doc)
            orders.append(order)

        return orders

    async def find_active_orders_async(self) -> List[Order]:
        """Find orders that are not delivered or cancelled"""
        active_statuses = [
            OrderStatus.PENDING.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.COOKING.value,
            OrderStatus.READY.value,
            OrderStatus.DELIVERING.value,
        ]

        cursor = self.collection.find({
            "state.status": {"$in": active_statuses}
        })

        orders = []
        async for doc in cursor:
            order = await self._deserialize_async(doc)
            orders.append(order)

        return orders
```

**What MotorRepository provides:**

- `get_async(id)`: Get by ID
- `add_async(entity)`: Insert new entity
- `update_async(entity)`: Update existing entity
- `delete_async(id)`: Delete by ID
- `list_async()`: Get all entities
- Automatic serialization using JsonSerializer
- Automatic deserialization to domain entities

### Step 3: Configure MongoDB Connection

In `main.py`:

```python
from neuroglia.data.infrastructure.mongo import MotorRepository
from domain.entities import Order, Customer, Pizza
from domain.repositories import (
    IOrderRepository,
    ICustomerRepository,
    IPizzaRepository
)

def create_pizzeria_app():
    builder = WebApplicationBuilder()

    # ... other configuration ...

    # Configure MongoDB repositories
    MotorRepository.configure(
        builder,
        entity_type=Order,
        key_type=str,
        database_name="mario_pizzeria",
        collection_name="orders",
        domain_repository_type=IOrderRepository,
    )

    MotorRepository.configure(
        builder,
        entity_type=Customer,
        key_type=str,
        database_name="mario_pizzeria",
        collection_name="customers",
        domain_repository_type=ICustomerRepository,
    )

    return builder.build_app_with_lifespan(...)
```

Passing `domain_repository_type` automatically binds your domain-level repository interface
to the scoped `MotorRepository` instance. This keeps handlers decoupled from the infrastructure
layer while avoiding manual service registration boilerplate.

### Using Custom Repository Implementations

If you need domain-specific query methods beyond basic CRUD, create a custom repository
that extends `MotorRepository` and register it using the `implementation_type` parameter:

```python
# Custom repository with domain-specific queries
class MongoOrderRepository(MotorRepository[Order, str]):
    """Custom MongoDB repository with order-specific queries."""

    async def get_by_customer_phone_async(self, phone: str) -> List[Order]:
        """Get orders by customer phone number."""
        return await self.find_async({"customer_phone": phone})

    async def get_by_status_async(self, status: str) -> List[Order]:
        """Get orders by status for kitchen management."""
        return await self.find_async({"status": status})

# Single-line registration with custom implementation
MotorRepository.configure(
    builder,
    entity_type=Order,
    key_type=str,
    database_name="mario_pizzeria",
    collection_name="orders",
    domain_repository_type=IOrderRepository,
    implementation_type=MongoOrderRepository,  # Custom implementation
)
```

When `implementation_type` is provided, your domain interface resolves to the custom
repository class, giving you access to specialized query methods while maintaining
clean architecture boundaries.

`MotorRepository.configure` now resolves the `Mediator` for you, so aggregate domain events
are published automatically once your handlers persist state.

**Configuration does:**

1. Creates MongoDB connection pool
2. Sets up collection access
3. Registers serialization/deserialization
4. Binds interface to implementation in DI

### Step 4: Environment Configuration

Create `.env` file:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=mario_pizzeria

# Or for MongoDB Atlas
# MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/

# Application Settings
LOG_LEVEL=INFO
```

Load in `application/settings.py`:

```python
"""Application settings"""
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application configuration"""

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "mario_pizzeria"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


# Singleton instance
app_settings = AppSettings()
```

## 🔄 Transaction Management with Repository Pattern

The **Command Handler serves as the transaction boundary**, and the **Repository** coordinates persistence with automatic event publishing.

### How Repository-Based Transactions Work

```python
# In command handler
async def handle_async(self, command: PlaceOrderCommand):
    # 1️⃣ Create order (in memory)
    order = Order(customer_id=command.customer_id)
    order.add_order_item(item)
    order.confirm_order()  # Raises OrderConfirmedEvent internally

    # 2️⃣ Save changes via repository (transaction boundary)
    await self.order_repository.add_async(order)

    # Repository does:
    # - Saves order state to database
    # - Gets uncommitted events from order
    # - Publishes events to event bus
    # - Clears uncommitted events from order
    # - All in a transactional scope!
```

**Benefits:**

- **Atomic**: State changes and event publishing succeed or fail together
- **Event consistency**: Events only published if database save succeeds
- **Automatic**: No manual event publishing needed
- **Simple**: Command handler IS the transaction boundary

### Configure Repositories

In `main.py`:

```python
from neuroglia.data.infrastructure.mongo import MongoRepository
from domain.repositories import IOrderRepository

# Configure repositories with automatic event publishing
services.add_scoped(IOrderRepository, MongoOrderRepository)

# Repository automatically handles:
# - State persistence
# - Event publishing
# - Transaction coordination
```

````

## 🧪 Testing Repositories

### Option 1: In-Memory Repository (Unit Tests)

Create `tests/fixtures/in_memory_order_repository.py`:

```python
"""In-memory repository for testing"""
from typing import Dict, List, Optional

from domain.entities import Order, OrderStatus
from domain.repositories import IOrderRepository


class InMemoryOrderRepository(IOrderRepository):
    """In-memory implementation for testing"""

    def __init__(self):
        self._orders: Dict[str, Order] = {}

    async def get_async(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    async def add_async(self, order: Order) -> None:
        self._orders[order.id()] = order

    async def update_async(self, order: Order) -> None:
        self._orders[order.id()] = order

    async def delete_async(self, order_id: str) -> None:
        self._orders.pop(order_id, None)

    async def list_async(self) -> List[Order]:
        return list(self._orders.values())

    async def find_by_status_async(self, status: str) -> List[Order]:
        order_status = OrderStatus(status.lower())
        return [
            o for o in self._orders.values()
            if o.state.status == order_status
        ]
````

Use in tests:

```python
@pytest.fixture
def order_repository():
    return InMemoryOrderRepository()


@pytest.mark.asyncio
async def test_place_order_handler(order_repository):
    """Test handler with in-memory repository"""
    handler = PlaceOrderHandler(
        order_repository=order_repository,
        # ... other mocks
    )

    command = PlaceOrderCommand(...)
    result = await handler.handle_async(command)

    assert result.is_success

    # Verify order was saved
    orders = await order_repository.list_async()
    assert len(orders) == 1
```

### Option 2: Integration Tests with MongoDB

Create `tests/integration/test_mongo_order_repository.py`:

```python
"""Integration tests for MongoDB repository"""
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from domain.entities import Order, OrderItem, PizzaSize
from integration.repositories import MongoOrderRepository
from decimal import Decimal


@pytest.fixture
async def mongo_client():
    """Create test MongoDB client"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    yield client

    # Cleanup
    await client.mario_pizzeria_test.orders.delete_many({})
    client.close()


@pytest.fixture
async def order_repository(mongo_client):
    """Create repository with test collection"""
    collection = mongo_client.mario_pizzeria_test.orders
    return MongoOrderRepository(collection)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_crud_operations(order_repository):
    """Test complete CRUD workflow"""
    # Create
    order = Order(customer_id="cust-123")
    item = OrderItem.create(
        name="Margherita",
        size=PizzaSize.LARGE,
        quantity=1,
        unit_price=Decimal("12.99")
    )
    order.add_order_item(item)
    order.confirm_order()

    await order_repository.add_async(order)

    # Read
    retrieved = await order_repository.get_async(order.id())
    assert retrieved is not None
    assert retrieved.state.customer_id == "cust-123"
    assert retrieved.pizza_count == 1

    # Update
    retrieved.start_cooking(user_id="chef-1", user_name="Mario")
    await order_repository.update_async(retrieved)

    # Verify update
    updated = await order_repository.get_async(order.id())
    assert updated.state.status == OrderStatus.COOKING

    # Delete
    await order_repository.delete_async(order.id())
    deleted = await order_repository.get_async(order.id())
    assert deleted is None
```

Run integration tests:

```bash
# Start MongoDB
docker run -d -p 27017:27017 mongo:latest

# Run tests
poetry run pytest tests/integration/ -m integration -v
```

## 📝 Key Takeaways

1. **Repository Pattern**: Abstracts data access behind interfaces
2. **Clean Architecture**: Domain doesn't depend on infrastructure
3. **Motor**: Async MongoDB driver for Python
4. **MotorRepository**: Framework base class with CRUD operations
5. **Repository Pattern**: Handles persistence and automatic event publishing
6. **Testing**: Use in-memory repos for unit tests, real DB for integration tests

## 🚀 What's Next?

In [Part 7: Authentication & Authorization](mario-pizzeria-07-auth.md), you'll learn:

- OAuth2 and JWT authentication
- Keycloak integration
- Role-based access control (RBAC)
- Protecting API endpoints

---

**Previous:** [← Part 5: Events & Integration](mario-pizzeria-05-events.md) | **Next:** [Part 7: Authentication & Authorization →](mario-pizzeria-07-auth.md)
