# Repository Pattern

**Time to read: 11 minutes**

The Repository pattern provides a **collection-like interface** for accessing domain objects. It abstracts data access, hiding whether data comes from a database, API, or memory.

## ❌ The Problem: Database Code Everywhere

Without repositories, database code leaks into business logic:

```python
# ❌ Handler knows about MongoDB
class PlaceOrderHandler:
    def __init__(self, mongo_client: MongoClient):
        self.db = mongo_client.orders_db

    async def handle_async(self, command: PlaceOrderCommand):
        # Create domain object
        order = Order(command.customer_id)
        order.add_item(command.item)

        # MongoDB-specific code in handler!
        await self.db.orders.insert_one({
            "_id": order.id,
            "customer_id": order.customer_id,
            "items": [item.__dict__ for item in order.items],
            "status": order.status.value
        })
```

**Problems:**

1. **Tight coupling**: Handler depends on MongoDB
2. **Hard to test**: Need real MongoDB for tests
3. **Can't switch databases**: MongoDB everywhere
4. **Violates clean architecture**: Infrastructure in application layer
5. **Repeated code**: Same serialization everywhere

## ✅ The Solution: Repository Abstraction

Repository provides collection-like interface:

```
┌────────────────────────────────────────┐
│        Application Layer               │
│                                        │
│  Handler → IOrderRepository (interface)│
│                    │                   │
│                    │ abstracts         │
└────────────────────┼────────────────────┘
                     │
┌────────────────────┼────────────────────┐
│    Infrastructure Layer                │
│                    ▼                   │
│   MongoOrderRepository (implementation)│
│   PostgresOrderRepository             │
│   InMemoryOrderRepository             │
│                                        │
└────────────────────────────────────────┘

Handler doesn't know which implementation!
```

**Benefits:**

1. **Abstraction**: Handler uses interface, not implementation
2. **Testability**: Use in-memory repository for tests
3. **Flexibility**: Swap databases without changing handlers
4. **Clean architecture**: Domain/application don't know about infrastructure
5. **Consistency**: One place for data access logic

## 🏗️ Repository Interface (Domain Layer)

Define interface in domain layer:

```python
from abc import ABC, abstractmethod
from typing import Optional, List

class IOrderRepository(ABC):
    """
    Repository interface - defines what operations are needed.
    Lives in DOMAIN layer (no MongoDB, no Postgres - pure abstraction).
    """

    @abstractmethod
    async def get_by_id_async(self, order_id: str) -> Optional[Order]:
        """Retrieve order by ID."""
        pass

    @abstractmethod
    async def save_async(self, order: Order) -> None:
        """Save order (create or update)."""
        pass

    @abstractmethod
    async def delete_async(self, order_id: str) -> None:
        """Delete order."""
        pass

    @abstractmethod
    async def find_by_customer_async(self, customer_id: str) -> List[Order]:
        """Find all orders for a customer."""
        pass

    @abstractmethod
    async def find_by_status_async(self, status: OrderStatus) -> List[Order]:
        """Find all orders with given status."""
        pass
```

**Key Points:**

- **Interface only**: No implementation details
- **Domain language**: Methods match business terms
- **Aggregate root**: Repository for `Order`, not `OrderItem`
- **Domain layer**: Alongside entities, not in infrastructure

## 🔧 Repository Implementation (Infrastructure Layer)

Implement interface in infrastructure:

```python
from motor.motor_asyncio import AsyncIOMotorCollection
from neuroglia.data.repositories import MotorRepository

class MongoOrderRepository(MotorRepository[Order, str], IOrderRepository):
    """
    MongoDB implementation of IOrderRepository.
    Lives in INFRASTRUCTURE layer.
    """

    def __init__(self, collection: AsyncIOMotorCollection):
        super().__init__(collection, Order)

    async def get_by_id_async(self, order_id: str) -> Optional[Order]:
        """Get order from MongoDB."""
        doc = await self.collection.find_one({"_id": order_id})

        if not doc:
            return None

        return self._to_entity(doc)

    async def save_async(self, order: Order) -> None:
        """Save order to MongoDB."""
        doc = self._to_document(order)

        await self.collection.replace_one(
            {"_id": order.id},
            doc,
            upsert=True
        )

        # Dispatch domain events
        await self.unit_of_work.save_changes_async(order)

    async def delete_async(self, order_id: str) -> None:
        """Delete order from MongoDB."""
        await self.collection.delete_one({"_id": order_id})

    async def find_by_customer_async(self, customer_id: str) -> List[Order]:
        """Find orders by customer (MongoDB-specific query)."""
        cursor = self.collection.find({"customer_id": customer_id})
        docs = await cursor.to_list(length=None)

        return [self._to_entity(doc) for doc in docs]

    async def find_by_status_async(self, status: OrderStatus) -> List[Order]:
        """Find orders by status."""
        cursor = self.collection.find({"status": status.value})
        docs = await cursor.to_list(length=None)

        return [self._to_entity(doc) for doc in docs]

    def _to_document(self, order: Order) -> dict:
        """Convert Order entity to MongoDB document."""
        return {
            "_id": order.id,
            "customer_id": order.customer_id,
            "items": [
                {
                    "pizza_name": item.pizza_name,
                    "size": item.size.value,
                    "quantity": item.quantity,
                    "price": float(item.price)
                }
                for item in order.items
            ],
            "status": order.status.value,
            "created_at": order.created_at
        }

    def _to_entity(self, doc: dict) -> Order:
        """Convert MongoDB document to Order entity."""
        order = Order(doc["customer_id"])
        order.id = doc["_id"]
        order.status = OrderStatus(doc["status"])
        order.created_at = doc["created_at"]

        for item_doc in doc["items"]:
            order.items.append(OrderItem(
                pizza_name=item_doc["pizza_name"],
                size=PizzaSize(item_doc["size"]),
                quantity=item_doc["quantity"],
                price=Decimal(str(item_doc["price"]))
            ))

        return order
```

## 🧪 In-Memory Repository (Testing)

For unit tests:

```python
class InMemoryOrderRepository(IOrderRepository):
    """
    In-memory implementation for testing.
    No database needed!
    """

    def __init__(self):
        self._orders: Dict[str, Order] = {}

    async def get_by_id_async(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    async def save_async(self, order: Order) -> None:
        self._orders[order.id] = order

    async def delete_async(self, order_id: str) -> None:
        if order_id in self._orders:
            del self._orders[order_id]

    async def find_by_customer_async(self, customer_id: str) -> List[Order]:
        return [
            order for order in self._orders.values()
            if order.customer_id == customer_id
        ]

    async def find_by_status_async(self, status: OrderStatus) -> List[Order]:
        return [
            order for order in self._orders.values()
            if order.status == status
        ]
```

## 🏗️ Using Repositories

### In Handlers

```python
class PlaceOrderHandler(CommandHandler):
    def __init__(self, repository: IOrderRepository):  # Interface!
        self.repository = repository

    async def handle_async(self, command: PlaceOrderCommand):
        # Create domain object
        order = Order(command.customer_id)
        for item in command.items:
            order.add_item(item.pizza_name, item.size, item.quantity, item.price)

        # Save through repository (don't know/care about MongoDB)
        await self.repository.save_async(order)

        return self.created(order_dto)

class GetOrderByIdHandler(QueryHandler):
    def __init__(self, repository: IOrderRepository):  # Same interface!
        self.repository = repository

    async def handle_async(self, query: GetOrderByIdQuery):
        # Retrieve through repository
        order = await self.repository.get_by_id_async(query.order_id)

        if not order:
            return None

        return self.mapper.map(order, OrderDto)
```

### Registration

```python
from neuroglia.dependency_injection import ServiceCollection

services = ServiceCollection()

# Register interface → implementation mapping
services.add_scoped(IOrderRepository, MongoOrderRepository)

# For testing, swap implementation
services.add_scoped(IOrderRepository, InMemoryOrderRepository)
```

## 🚀 Advanced: Generic Repository

Neuroglia provides base classes:

```python
from neuroglia.data.repositories import Repository, MotorRepository

class OrderRepository(MotorRepository[Order, str]):
    """
    Inherit from MotorRepository for common operations.
    Add custom queries as needed.
    """

    async def find_pending_orders(self) -> List[Order]:
        """Custom query - find pending orders older than 30 minutes."""
        thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)

        cursor = self.collection.find({
            "status": OrderStatus.PENDING.value,
            "created_at": {"$lt": thirty_minutes_ago}
        })

        docs = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in docs]

    async def get_order_statistics(self, date_from: datetime, date_to: datetime) -> dict:
        """Custom aggregation - order statistics."""
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": date_from, "$lt": date_to}
                }
            },
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "total_revenue": {"$sum": "$total"}
                }
            }
        ]

        result = await self.collection.aggregate(pipeline).to_list(length=None)
        return result
```

## 🧪 Testing with Repositories

### Unit Tests: In-Memory Repository

```python
async def test_place_order():
    """Test handler with in-memory repository."""
    # Use in-memory repository (no database!)
    repository = InMemoryOrderRepository()
    handler = PlaceOrderHandler(repository)

    # Execute command
    command = PlaceOrderCommand(
        customer_id="123",
        items=[OrderItemDto("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))]
    )
    result = await handler.handle_async(command)

    # Verify
    assert result.is_success
    assert len(repository._orders) == 1

    # Verify order is retrievable
    order = await repository.get_by_id_async(result.data.order_id)
    assert order is not None
    assert order.customer_id == "123"
```

### Integration Tests: Real Repository

```python
@pytest.mark.integration
async def test_mongo_repository():
    """Test with real MongoDB."""
    # Setup MongoDB connection
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    collection = client.test_db.orders

    repository = MongoOrderRepository(collection)

    # Create and save order
    order = Order(customer_id="123")
    order.add_item("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))
    await repository.save_async(order)

    # Retrieve and verify
    retrieved = await repository.get_by_id_async(order.id)
    assert retrieved.id == order.id
    assert retrieved.customer_id == "123"
    assert len(retrieved.items) == 1

    # Cleanup
    await collection.delete_one({"_id": order.id})
```

## ⚠️ Common Mistakes

### 1. Repository for Every Entity

```python
# ❌ WRONG: Repository for child entity
class IOrderItemRepository(ABC):  # OrderItem is not aggregate root!
    pass

# ✅ RIGHT: Repository only for aggregate roots
class IOrderRepository(ABC):
    # Access items through Order
    pass
```

### 2. Business Logic in Repository

```python
# ❌ WRONG: Business logic in repository
class OrderRepository:
    async def save_async(self, order: Order):
        if order.total() < 10:
            raise ValueError("Minimum order is $10")  # Business rule!
        await self.collection.insert_one(order.to_dict())

# ✅ RIGHT: Business logic in entity
class Order:
    def confirm(self):
        if self.total() < Decimal("10"):
            raise InvalidOperationError("Minimum order is $10")
        self.status = OrderStatus.CONFIRMED
```

### 3. Repository Returning DTOs

```python
# ❌ WRONG: Repository returns DTO
class IOrderRepository(ABC):
    async def get_by_id_async(self, order_id: str) -> OrderDto:  # DTO!
        pass

# ✅ RIGHT: Repository returns entity
class IOrderRepository(ABC):
    async def get_by_id_async(self, order_id: str) -> Order:  # Entity!
        pass
```

### 4. Direct Database Access

```python
# ❌ WRONG: Handler uses database directly
class GetOrderHandler:
    def __init__(self, mongo_client: MongoClient):
        self.db = mongo_client.orders_db

    async def handle_async(self, query):
        doc = await self.db.orders.find_one({"_id": query.order_id})  # Direct!
        return OrderDto(**doc)

# ✅ RIGHT: Handler uses repository
class GetOrderHandler:
    def __init__(self, repository: IOrderRepository):
        self.repository = repository

    async def handle_async(self, query):
        order = await self.repository.get_by_id_async(query.order_id)
        return self.mapper.map(order, OrderDto)
```

## 🚫 When NOT to Use Repository

Repositories add a layer. Skip when:

1. **Simple CRUD**: Direct ORM access is fine
2. **Reporting**: Complex queries easier with raw SQL
3. **Prototypes**: Experimenting with ideas
4. **No Domain Model**: If using transaction scripts
5. **Single Database**: If never switching databases

For simple apps, direct database access works fine.

## 📝 Key Takeaways

1. **Abstraction**: Interface in domain, implementation in infrastructure
2. **Collection-Like**: Methods like `get`, `save`, `find`
3. **Aggregate Roots**: Repository only for aggregate roots
4. **Testability**: In-memory implementation for tests
5. **Flexibility**: Swap implementations without changing handlers

## 🔄 Repository + Other Patterns

```
Handler
    ↓ uses
Repository Interface (domain)
    ↓ implemented by
Repository Implementation (infrastructure)
    ↓ persists
Aggregate Root
    ↓ raises
Domain Events
    ↓ dispatched by
Unit of Work
```

## 🚀 Next Steps

- **Implement it**: [Tutorial Part 6](../tutorials/mario-pizzeria-06-persistence.md) builds repositories
- **Event sourcing**: [Event Store](../features/data-access.md) for event-sourced aggregates
- **Advanced queries**: [Data Access documentation](../features/data-access.md)

## 📚 Further Reading

- Martin Fowler's [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- Evans' "Domain-Driven Design" (Chapter 6)
- [Specification Pattern](https://en.wikipedia.org/wiki/Specification_pattern) for complex queries

---

**Previous:** [← Event-Driven Architecture](event-driven.md) | **Next:** [Core Concepts Index](index.md)
