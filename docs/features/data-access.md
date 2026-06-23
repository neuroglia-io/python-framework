# 🍕 Data Access

Neuroglia provides a flexible data access layer that supports multiple storage backends through a unified repository pattern for **Mario's Pizzeria**. From storing pizza orders in files to managing kitchen workflows with event sourcing, the framework adapts to your pizzeria's needs.

Let's explore how to store orders, manage inventory, and track kitchen operations using different persistence strategies.

## 🎯 Overview

The pizzeria data access system provides:

- **Repository Pattern**: Unified interface for orders, pizzas, and customer data
- **Multiple Storage Backends**: File-based (development), MongoDB (production), Event Store (kitchen events)
- **Event Sourcing**: Complete order lifecycle tracking with EventStoreDB
- **CQRS Support**: Separate read models for menus and write models for orders
- **Query Abstractions**: Find orders by status, customer, or time period
- **Unit of Work**: Transaction management across order processing

## 🏗️ Core Abstractions

### Repository Interface for Pizzeria Entities

The base repository interface defines standard CRUD operations for pizzeria data:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional
from datetime import datetime, date

TEntity = TypeVar('TEntity')
TKey = TypeVar('TKey')

class Repository(Generic[TEntity, TKey], ABC):
    """Base repository interface for pizzeria entities"""

    @abstractmethod
    async def get_by_id_async(self, id: TKey) -> Optional[TEntity]:
        """Get entity by ID (order, pizza, customer)"""
        pass

    @abstractmethod
    async def save_async(self, entity: TEntity) -> None:
        """Save entity (create or update)"""
        pass

    @abstractmethod
    async def delete_async(self, id: TKey) -> None:
        """Delete entity by ID"""
        pass

    @abstractmethod
    async def get_all_async(self) -> List[TEntity]:
        """Get all entities"""
        pass

    @abstractmethod
    async def find_async(self, predicate) -> List[TEntity]:
        """Find entities matching predicate"""
        pass

# Pizzeria-specific repository interfaces
class IOrderRepository(Repository[Order, str], ABC):
    """Order-specific repository operations"""

    @abstractmethod
    async def get_by_customer_phone_async(self, phone: str) -> List[Order]:
        """Get orders by customer phone number"""
        pass

    @abstractmethod
    async def get_by_status_async(self, status: str) -> List[Order]:
        """Get orders by status (pending, cooking, ready, delivered)"""
        pass

    @abstractmethod
    async def get_by_date_range_async(self, start_date: date, end_date: date) -> List[Order]:
        """Get orders within date range for reports"""
        pass

class IPizzaRepository(Repository[Pizza, str], ABC):
    """Pizza menu repository operations"""

    @abstractmethod
    async def get_by_category_async(self, category: str) -> List[Pizza]:
        """Get pizzas by category (signature, specialty, custom)"""
        pass

    @abstractmethod
    async def get_available_async(self) -> List[Pizza]:
        """Get only available pizzas (not sold out)"""
        pass
```

```python
from neuroglia.data.abstractions import Queryable
from typing import Callable
from decimal import Decimal

class QueryablePizzeriaRepository(Repository[TEntity, TKey], Queryable[TEntity]):
    """Repository with advanced querying for pizzeria analytics"""

    async def where(self, predicate: Callable[[TEntity], bool]) -> List[TEntity]:
        """Filter pizzeria entities by predicate"""
        pass

    async def order_by_desc(self, selector: Callable[[TEntity], any]) -> List[TEntity]:
        """Order entities in descending order"""
        pass

    async def group_by(self, selector: Callable[[TEntity], any]) -> dict:
        """Group entities for analytics"""
        pass

# Example: Advanced order queries
class ExtendedOrderRepository(IOrderRepository, QueryablePizzeriaRepository[Order, str]):
    """Order repository with advanced analytics queries"""

    async def get_top_customers_async(self, limit: int = 10) -> List[dict]:
        """Get top customers by order count"""
        orders = await self.get_all_async()
        customer_counts = {}

        for order in orders:
            phone = order.customer_phone
            customer_counts[phone] = customer_counts.get(phone, 0) + 1

        # Sort and limit
        top_customers = sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [{"phone": phone, "order_count": count} for phone, count in top_customers]

    async def get_revenue_by_date_async(self, start_date: date, end_date: date) -> List[dict]:
        """Get daily revenue within date range"""
        orders = await self.get_by_date_range_async(start_date, end_date)
        daily_revenue = {}

        for order in orders:
            order_date = order.order_time.date()
            if order_date not in daily_revenue:
                daily_revenue[order_date] = Decimal('0')
            daily_revenue[order_date] += order.total_amount

        return [{"date": date, "revenue": revenue} for date, revenue in sorted(daily_revenue.items())]
```

## 📁 File-Based Storage for Development

### File Repository Implementation

Perfect for development and testing of Mario's Pizzeria:

```python
import json
import os
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime, date

class FileRepository(Repository[TEntity, TKey]):
    """File-based repository using JSON storage"""

    def __init__(self, entity_type: type, data_dir: str = "data"):
        self.entity_type = entity_type
        self.entity_name = entity_type.__name__.lower()
        self.data_dir = Path(data_dir)
        self.entity_dir = self.data_dir / self.entity_name

        # Ensure directories exist
        self.entity_dir.mkdir(parents=True, exist_ok=True)

    async def get_by_id_async(self, id: TKey) -> Optional[TEntity]:
        """Get entity from JSON file"""
        file_path = self.entity_dir / f"{id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return self._dict_to_entity(data)
        except Exception as e:
            raise StorageException(f"Failed to load {self.entity_name} {id}: {e}")

    async def save_async(self, entity: TEntity) -> None:
        """Save entity to JSON file"""
        file_path = self.entity_dir / f"{entity.id}.json"

        try:
            data = self._entity_to_dict(entity)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=self._json_serializer, ensure_ascii=False)
        except Exception as e:
            raise StorageException(f"Failed to save {self.entity_name} {entity.id}: {e}")

    async def delete_async(self, id: TKey) -> None:
        """Delete entity JSON file"""
        file_path = self.entity_dir / f"{id}.json"
        if file_path.exists():
            file_path.unlink()

    async def get_all_async(self) -> List[TEntity]:
        """Get all entities from JSON files"""
        entities = []

        for file_path in self.entity_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    entity = self._dict_to_entity(data)
                    entities.append(entity)
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")
                continue

        return entities

    async def find_async(self, predicate: Callable[[TEntity], bool]) -> List[TEntity]:
        """Find entities matching predicate"""
        all_entities = await self.get_all_async()
        return [entity for entity in all_entities if predicate(entity)]

    def _entity_to_dict(self, entity: TEntity) -> dict:
        """Convert entity to dictionary for JSON serialization"""
        if hasattr(entity, '__dict__'):
            return entity.__dict__.copy()
        elif hasattr(entity, '_asdict'):
            return entity._asdict()
        else:
            raise ValueError(f"Cannot serialize entity of type {type(entity)}")

    def _dict_to_entity(self, data: dict) -> TEntity:
        """Convert dictionary back to entity"""
        return self.entity_type(**data)

    def _json_serializer(self, obj):
        """Handle special types in JSON serialization"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)

# Pizzeria-specific file repositories
class FileOrderRepository(FileRepository[Order, str], IOrderRepository):
    """File-based order repository for development"""

    def __init__(self, data_dir: str = "data"):
        super().__init__(Order, data_dir)

    async def get_by_customer_phone_async(self, phone: str) -> List[Order]:
        """Get orders by customer phone"""
        return await self.find_async(lambda order: order.customer_phone == phone)

    async def get_by_status_async(self, status: str) -> List[Order]:
        """Get orders by status"""
        return await self.find_async(lambda order: order.status == status)

    async def get_by_date_range_async(self, start_date: date, end_date: date) -> List[Order]:
        """Get orders within date range"""
        return await self.find_async(lambda order:
            start_date <= order.order_time.date() <= end_date)

class FilePizzaRepository(FileRepository[Pizza, str], IPizzaRepository):
    """File-based pizza repository for menu management"""

    def __init__(self, data_dir: str = "data"):
        super().__init__(Pizza, data_dir)

    async def get_by_category_async(self, category: str) -> List[Pizza]:
        """Get pizzas by category"""
        return await self.find_async(lambda pizza: pizza.category == category)

    async def get_available_async(self) -> List[Pizza]:
        """Get available pizzas only"""
        return await self.find_async(lambda pizza: pizza.is_available)
```

### MongoDB Repository for Pizzeria

Built-in MongoDB repository implementation for production pizzeria:

```python
from neuroglia.data.infrastructure.mongo import MongoRepository
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional, List, Dict, Any

class MongoOrderRepository(MongoRepository[Order, str], IOrderRepository):
    """MongoDB repository for pizza orders"""

    def __init__(self, database: AsyncIOMotorDatabase):
        super().__init__(database, "orders")

    async def get_by_customer_phone_async(self, phone: str) -> List[Order]:
        """Get orders by customer phone with index optimization"""
        cursor = self.collection.find({"customer_phone": phone}).sort("order_time", -1)
        documents = await cursor.to_list(length=None)
        return [self._document_to_entity(doc) for doc in documents]

    async def get_by_status_async(self, status: str) -> List[Order]:
        """Get orders by status for kitchen management"""
        cursor = self.collection.find({"status": status}).sort("order_time", 1)  # FIFO
        documents = await cursor.to_list(length=None)
        return [self._document_to_entity(doc) for doc in documents]

    async def get_by_date_range_async(self, start_date: date, end_date: date) -> List[Order]:
        """Get orders within date range for reporting"""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        cursor = self.collection.find({
            "order_time": {
                "$gte": start_datetime,
                "$lte": end_datetime
            }
        }).sort("order_time", 1)

        documents = await cursor.to_list(length=None)
        return [self._document_to_entity(doc) for doc in documents]

    async def get_kitchen_queue_async(self, statuses: List[str]) -> List[Order]:
        """Get orders in kitchen queue (optimized for kitchen display)"""
        cursor = self.collection.find(
            {"status": {"$in": statuses}},
            {"customer_name": 1, "pizzas": 1, "order_time": 1, "status": 1, "estimated_ready_time": 1}
        ).sort("order_time", 1)

        documents = await cursor.to_list(length=None)
        return [self._document_to_entity(doc) for doc in documents]

    async def get_daily_revenue_async(self, target_date: date) -> Dict[str, Any]:
        """Get daily revenue aggregation"""
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        pipeline = [
            {
                "$match": {
                    "order_time": {"$gte": start_datetime, "$lte": end_datetime},
                    "status": {"$in": ["ready", "delivered"]}  # Only completed orders
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$total_amount"},
                    "order_count": {"$sum": 1},
                    "average_order_value": {"$avg": "$total_amount"}
                }
            }
        ]

        result = await self.collection.aggregate(pipeline).to_list(length=1)
        return result[0] if result else {"total_revenue": 0, "order_count": 0, "average_order_value": 0}

    def _entity_to_document(self, order: Order) -> Dict[str, Any]:
        """Convert order entity to MongoDB document"""
        doc = {
            "_id": order.id,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_address": order.customer_address,
            "pizzas": [self._pizza_to_dict(pizza) for pizza in order.pizzas],
            "status": order.status,
            "order_time": order.order_time,
            "estimated_ready_time": order.estimated_ready_time,
            "total_amount": float(order.total_amount),  # MongoDB decimal handling
            "payment_method": order.payment_method
        }
        return doc

    def _document_to_entity(self, doc: Dict[str, Any]) -> Order:
        """Convert MongoDB document to order entity"""
        return Order(
            id=doc["_id"],
            customer_name=doc["customer_name"],
            customer_phone=doc["customer_phone"],
            customer_address=doc["customer_address"],
            pizzas=[self._dict_to_pizza(pizza_dict) for pizza_dict in doc["pizzas"]],
            status=doc["status"],
            order_time=doc["order_time"],
            estimated_ready_time=doc.get("estimated_ready_time"),
            total_amount=Decimal(str(doc["total_amount"])),
            payment_method=doc.get("payment_method", "cash")
        )

class MongoPizzaRepository(MongoRepository[Pizza, str], IPizzaRepository):
    """MongoDB repository for pizza menu management"""

    def __init__(self, database: AsyncIOMotorDatabase):
        super().__init__(database, "pizzas")

    async def get_by_category_async(self, category: str) -> List[Pizza]:
        """Get pizzas by category with caching optimization"""
        cursor = self.collection.find({"category": category, "is_available": True}).sort("name", 1)
        documents = await cursor.to_list(length=None)
        return [self._document_to_entity(doc) for doc in documents]

    async def get_available_async(self) -> List[Pizza]:
        """Get all available pizzas for menu display"""
        cursor = self.collection.find({"is_available": True}).sort([("category", 1), ("name", 1)])
        documents = await cursor.to_list(length=None)
        return [self._document_to_entity(doc) for doc in documents]

    async def update_availability_async(self, pizza_id: str, is_available: bool) -> None:
        """Update pizza availability (for sold out items)"""
        await self.collection.update_one(
            {"_id": pizza_id},
            {"$set": {"is_available": is_available, "updated_at": datetime.utcnow()}}
        )

    def _entity_to_document(self, pizza: Pizza) -> Dict[str, Any]:
        """Convert pizza entity to MongoDB document"""
        return {
            "_id": pizza.id,
            "name": pizza.name,
            "description": pizza.description,
            "category": pizza.category,
            "base_price": float(pizza.base_price),
            "available_toppings": pizza.available_toppings,
            "preparation_time_minutes": pizza.preparation_time_minutes,
            "is_available": pizza.is_available,
            "is_seasonal": pizza.is_seasonal,
            "created_at": pizza.created_at,
            "updated_at": datetime.utcnow()
        }
```

### MongoDB Indexes for Performance

Create indexes for pizzeria query patterns:

```python
# Create indexes for optimal pizzeria query performance
async def create_pizzeria_indexes():
    """Create MongoDB indexes for pizzeria collections"""

    # Order collection indexes
    await orders_collection.create_index("customer_phone")  # Customer lookup
    await orders_collection.create_index("status")  # Kitchen filtering
    await orders_collection.create_index("order_time")  # Chronological ordering
    await orders_collection.create_index([("status", 1), ("order_time", 1)])  # Kitchen queue
    await orders_collection.create_index([("order_time", -1)])  # Recent orders first
    await orders_collection.create_index("estimated_ready_time")  # Ready time tracking

    # Pizza collection indexes
    await pizzas_collection.create_index("category")  # Menu category filtering
    await pizzas_collection.create_index("is_available")  # Available items only
    await pizzas_collection.create_index([("category", 1), ("name", 1)])  # Sorted menu display
    await pizzas_collection.create_index("is_seasonal")  # Seasonal items management
```

### Repository Registration with MongoDB

```python
from neuroglia.hosting.web import WebApplicationBuilder

def create_pizzeria_app():
    """Create Mario's Pizzeria application with MongoDB persistence"""
    builder = WebApplicationBuilder()

    # MongoDB configuration
    mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = mongo_client.marios_pizzeria

    # Repository registration
    builder.services.add_singleton(lambda: database)
    builder.services.add_scoped(MongoOrderRepository)
    builder.services.add_scoped(MongoPizzaRepository)

    # Alias interfaces to implementations
    builder.services.add_scoped(IOrderRepository, lambda sp: sp.get_service(MongoOrderRepository))
    builder.services.add_scoped(IPizzaRepository, lambda sp: sp.get_service(MongoPizzaRepository))

    app = builder.build()
    return app
```

### Optimistic Concurrency Control (OCC)

MotorRepository provides automatic **Optimistic Concurrency Control** for `AggregateRoot` entities using version-based conflict detection. This prevents lost updates when multiple processes attempt to modify the same entity concurrently.

#### How OCC Works

When saving an `AggregateRoot`, the repository:

1. **Checks the current version** - Reads `state_version` from the aggregate's state
2. **Increments the version** - Increases `state_version` by 1 for this save
3. **Atomic update** - Uses MongoDB's `replace_one` with version filter: `{"id": entity_id, "state_version": old_version}`
4. **Conflict detection** - If `matched_count == 0` and entity exists, another process updated it first
5. **Exception** - Raises `OptimisticConcurrencyException` with version details

#### Version Semantics for State-Based Persistence

- **New aggregates**: Start with `state_version = 0`
- **Version increment**: Once per save operation (not per event)
- **Event sourcing**: This is different - events have their own sequence numbers
- **Timestamps**: `last_modified` automatically updated on each save

#### Pizzeria OCC Example

```python
from neuroglia.data import OptimisticConcurrencyException, EntityNotFoundException

class UpdateOrderStatusHandler(CommandHandler[UpdateOrderStatusCommand, OperationResult]):
    """Update order status with automatic conflict detection"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, command: UpdateOrderStatusCommand) -> OperationResult:
        try:
            # Load current order state
            order = await self.order_repository.get_by_id_async(command.order_id)
            if not order:
                return self.not_found(f"Order {command.order_id} not found")

            # Business logic - update status
            order.update_status(command.new_status)

            # Save with automatic OCC
            # If another process modified this order, OptimisticConcurrencyException is raised
            await self.order_repository.update_async(order)

            return self.ok("Order status updated successfully")

        except OptimisticConcurrencyException as ex:
            # Concurrent update detected - inform user to retry
            return self.conflict(
                f"Order was modified by another process. "
                f"Expected version {ex.expected_version}, but current version is {ex.actual_version}. "
                f"Please reload and try again."
            )
        except EntityNotFoundException as ex:
            # Entity was deleted between load and save
            return self.not_found(f"{ex.entity_type} '{ex.entity_id}' not found")
```

#### Retry Pattern for OCC

Implement automatic retry with exponential backoff:

```python
from typing import Callable, TypeVar, Optional
import asyncio

T = TypeVar('T')

async def retry_on_conflict(
    operation: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 0.1
) -> T:
    """Retry operation on OptimisticConcurrencyException"""

    for attempt in range(max_attempts):
        try:
            return await operation()
        except OptimisticConcurrencyException as ex:
            if attempt == max_attempts - 1:
                # Final attempt failed - re-raise
                raise

            # Exponential backoff
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)

            # Log retry for observability
            logger.warning(
                f"Optimistic concurrency conflict on attempt {attempt + 1}/{max_attempts}. "
                f"Expected version: {ex.expected_version}, Actual: {ex.actual_version}. "
                f"Retrying in {delay}s..."
            )

# Usage in handler
async def update_order_with_retry(self, order_id: str, new_status: str):
    """Update order with automatic conflict retry"""

    async def update_operation():
        order = await self.order_repository.get_by_id_async(order_id)
        order.update_status(new_status)
        await self.order_repository.update_async(order)
        return order

    return await retry_on_conflict(update_operation, max_attempts=3)
```

#### When OCC is Applied

OCC is **automatically enabled** for:

- ✅ `AggregateRoot` entities with `AggregateState`
- ✅ State-based persistence using `MotorRepository`
- ✅ All update operations via `update_async()`

OCC is **NOT applied** to:

- ❌ Simple `Entity` objects (no state version tracking)
- ❌ Read operations (`get_by_id_async`, queries)
- ❌ Delete operations (no version check)

#### Testing OCC

The framework includes comprehensive OCC tests:

```python
# Example test structure
@pytest.mark.asyncio
async def test_concurrent_update_raises_exception():
    """Verify OCC detects concurrent modifications"""
    # Arrange: Two handlers load same order
    order1 = await repository.get_by_id_async(order_id)
    order2 = await repository.get_by_id_async(order_id)

    # Act: First update succeeds
    order1.update_status("cooking")
    await repository.update_async(order1)  # version: 0 -> 1

    # Assert: Second update fails (version conflict)
    order2.update_status("ready")
    with pytest.raises(OptimisticConcurrencyException) as exc:
        await repository.update_async(order2)  # expects version 0, but actual is 1

    assert exc.value.expected_version == 0
    assert exc.value.actual_version == 1
```

#### Best Practices

1. **Always handle OptimisticConcurrencyException** - Inform users and suggest reload
2. **Use retry patterns** for automated workflows (background jobs, integrations)
3. **Keep transactions short** - Load, modify, save quickly to minimize conflicts
4. **Design for eventual consistency** - Accept that conflicts will occur
5. **Monitor conflict rates** - High rates may indicate architectural issues
6. **Don't use for simple entities** - OCC overhead only needed for aggregates

## 📊 Event Sourcing for Kitchen Workflow

### Kitchen Event Store

Track kitchen workflow with event sourcing patterns:

```python
from neuroglia.eventing import DomainEvent
from datetime import datetime, timedelta
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class OrderStatusChangedEvent(DomainEvent):
    """Event for tracking order status changes in kitchen"""
    order_id: str
    old_status: str
    new_status: str
    changed_by: str
    change_reason: Optional[str] = None
    estimated_ready_time: Optional[datetime] = None

@dataclass
class PizzaStartedEvent(DomainEvent):
    """Event when pizza preparation begins"""
    order_id: str
    pizza_name: str
    pizza_index: int
    started_by: str
    estimated_completion: datetime

@dataclass
class PizzaCompletedEvent(DomainEvent):
    """Event when pizza is finished"""
    order_id: str
    pizza_name: str
    pizza_index: int
    completed_by: str
    actual_completion_time: datetime
    preparation_duration_minutes: int

class KitchenWorkflowEventStore:
    """Event store for kitchen workflow tracking"""

    def __init__(self, event_repository: IEventRepository):
        self.event_repository = event_repository

    async def record_order_status_change(self,
                                         order_id: str,
                                         old_status: str,
                                         new_status: str,
                                         changed_by: str,
                                         change_reason: str = None) -> None:
        """Record order status changes for kitchen analytics"""
        event = OrderStatusChangedEvent(
            order_id=order_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            change_reason=change_reason,
            estimated_ready_time=self._calculate_ready_time(new_status)
        )

        await self.event_repository.save_event_async(event)

    async def record_pizza_started(self,
                                   order_id: str,
                                   pizza_name: str,
                                   pizza_index: int,
                                   started_by: str) -> None:
        """Record when pizza preparation begins"""
        estimated_completion = datetime.now(timezone.utc) + timedelta(
            minutes=self._get_pizza_prep_time(pizza_name)
        )

        event = PizzaStartedEvent(
            order_id=order_id,
            pizza_name=pizza_name,
            pizza_index=pizza_index,
            started_by=started_by,
            estimated_completion=estimated_completion
        )

        await self.event_repository.save_event_async(event)

    async def record_pizza_completed(self,
                                     order_id: str,
                                     pizza_name: str,
                                     pizza_index: int,
                                     completed_by: str,
                                     start_time: datetime) -> None:
        """Record when pizza is completed"""
        completion_time = datetime.now(timezone.utc)
        duration_minutes = int((completion_time - start_time).total_seconds() / 60)

        event = PizzaCompletedEvent(
            order_id=order_id,
            pizza_name=pizza_name,
            pizza_index=pizza_index,
            completed_by=completed_by,
            actual_completion_time=completion_time,
            preparation_duration_minutes=duration_minutes
        )

        await self.event_repository.save_event_async(event)

    async def get_kitchen_performance_metrics(self, date_range: tuple[date, date]) -> Dict[str, Any]:
        """Get kitchen performance analytics from events"""
        start_date, end_date = date_range

        # Query events within date range
        events = await self.event_repository.get_events_by_date_range_async(start_date, end_date)

        # Calculate metrics
        pizza_completion_events = [e for e in events if isinstance(e, PizzaCompletedEvent)]
        status_change_events = [e for e in events if isinstance(e, OrderStatusChangedEvent)]

        return {
            "total_pizzas_completed": len(pizza_completion_events),
            "average_prep_time_minutes": self._calculate_average_prep_time(pizza_completion_events),
            "peak_hours": self._calculate_peak_hours(status_change_events),
            "order_completion_rate": self._calculate_completion_rate(status_change_events),
            "staff_performance": self._calculate_staff_performance(pizza_completion_events)
        }
```

```python
from neuroglia.data import Repository
from typing import List, Dict, Any
import json
from pathlib import Path
from datetime import datetime

class FileEventRepository(Repository[DomainEvent, str]):
    """File-based event repository for development and testing"""

    def __init__(self, events_directory: str = "data/events"):
        super().__init__()
        self.events_directory = Path(events_directory)
        self.events_directory.mkdir(parents=True, exist_ok=True)

    async def save_event_async(self, event: DomainEvent) -> None:
        """Save event to JSON file organized by date"""
        event_date = event.occurred_at.date()
        date_directory = self.events_directory / event_date.strftime("%Y-%m-%d")
        date_directory.mkdir(exist_ok=True)

        event_file = date_directory / f"{event.id}.json"

        event_data = {
            "id": event.id,
            "event_type": event.__class__.__name__,
            "occurred_at": event.occurred_at.isoformat(),
            "data": self._serialize_event_data(event)
        }

        async with aiofiles.open(event_file, 'w') as f:
            await f.write(json.dumps(event_data, indent=2))

    async def get_events_by_date_range_async(self,
                                             start_date: date,
                                             end_date: date) -> List[DomainEvent]:
        """Get events within date range"""
        events = []
        current_date = start_date

        while current_date <= end_date:
            date_directory = self.events_directory / current_date.strftime("%Y-%m-%d")

            if date_directory.exists():
                for event_file in date_directory.glob("*.json"):
                    async with aiofiles.open(event_file, 'r') as f:
                        event_data = json.loads(await f.read())
                        event = self._deserialize_event(event_data)
                        if event:
                            events.append(event)

            current_date += timedelta(days=1)

        return sorted(events, key=lambda e: e.occurred_at)
```

### MongoDB Event Store

Production event store with aggregation capabilities:

```python
from neuroglia.data.infrastructure.mongo import MongoRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

class MongoEventRepository(MongoRepository[DomainEvent, str]):
    """MongoDB event repository for production event sourcing"""

    def __init__(self, database: AsyncIOMotorDatabase):
        super().__init__(database, "events")

    async def save_event_async(self, event: DomainEvent) -> None:
        """Save event with automatic indexing"""
        document = {
            "_id": event.id,
            "event_type": event.__class__.__name__,
            "occurred_at": event.occurred_at,
            "data": self._serialize_event_data(event),
            "version": 1,
            "metadata": {
                "correlation_id": getattr(event, 'correlation_id', None),
                "causation_id": getattr(event, 'causation_id', None)
            }
        }

        await self.collection.insert_one(document)

    async def get_kitchen_timeline_events(self,
                                          order_id: str,
                                          limit: int = 100) -> List[DomainEvent]:
        """Get chronological timeline of kitchen events for an order"""
        cursor = self.collection.find(
            {
                "event_type": {"$in": ["OrderStatusChangedEvent", "PizzaStartedEvent", "PizzaCompletedEvent"]},
                "data.order_id": order_id
            }
        ).sort("occurred_at", 1).limit(limit)

        documents = await cursor.to_list(length=limit)
        return [self._deserialize_event(doc) for doc in documents]

    async def get_performance_aggregation(self,
                                          start_date: datetime,
                                          end_date: datetime) -> Dict[str, Any]:
        """Get aggregated kitchen performance metrics"""
        pipeline = [
            {
                "$match": {
                    "occurred_at": {"$gte": start_date, "$lte": end_date},
                    "event_type": "PizzaCompletedEvent"
                }
            },
            {
                "$group": {
                    "_id": "$data.pizza_name",
                    "total_pizzas": {"$sum": 1},
                    "avg_prep_time": {"$avg": "$data.preparation_duration_minutes"},
                    "min_prep_time": {"$min": "$data.preparation_duration_minutes"},
                    "max_prep_time": {"$max": "$data.preparation_duration_minutes"}
                }
            },
            {
                "$sort": {"total_pizzas": -1}
            }
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)
        return {
            "pizza_performance": results,
            "reporting_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
```

```python
from neuroglia.data import IQueryableRepository
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta

class IAnalyticsRepository(IQueryableRepository[Order, str]):
    """Enhanced queryable interface for pizzeria analytics"""

    async def get_revenue_by_period_async(self,
                                          period: str,  # 'daily', 'weekly', 'monthly'
                                          start_date: date,
                                          end_date: date) -> Dict[str, Any]:
        """Get revenue metrics grouped by time period"""
        pass

    async def get_popular_pizzas_async(self,
                                       start_date: date,
                                       end_date: date,
                                       limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular pizzas by order count"""
        pass

    async def get_customer_insights_async(self,
                                          customer_phone: str) -> Dict[str, Any]:
        """Get customer ordering patterns and preferences"""
        pass

    async def get_peak_hours_analysis_async(self,
                                            date_range: tuple[date, date]) -> Dict[str, Any]:
        """Analyze order patterns by hour of day"""
        pass

class MongoAnalyticsRepository(MongoOrderRepository, IAnalyticsRepository):
    """MongoDB implementation with advanced analytics capabilities"""

    async def get_revenue_by_period_async(self,
                                          period: str,
                                          start_date: date,
                                          end_date: date) -> Dict[str, Any]:
        """Get revenue metrics with MongoDB aggregation"""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Dynamic grouping based on period
        group_format = {
            'daily': {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_time"}},
            'weekly': {"$dateToString": {"format": "%Y-W%U", "date": "$order_time"}},
            'monthly': {"$dateToString": {"format": "%Y-%m", "date": "$order_time"}}
        }

        pipeline = [
            {
                "$match": {
                    "order_time": {"$gte": start_datetime, "$lte": end_datetime},
                    "status": {"$in": ["ready", "delivered"]}
                }
            },
            {
                "$group": {
                    "_id": group_format.get(period, group_format['daily']),
                    "revenue": {"$sum": "$total_amount"},
                    "order_count": {"$sum": 1},
                    "average_order_value": {"$avg": "$total_amount"}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)

        return {
            "period": period,
            "data": results,
            "summary": {
                "total_revenue": sum(r["revenue"] for r in results),
                "total_orders": sum(r["order_count"] for r in results),
                "periods_analyzed": len(results)
            }
        }

    async def get_popular_pizzas_async(self,
                                       start_date: date,
                                       end_date: date,
                                       limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular pizzas with detailed analytics"""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        pipeline = [
            {
                "$match": {
                    "order_time": {"$gte": start_datetime, "$lte": end_datetime},
                    "status": {"$in": ["ready", "delivered"]}
                }
            },
            {
                "$unwind": "$pizzas"
            },
            {
                "$group": {
                    "_id": "$pizzas.name",
                    "order_count": {"$sum": 1},
                    "total_revenue": {"$sum": "$pizzas.price"},
                    "avg_price": {"$avg": "$pizzas.price"},
                    "unique_customers": {"$addToSet": "$customer_phone"}
                }
            },
            {
                "$project": {
                    "pizza_name": "$_id",
                    "order_count": 1,
                    "total_revenue": 1,
                    "avg_price": 1,
                    "unique_customers": {"$size": "$unique_customers"},
                    "_id": 0
                }
            },
            {
                "$sort": {"order_count": -1}
            },
            {
                "$limit": limit
            }
        ]

        return await self.collection.aggregate(pipeline).to_list(length=limit)

    async def get_customer_insights_async(self,
                                          customer_phone: str) -> Dict[str, Any]:
        """Comprehensive customer analytics"""
        pipeline = [
            {
                "$match": {"customer_phone": customer_phone}
            },
            {
                "$group": {
                    "_id": "$customer_phone",
                    "total_orders": {"$sum": 1},
                    "total_spent": {"$sum": "$total_amount"},
                    "avg_order_value": {"$avg": "$total_amount"},
                    "first_order": {"$min": "$order_time"},
                    "last_order": {"$max": "$order_time"},
                    "favorite_pizzas": {"$push": "$pizzas.name"},
                    "payment_methods": {"$addToSet": "$payment_method"}
                }
            },
            {
                "$project": {
                    "customer_phone": "$_id",
                    "total_orders": 1,
                    "total_spent": 1,
                    "avg_order_value": 1,
                    "first_order": 1,
                    "last_order": 1,
                    "customer_lifetime_days": {
                        "$divide": [
                            {"$subtract": ["$last_order", "$first_order"]},
                            86400000  # milliseconds to days
                        ]
                    },
                    "payment_methods": 1,
                    "_id": 0
                }
            }
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=1)
        if not results:
            return {"error": "Customer not found"}

        customer_data = results[0]

        # Calculate favorite pizza (most frequent)
        # This would need additional aggregation pipeline for pizza frequency

        return customer_data

    async def get_peak_hours_analysis_async(self,
                                            date_range: tuple[date, date]) -> Dict[str, Any]:
        """Analyze order patterns by hour for staffing optimization"""
        start_date, end_date = date_range
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        pipeline = [
            {
                "$match": {
                    "order_time": {"$gte": start_datetime, "$lte": end_datetime}
                }
            },
            {
                "$group": {
                    "_id": {"$hour": "$order_time"},
                    "order_count": {"$sum": 1},
                    "total_revenue": {"$sum": "$total_amount"},
                    "avg_order_value": {"$avg": "$total_amount"}
                }
            },
            {
                "$project": {
                    "hour": "$_id",
                    "order_count": 1,
                    "total_revenue": 1,
                    "avg_order_value": 1,
                    "_id": 0
                }
            },
            {
                "$sort": {"hour": 1}
            }
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=24)

        # Fill in missing hours with zero values
        hourly_data = {r["hour"]: r for r in results}
        complete_data = []

        for hour in range(24):
            hour_data = hourly_data.get(hour, {
                "hour": hour,
                "order_count": 0,
                "total_revenue": 0.0,
                "avg_order_value": 0.0
            })
            complete_data.append(hour_data)

        # Find peak hours (top 3)
        sorted_by_orders = sorted(complete_data, key=lambda x: x["order_count"], reverse=True)
        peak_hours = sorted_by_orders[:3]

        return {
            "hourly_breakdown": complete_data,
            "peak_hours": peak_hours,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
```

```python
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, date, timedelta
from decimal import Decimal

class TestOrderRepository:
    """Unit tests for order repository implementations"""

    @pytest.fixture
    def sample_order(self):
        """Create sample pizza order for testing"""
        return Order(
            id="order_123",
            customer_name="John Doe",
            customer_phone="+1234567890",
            customer_address="123 Main St",
            pizzas=[
                Pizza(name="Margherita", price=Decimal("12.99")),
                Pizza(name="Pepperoni", price=Decimal("14.99"))
            ],
            status="preparing",
            order_time=datetime.utcnow(),
            total_amount=Decimal("27.98"),
            payment_method="card"
        )

    @pytest.fixture
    def mock_file_repository(self, tmp_path):
        """Create file repository with temporary directory"""
        return FileOrderRepository(str(tmp_path / "orders"))

    @pytest.mark.asyncio
    async def test_save_order_creates_file(self, mock_file_repository, sample_order):
        """Test that saving an order creates proper file structure"""
        await mock_file_repository.save_async(sample_order)

        # Verify file was created
        order_file = Path(mock_file_repository.orders_directory) / f"{sample_order.id}.json"
        assert order_file.exists()

        # Verify file content
        with open(order_file, 'r') as f:
            order_data = json.load(f)
            assert order_data["customer_name"] == sample_order.customer_name
            assert len(order_data["pizzas"]) == 2

    @pytest.mark.asyncio
    async def test_get_by_customer_phone(self, mock_file_repository, sample_order):
        """Test customer phone lookup functionality"""
        await mock_file_repository.save_async(sample_order)

        # Create another order for same customer
        second_order = Order(
            id="order_456",
            customer_name="John Doe",
            customer_phone="+1234567890",
            customer_address="123 Main St",
            pizzas=[Pizza(name="Hawaiian", price=Decimal("15.99"))],
            status="ready",
            order_time=datetime.utcnow() + timedelta(hours=1)
        )
        await mock_file_repository.save_async(second_order)

        # Test phone lookup
        customer_orders = await mock_file_repository.get_by_customer_phone_async("+1234567890")

        assert len(customer_orders) == 2
        # Should be ordered by time (most recent first)
        assert customer_orders[0].id == "order_456"
        assert customer_orders[1].id == "order_123"

    @pytest.mark.asyncio
    async def test_kitchen_queue_filtering(self, mock_file_repository):
        """Test kitchen queue status filtering"""
        # Create orders with different statuses
        orders = [
            Order(id="order_1", status="preparing", customer_name="Customer 1"),
            Order(id="order_2", status="cooking", customer_name="Customer 2"),
            Order(id="order_3", status="ready", customer_name="Customer 3"),
            Order(id="order_4", status="delivered", customer_name="Customer 4")
        ]

        for order in orders:
            await mock_file_repository.save_async(order)

        # Get kitchen queue (preparing and cooking)
        kitchen_orders = await mock_file_repository.get_kitchen_queue_async(["preparing", "cooking"])

        assert len(kitchen_orders) == 2
        statuses = [order.status for order in kitchen_orders]
        assert "preparing" in statuses
        assert "cooking" in statuses
        assert "ready" not in statuses

@pytest.mark.integration
class TestMongoOrderRepository:
    """Integration tests for MongoDB repository"""

    @pytest.fixture
    async def mongo_repository(self, mongo_test_client):
        """Create MongoDB repository for testing"""
        database = mongo_test_client.test_pizzeria
        return MongoOrderRepository(database)

    @pytest.mark.asyncio
    async def test_revenue_aggregation(self, mongo_repository):
        """Test MongoDB revenue aggregation pipeline"""
        # Setup test data
        test_orders = [
            Order(
                id="order_1",
                total_amount=Decimal("25.99"),
                status="delivered",
                order_time=datetime(2024, 1, 15, 12, 0)
            ),
            Order(
                id="order_2",
                total_amount=Decimal("18.50"),
                status="delivered",
                order_time=datetime(2024, 1, 15, 18, 0)
            ),
            Order(
                id="order_3",
                total_amount=Decimal("32.00"),
                status="preparing",  # Should be excluded
                order_time=datetime(2024, 1, 15, 19, 0)
            )
        ]

        for order in test_orders:
            await mongo_repository.save_async(order)

        # Test daily revenue calculation
        revenue_data = await mongo_repository.get_daily_revenue_async(date(2024, 1, 15))

        assert revenue_data["total_revenue"] == 44.49  # Only delivered orders
        assert revenue_data["order_count"] == 2
        assert revenue_data["average_order_value"] == 22.245

class TestEventRepository:
    """Test event repository for kitchen workflow tracking"""

    @pytest.fixture
    def sample_kitchen_events(self):
        """Create sample kitchen events for testing"""
        return [
            OrderStatusChangedEvent(
                order_id="order_123",
                old_status="received",
                new_status="preparing",
                changed_by="chef_mario"
            ),
            PizzaStartedEvent(
                order_id="order_123",
                pizza_name="Margherita",
                pizza_index=0,
                started_by="chef_mario",
                estimated_completion=datetime.utcnow() + timedelta(minutes=12)
            )
        ]

    @pytest.mark.asyncio
    async def test_event_chronological_ordering(self, file_event_repository, sample_kitchen_events):
        """Test that events are retrieved in chronological order"""
        # Save events in random order
        for event in reversed(sample_kitchen_events):
            await file_event_repository.save_event_async(event)

        # Retrieve events
        today = date.today()
        retrieved_events = await file_event_repository.get_events_by_date_range_async(today, today)

        # Should be ordered by occurrence time
        assert len(retrieved_events) == 2
        assert retrieved_events[0].occurred_at <= retrieved_events[1].occurred_at

# Test fixtures for integration testing
@pytest.fixture
async def mongo_test_client():
    """MongoDB test client with cleanup"""
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient("mongodb://localhost:27017")

    # Use test database
    test_db = client.test_pizzeria

    yield client

    # Cleanup
    await client.drop_database("test_pizzeria")
    client.close()

@pytest.fixture
def file_event_repository(tmp_path):
    """File event repository with temporary storage"""
    return FileEventRepository(str(tmp_path / "events"))
```

## 🔗 Related Documentation

- [Getting Started Guide](../getting-started.md) - Complete pizzeria application tutorial
- [CQRS & Mediation](../patterns/cqrs.md) - Commands and queries with pizzeria examples
- [Dependency Injection](../patterns/dependency-injection.md) - Service registration for repositories
- [MVC Controllers](mvc-controllers.md) - API endpoints using these repositories
- [Source Code Naming Conventions](../references/source_code_naming_convention.md) - Repository, entity, and method naming patterns

---

_This documentation demonstrates data access patterns using Mario's Pizzeria as a consistent example throughout the Neuroglia framework. The patterns shown scale from simple file-based storage for development to MongoDB with advanced analytics for production use._
