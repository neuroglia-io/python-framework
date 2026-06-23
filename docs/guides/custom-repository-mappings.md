# 🔌 Custom Repository Mappings

Learn how to register domain-specific repository implementations with single-line configuration using `repository_mappings`.

## 🎯 Overview

Starting with **v0.7.2**, `DataAccessLayer.ReadModel` supports `repository_mappings` parameter, enabling clean registration of custom repository implementations that extend base repository functionality with domain-specific query methods.

**Key Benefits:**

- ✅ **Single-Line Registration**: No manual DI setup required
- ✅ **Domain-Specific Methods**: Add custom query operations
- ✅ **Clean Architecture**: Preserve domain layer boundaries
- ✅ **Type Safety**: Full IDE support and type checking
- ✅ **Convention Over Configuration**: Automatic wiring

## 🏗️ Basic Usage

### Problem: Need Domain-Specific Queries

Your domain layer defines repository interfaces with custom query methods:

```python
# domain/repositories/task_repository.py
from abc import ABC, abstractmethod
from typing import List
from neuroglia.data.infrastructure.abstractions import Repository
from integration.models import TaskDto

class TaskRepository(Repository[TaskDto, str], ABC):
    """Domain-specific task repository interface"""

    @abstractmethod
    async def get_by_department_async(self, department: str) -> List[TaskDto]:
        """Get all tasks for a specific department"""
        pass

    @abstractmethod
    async def get_overdue_tasks_async(self) -> List[TaskDto]:
        """Get all tasks past their due date"""
        pass

    @abstractmethod
    async def get_by_assignee_async(self, user_id: str) -> List[TaskDto]:
        """Get all tasks assigned to a specific user"""
        pass
```

### Solution: Custom Implementation with Repository Mappings

**Step 1: Create Motor Implementation**

```python
# integration/repositories/motor_task_repository.py
from datetime import datetime, timezone
from typing import List
from neuroglia.data.infrastructure.mongo import MotorRepository
from integration.models import TaskDto
from domain.repositories import TaskRepository

class MotorTaskRepository(MotorRepository[TaskDto, str], TaskRepository):
    """Motor implementation of TaskRepository with custom queries"""

    async def get_by_department_async(self, department: str) -> List[TaskDto]:
        """Get all tasks for a specific department"""
        return await self.find_async({"department": department})

    async def get_overdue_tasks_async(self) -> List[TaskDto]:
        """Get all tasks past their due date"""
        now = datetime.now(timezone.utc)
        return await self.find_async({
            "due_date": {"$lt": now},
            "status": {"$ne": "completed"}
        })

    async def get_by_assignee_async(self, user_id: str) -> List[TaskDto]:
        """Get all tasks assigned to a specific user"""
        return await self.find_async({"assigned_to": user_id})
```

**Step 2: Register with Repository Mappings**

```python
# main.py
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer
from domain.repositories import TaskRepository
from integration.repositories import MotorTaskRepository

builder = WebApplicationBuilder()

# Single-line registration with repository_mappings!
DataAccessLayer.ReadModel(
    database_name="tools_provider",
    repository_type="motor",
    repository_mappings={
        TaskRepository: MotorTaskRepository,  # Map interface to implementation
    }
).configure(builder, ["integration.models"])

app = builder.build()
```

**Step 3: Use in Handlers**

```python
# application/handlers/get_tasks_handler.py
from neuroglia.mediation import QueryHandler
from domain.repositories import TaskRepository

class GetTasksQueryHandler(QueryHandler[GetTasksQuery, OperationResult]):
    def __init__(self, task_repository: TaskRepository):  # Inject domain interface
        self.task_repository = task_repository

    async def handle_async(self, request: GetTasksQuery) -> OperationResult:
        # Use domain-specific methods!
        if "admin" in request.user_info.get("roles", []):
            tasks = await self.task_repository.get_all_async()
        elif request.department:
            tasks = await self.task_repository.get_by_department_async(request.department)
        elif request.show_overdue:
            tasks = await self.task_repository.get_overdue_tasks_async()
        else:
            user_id = request.user_info.get("user_id")
            tasks = await self.task_repository.get_by_assignee_async(user_id)

        return self.ok(tasks)
```

## 🚀 Advanced Patterns

### Multiple Repository Mappings

Register multiple custom repositories at once:

```python
DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type="motor",
    repository_mappings={
        TaskRepository: MotorTaskRepository,
        OrderRepository: MotorOrderRepository,
        CustomerRepository: MotorCustomerRepository,
    }
).configure(builder, ["integration.models"])
```

### Combining with Queryable Support

Custom repositories automatically support queryable operations:

```python
class MotorTaskRepository(MotorRepository[TaskDto, str], TaskRepository):
    """Custom repository with both domain methods AND queryable support"""

    async def get_by_department_async(self, department: str) -> List[TaskDto]:
        """Domain-specific method using queryable API"""
        return await self.query_async() \
            .where(lambda t: t.department == department) \
            .order_by(lambda t: t.created_at) \
            .to_list_async()

    async def get_critical_tasks_async(self, department: str) -> List[TaskDto]:
        """Complex query with multiple filters"""
        return await self.query_async() \
            .where(lambda t: t.department == department) \
            .where(lambda t: t.priority == "critical") \
            .where(lambda t: t.status != "completed") \
            .order_by_descending(lambda t: t.due_date) \
            .to_list_async()
```

### Reusable Query Patterns

Encapsulate complex queries in repository methods:

```python
class MotorOrderRepository(MotorRepository[OrderDto, str], OrderRepository):
    """Order repository with reusable query patterns"""

    async def get_pending_orders_by_customer_async(
        self,
        customer_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> List[OrderDto]:
        """Paginated pending orders for a customer"""
        skip_count = (page - 1) * page_size

        return await self.query_async() \
            .where(lambda o: o.customer_id == customer_id) \
            .where(lambda o: o.status == "pending") \
            .order_by_descending(lambda o: o.created_at) \
            .skip(skip_count) \
            .take(page_size) \
            .to_list_async()

    async def get_revenue_by_period_async(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[OrderDto]:
        """Get completed orders within date range for revenue calculation"""
        return await self.find_async({
            "status": "completed",
            "completed_at": {
                "$gte": start_date,
                "$lte": end_date
            }
        })
```

## 🎨 Design Patterns

### Pattern 1: Repository Per Aggregate

Create one repository interface per aggregate root:

```python
# Domain layer - one repository per aggregate
class OrderRepository(Repository[OrderDto, str], ABC):
    """Order aggregate repository"""
    pass

class CustomerRepository(Repository[CustomerDto, str], ABC):
    """Customer aggregate repository"""
    pass

# Infrastructure layer - Motor implementations
class MotorOrderRepository(MotorRepository[OrderDto, str], OrderRepository):
    pass

class MotorCustomerRepository(MotorRepository[CustomerDto, str], CustomerRepository):
    pass

# Registration
DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type="motor",
    repository_mappings={
        OrderRepository: MotorOrderRepository,
        CustomerRepository: MotorCustomerRepository,
    }
).configure(builder, ["integration.models"])
```

### Pattern 2: Query Object Pattern

Combine repository mappings with query objects:

```python
# Domain query specifications
@dataclass
class TaskSearchCriteria:
    department: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    overdue_only: bool = False

class TaskRepository(Repository[TaskDto, str], ABC):
    @abstractmethod
    async def search_async(self, criteria: TaskSearchCriteria) -> List[TaskDto]:
        """Search tasks using criteria object"""
        pass

# Implementation with dynamic query building
class MotorTaskRepository(MotorRepository[TaskDto, str], TaskRepository):
    async def search_async(self, criteria: TaskSearchCriteria) -> List[TaskDto]:
        """Build query dynamically based on criteria"""
        query = self.query_async()

        if criteria.department:
            query = query.where(lambda t: t.department == criteria.department)

        if criteria.status:
            query = query.where(lambda t: t.status == criteria.status)

        if criteria.assigned_to:
            query = query.where(lambda t: t.assigned_to == criteria.assigned_to)

        if criteria.priority:
            query = query.where(lambda t: t.priority == criteria.priority)

        if criteria.overdue_only:
            now = datetime.now(timezone.utc)
            return await self.find_async({
                "due_date": {"$lt": now},
                "status": {"$ne": "completed"}
            })

        return await query.order_by_descending(lambda t: t.created_at).to_list_async()
```

### Pattern 3: Read/Write Separation

Use different repositories for read and write operations:

```python
# Read repository with query optimizations
class TaskReadRepository(Repository[TaskDto, str], ABC):
    """Optimized for read operations"""

    @abstractmethod
    async def get_dashboard_summary_async(self, user_id: str) -> dict:
        """Get user's task dashboard data"""
        pass

# Write repository with business logic
class TaskWriteRepository(Repository[Task, str], ABC):
    """Optimized for write operations with domain events"""

    @abstractmethod
    async def create_with_validation_async(self, task: Task) -> OperationResult:
        """Create task with validation"""
        pass

# Registration (separate read/write models)
DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type="motor",
    repository_mappings={
        TaskReadRepository: MotorTaskReadRepository,
    }
).configure(builder, ["integration.models.read"])

DataAccessLayer.WriteModel().configure(builder, ["domain.entities"])
```

## 🧪 Testing Custom Repositories

### Unit Testing Custom Methods

```python
import pytest
from unittest.mock import AsyncMock, Mock
from neuroglia.serialization.json import JsonSerializer

@pytest.fixture
def mock_motor_client():
    """Create mock Motor client"""
    client = Mock()
    collection = AsyncMock()
    client.__getitem__ = Mock(return_value=Mock(__getitem__=Mock(return_value=collection)))
    return client, collection

@pytest.mark.asyncio
async def test_get_by_department(mock_motor_client):
    """Test custom department query method"""
    client, collection = mock_motor_client

    # Create repository instance
    repo = MotorTaskRepository(
        client=client,
        database_name="test_db",
        collection_name="tasks",
        serializer=JsonSerializer(),
        entity_type=TaskDto,
        mediator=None
    )

    # Mock collection response
    collection.find = Mock(return_value=AsyncMock())
    collection.find.return_value.__aiter__ = lambda: iter([
        {"id": "1", "department": "engineering", "title": "Task 1"},
        {"id": "2", "department": "engineering", "title": "Task 2"}
    ])

    # Test custom method
    tasks = await repo.get_by_department_async("engineering")

    assert len(tasks) == 2
    collection.find.assert_called_once_with({"department": "engineering"})
```

### Integration Testing with TestContainers

```python
import pytest
from testcontainers.mongodb import MongoDbContainer
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture(scope="module")
async def mongodb_container():
    """Start MongoDB container for integration tests"""
    with MongoDbContainer("mongo:7") as mongo:
        yield mongo.get_connection_url()

@pytest.fixture
async def test_repository(mongodb_container):
    """Create real repository with test MongoDB"""
    client = AsyncIOMotorClient(mongodb_container)
    repo = MotorTaskRepository(
        client=client,
        database_name="test_db",
        collection_name="tasks",
        serializer=JsonSerializer(),
        entity_type=TaskDto,
        mediator=None
    )
    yield repo
    # Cleanup
    await client.drop_database("test_db")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_custom_repository_integration(test_repository):
    """Integration test with real MongoDB"""
    # Create test data
    task1 = TaskDto(id="1", department="eng", title="Task 1", due_date=datetime.now())
    task2 = TaskDto(id="2", department="eng", title="Task 2", due_date=datetime.now())
    task3 = TaskDto(id="3", department="sales", title="Task 3", due_date=datetime.now())

    await test_repository.add_async(task1)
    await test_repository.add_async(task2)
    await test_repository.add_async(task3)

    # Test custom query
    eng_tasks = await test_repository.get_by_department_async("eng")

    assert len(eng_tasks) == 2
    assert all(t.department == "eng" for t in eng_tasks)
```

## 💡 Best Practices

### 1. **Keep Domain Layer Pure**

```python
# ✅ Good: Abstract interface in domain layer
class TaskRepository(Repository[TaskDto, str], ABC):
    @abstractmethod
    async def get_by_department_async(self, department: str) -> List[TaskDto]:
        pass

# ❌ Avoid: MongoDB-specific code in domain
class TaskRepository:
    async def get_by_department(self, department: str):
        return await self.collection.find({"department": department})  # ❌ Infrastructure leak
```

### 2. **Use Repository Mappings for All Custom Repositories**

```python
# ✅ Good: Single registration point
DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type="motor",
    repository_mappings={
        TaskRepository: MotorTaskRepository,
        OrderRepository: MotorOrderRepository,
    }
).configure(builder, ["integration.models"])

# ❌ Avoid: Manual DI registration scattered across codebase
builder.services.add_scoped(TaskRepository, MotorTaskRepository)  # ❌ Inconsistent
builder.services.add_scoped(OrderRepository, MotorOrderRepository)  # ❌ Boilerplate
```

### 3. **Leverage Both Queryable and Custom Methods**

```python
# ✅ Good: Use appropriate method for the task
class MotorTaskRepository(MotorRepository[TaskDto, str], TaskRepository):
    async def get_by_department_async(self, department: str) -> List[TaskDto]:
        # Simple query - use find_async
        return await self.find_async({"department": department})

    async def get_critical_pending_tasks_async(self, department: str) -> List[TaskDto]:
        # Complex query - use queryable
        return await self.query_async() \
            .where(lambda t: t.department == department) \
            .where(lambda t: t.priority == "critical") \
            .where(lambda t: t.status == "pending") \
            .order_by(lambda t: t.due_date) \
            .to_list_async()
```

### 4. **Document Custom Query Methods**

````python
class MotorTaskRepository(MotorRepository[TaskDto, str], TaskRepository):
    async def get_by_department_async(self, department: str) -> List[TaskDto]:
        """
        Get all tasks for a specific department.

        Args:
            department: Department name (e.g., "engineering", "sales")

        Returns:
            List of TaskDto objects ordered by creation date (newest first)

        Example:
            ```python
            eng_tasks = await repo.get_by_department_async("engineering")
            ```
        """
        return await self.query_async() \
            .where(lambda t: t.department == department) \
            .order_by_descending(lambda t: t.created_at) \
            .to_list_async()
````

## 🔄 Migration from Manual Registration

### Before (Manual DI Registration)

```python
# main.py - Manual registration (verbose, error-prone)
from neuroglia.dependency_injection import ServiceProvider

builder = WebApplicationBuilder()

# Configure base repositories
DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type="motor"
).configure(builder, ["integration.models"])

# Manual registration for custom repositories (boilerplate!)
def create_task_repo(sp: ServiceProvider):
    motor_client = sp.get_required_service(AsyncIOMotorClient)
    serializer = sp.get_required_service(JsonSerializer)
    return MotorTaskRepository(
        client=motor_client,
        database_name="myapp",
        collection_name="tasks",
        serializer=serializer,
        entity_type=TaskDto,
        mediator=sp.get_service(Mediator)
    )

builder.services.add_scoped(TaskRepository, create_task_repo)  # Lots of boilerplate!
```

### After (Repository Mappings)

```python
# main.py - Clean, single-line registration
builder = WebApplicationBuilder()

DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type="motor",
    repository_mappings={
        TaskRepository: MotorTaskRepository,  # That's it!
    }
).configure(builder, ["integration.models"])
```

## 🔗 Related Documentation

- [MotorRepository Queryable Support](./motor-queryable-repositories.md)
- [Data Access Layer](../features/data-access.md)
- [Repository Pattern](../patterns/repository.md)
- [Dependency Injection](../features/dependency-injection.md)

## 🐛 Troubleshooting

### Repository Not Resolving

**Issue**: Handler fails with "Service not registered" error

**Solution**: Ensure the domain interface is in `repository_mappings`:

```python
# ❌ Wrong: Registering implementation class
repository_mappings={
    MotorTaskRepository: MotorTaskRepository,  # Wrong!
}

# ✅ Correct: Map interface to implementation
repository_mappings={
    TaskRepository: MotorTaskRepository,  # Correct!
}
```

### Type Mismatch Errors

**Issue**: Implementation doesn't match interface signature

**Solution**: Ensure implementation class extends both `MotorRepository` and domain interface:

```python
# ✅ Correct: Extend both base and interface
class MotorTaskRepository(MotorRepository[TaskDto, str], TaskRepository):
    pass

# ❌ Wrong: Missing domain interface
class MotorTaskRepository(MotorRepository[TaskDto, str]):
    pass
```

### Custom Methods Not Available

**Issue**: IDE doesn't show custom methods after injection

**Solution**: Inject domain interface, not base Repository:

```python
# ✅ Correct: Inject domain interface
class GetTasksHandler(QueryHandler):
    def __init__(self, task_repository: TaskRepository):  # Domain interface
        self.repository = task_repository

# ❌ Wrong: Inject base repository
class GetTasksHandler(QueryHandler):
    def __init__(self, task_repository: Repository[TaskDto, str]):  # No custom methods
        self.repository = task_repository
```

---

**Next Steps:**

- Learn about [Queryable Repositories](./motor-queryable-repositories.md)
- Explore [CQRS Query Patterns](../features/simple-cqrs.md)
- Read about [Clean Architecture](../patterns/clean-architecture.md)
