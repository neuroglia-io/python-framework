# Motor Async MongoDB Migration

**Date:** October 22, 2025
**Issue:** Mario's Pizzeria was using Neuroglia's synchronous `MongoRepository` which doesn't align with the async/await pattern used throughout the application.

## Problem

1. **Sync/Async Mismatch**: Neuroglia's `MongoRepository` uses `pymongo.MongoClient` (synchronous) but wraps methods in `async` signatures
2. **Not Truly Async**: All database operations were blocking even though methods were marked async
3. **Performance Impact**: Synchronous database calls block the event loop in async applications

## Solution

Implemented custom async repositories using **Motor** (the official async MongoDB driver for Python).

### Changes Made

#### 1. Added Motor Dependency

**File:** `pyproject.toml`

```toml
# Optional dependencies
motor = { version = "^3.3.0", optional = true }

[tool.poetry.extras]
mongodb = ["pymongo", "motor"]
all = ["pymongo", "motor", "esdbclient", "rx", "redis"]
```

**Installation:**

```bash
poetry lock
poetry install --extras mongodb
```

#### 2. Created Async MongoDB Repositories

**Files:**

- `integration/repositories/mongo_customer_repository.py`
- `integration/repositories/mongo_order_repository.py`

**Key Changes:**

- Import `AsyncIOMotorClient` from `motor.motor_asyncio`
- Don't inherit from Neuroglia's `MongoRepository`
- Implement `ICustomerRepository` and `IOrderRepository` directly
- Use `await` for all database operations

**Example:**

```python
from motor.motor_asyncio import AsyncIOMotorClient

class MongoCustomerRepository(ICustomerRepository):
    def __init__(self, mongo_client: AsyncIOMotorClient, serializer: JsonSerializer):
        self._mongo_client = mongo_client
        self._database = mongo_client["mario_pizzeria"]
        self._collection = self._database["customers"]
        self._serializer = serializer

    async def get_async(self, id: str) -> Optional[Customer]:
        doc = await self._collection.find_one({"id": id})  # Truly async!
        if doc is None:
            return None

        doc.pop("_id", None)
        json_str = self._serializer.serialize_to_text(doc)
        entity = self._serializer.deserialize_from_text(json_str, Customer)
        return entity

    async def add_async(self, entity: Customer) -> Customer:
        json_str = self._serializer.serialize_to_text(entity)
        doc = self._serializer.deserialize_from_text(json_str, dict)
        await self._collection.insert_one(doc)  # Truly async!
        return entity
```

#### 3. Updated DI Registration

**File:** `samples/mario-pizzeria/main.py`

```python
from motor.motor_asyncio import AsyncIOMotorClient

def configure_services(services: ServiceCollection):
    # Register async MongoDB client as singleton
    mongo_client = AsyncIOMotorClient("mongodb://mongodb:27017")
    services.add_singleton(AsyncIOMotorClient, lambda _: mongo_client)

    # Register async repositories
    services.add_scoped(ICustomerRepository, MongoCustomerRepository)
    services.add_scoped(IOrderRepository, MongoOrderRepository)
```

#### 4. Fixed Controller Imports

**Issue:** `main.py` was importing non-existent controllers

**Fixed Imports:**

```python
from api.controllers import (
    AuthController,      # Was: CustomersController
    KitchenController,   # Was: KitchensController
    MenuController,      # Was: PizzasController
    OrdersController,    # Correct ✓
    ProfileController,   # New
)
```

**File:** `api/controllers/__init__.py`

```python
from api.controllers.auth_controller import AuthController
from api.controllers.kitchen_controller import KitchenController
from api.controllers.menu_controller import MenuController
from api.controllers.orders_controller import OrdersController
from api.controllers.profile_controller import ProfileController

__all__ = [
    "AuthController",
    "KitchenController",
    "MenuController",
    "OrdersController",
    "ProfileController",
]
```

## Benefits

1. **True Async Operations**: Database calls no longer block the event loop
2. **Better Performance**: Concurrent request handling with non-blocking I/O
3. **Consistency**: Entire application stack is now async (FastAPI → handlers → repositories → MongoDB)
4. **Scalability**: Can handle more concurrent users with the same resources

## Motor vs PyMongo Comparison

| Feature             | PyMongo (Sync)     | Motor (Async)         |
| ------------------- | ------------------ | --------------------- |
| Event Loop          | Blocks             | Non-blocking          |
| Concurrency         | Limited            | High                  |
| FastAPI Integration | Poor fit           | Perfect fit           |
| Async/Await         | No                 | Yes                   |
| Performance         | Good for sync apps | Better for async apps |

## Testing

After migration:

1. ✅ Motor installed successfully (v3.7.1)
2. ✅ PyMongo updated (4.14.1 → 4.15.3)
3. ✅ Import errors resolved
4. ✅ Repository pattern maintained
5. ⏳ Integration testing pending

## Future Considerations

### Option 1: Update Neuroglia Framework

Consider adding a `MotorRepository` base class to the Neuroglia framework:

```python
# neuroglia/data/infrastructure/motor.py
from motor.motor_asyncio import AsyncIOMotorClient
from neuroglia.data.repository import Repository

class MotorRepository(Repository[TEntity, TKey]):
    """Base repository using Motor async MongoDB driver"""

    def __init__(self, mongo_client: AsyncIOMotorClient,
                 database_name: str,
                 serializer: JsonSerializer):
        self._mongo_client = mongo_client
        self._database = mongo_client[database_name]
        self._collection = self._database[self._get_collection_name()]
        self._serializer = serializer
```

### Option 2: Keep Application-Specific

Current approach works well for Mario's Pizzeria and allows full control over MongoDB operations.

## Related Documentation

- Motor Documentation: https://motor.readthedocs.io/
- Async/Await in Python: https://docs.python.org/3/library/asyncio.html
- MongoDB Async Patterns: https://www.mongodb.com/docs/drivers/motor/

## Conclusion

The migration to Motor provides true async MongoDB operations that align with FastAPI's async architecture. This improves performance, scalability, and maintains consistency across the entire application stack.
