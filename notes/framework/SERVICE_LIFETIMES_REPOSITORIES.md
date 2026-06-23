# Service Lifetimes for Repositories - Scoped vs Transient

## 🎯 The Question

**Why do repositories need to be registered as SCOPED instead of TRANSIENT?**

## 📋 Service Lifetime Overview

### Singleton

- **One instance for the entire application lifetime**
- Shared across all requests and scopes
- Examples: Configuration, connection pools, caches

### Scoped

- **One instance per request/scope**
- New instance created for each HTTP request
- Disposed when request completes
- Examples: Repositories, UnitOfWork, DbContext

### Transient

- **New instance every time it's requested**
- Multiple instances within the same request if injected multiple times
- Examples: Lightweight services with no state

---

## 🔍 Why Repositories MUST Be Scoped

### 1. **UnitOfWork Integration**

Repositories need to participate in the same transactional/tracking boundary within a request:

```python
# With SCOPED repositories:
class PlaceOrderHandler:
    def __init__(self,
                 customer_repo: Repository[Customer, str],
                 order_repo: Repository[Order, str],
                 unit_of_work: IUnitOfWork):
        self.customer_repo = customer_repo  # Same instance across handler
        self.order_repo = order_repo        # Same instance across handler
        self.unit_of_work = unit_of_work    # Same instance across handler

    async def handle_async(self, command):
        # Both repos share the same scope and can be tracked by UnitOfWork
        customer = await self.customer_repo.get_async(command.customer_id)

        order = Order(customer_id=customer.id())
        order.add_item(...)  # Raises domain events

        # UnitOfWork can collect events from both aggregates
        self.unit_of_work.register_aggregate(order)
        await self.order_repo.add_async(order)

        # Domain events dispatched automatically by middleware
```

**Problem with TRANSIENT**: Each injection would create a NEW repository instance, breaking the shared scope with UnitOfWork.

### 2. **Request-Scoped Caching**

Repositories may cache entities within a request to avoid redundant database queries:

```python
# Handler that needs the same customer multiple times
class ComplexOrderHandler:
    async def handle_async(self, command):
        # First call: Load from MongoDB
        customer = await self.customer_repo.get_async(command.customer_id)

        # Business logic...
        self.validate_customer(customer)

        # Second call: Could return cached instance (SCOPED)
        # vs. New database query (TRANSIENT)
        customer_again = await self.customer_repo.get_async(command.customer_id)
```

**With SCOPED**: Same repository instance can cache the customer within the request.

**With TRANSIENT**: Each call creates a new repository, no caching possible.

### 3. **Async Context Management**

Motor (async MongoDB driver) requires proper async context per request:

```python
# SCOPED ensures proper async context per request
class MotorRepository:
    def __init__(self, client: AsyncIOMotorClient, ...):
        self._client = client  # Singleton connection pool
        self._collection = None  # Lazy-loaded per scope

    @property
    def collection(self):
        if self._collection is None:
            # This happens ONCE per request (SCOPED)
            self._collection = self._client[db_name][collection_name]
        return self._collection
```

**With TRANSIENT**: Collection reference recreated unnecessarily on every injection.

### 4. **Memory Efficiency**

```python
# A single handler with multiple repository dependencies
class PlaceOrderHandler:
    def __init__(self,
                 customer_repo: Repository[Customer, str],
                 order_repo: Repository[Order, str],
                 pizza_repo: Repository[Pizza, str]):
        # SCOPED: 3 repository instances for the entire request
        # TRANSIENT: 3 instances NOW, but if handlers call each other
        #            or services use repos, could be 10+ instances
```

**SCOPED** = Predictable memory usage per request
**TRANSIENT** = Unpredictable, wasteful instantiation

### 5. **Domain Event Collection**

DomainEventDispatchingMiddleware depends on scoped repositories:

```python
class DomainEventDispatchingMiddleware(PipelineBehavior):
    def __init__(self, unit_of_work: IUnitOfWork, mediator: Mediator):
        # UnitOfWork and repositories MUST share the same scope
        self.unit_of_work = unit_of_work  # SCOPED

    async def handle_async(self, request, next_handler):
        # Execute command handler (uses SCOPED repositories)
        result = await next_handler(request)

        # Collect events from aggregates modified by SCOPED repositories
        events = self.unit_of_work.get_uncommitted_events()

        # Dispatch events
        for event in events:
            await self.mediator.publish_async(event)

        return result
```

If repositories were TRANSIENT, the middleware's UnitOfWork wouldn't see the aggregates because they'd be in different instances!

---

## 🏗️ MotorRepository.configure() Implementation

### Correct Implementation (SCOPED)

```python
@staticmethod
def configure(builder, entity_type, key_type, database_name, ...):
    # Singleton: Shared connection pool across ALL requests
    builder.services.try_add_singleton(
        AsyncIOMotorClient,
        singleton=AsyncIOMotorClient(connection_string),
    )

    # SCOPED: One repository per request
    builder.services.add_scoped(
        MotorRepository[entity_type, key_type],
        implementation_factory=create_motor_repository,
    )

    # SCOPED: Abstract interface also scoped
    builder.services.add_scoped(
        Repository[entity_type, key_type],
        implementation_factory=get_repository_interface,
    )
```

### Why This Pattern?

1. **AsyncIOMotorClient** = SINGLETON

   - Connection pool is expensive to create
   - Safe to share across requests (thread-safe)
   - Motor handles connection pooling internally

2. **MotorRepository** = SCOPED

   - Lightweight wrapper around client
   - Needs request isolation
   - Participates in UnitOfWork pattern

3. **Repository Interface** = SCOPED
   - Points to the SCOPED concrete implementation
   - Handlers inject `Repository[T, K]` and get SCOPED instance

---

## 📊 Comparison Table

| Aspect                     | Singleton                 | Scoped            | Transient           |
| -------------------------- | ------------------------- | ----------------- | ------------------- |
| **Lifetime**               | Application               | Request           | Injection           |
| **Instance Count**         | 1 total                   | 1 per request     | N per request       |
| **State**                  | Shared (dangerous)        | Request-isolated  | No state            |
| **UnitOfWork Integration** | ❌ No                     | ✅ Yes            | ❌ No               |
| **Request Caching**        | ❌ Shared across requests | ✅ Per request    | ❌ No               |
| **Async Context**          | ⚠️ Shared                 | ✅ Isolated       | ⚠️ Multiple         |
| **Memory Usage**           | Minimal                   | Moderate          | High                |
| **Best For**               | Connection pools, config  | Repositories, UoW | Helpers, validators |

---

## 🎯 Mario's Pizzeria Example

### Before (Manual Registration - SCOPED)

```python
# main.py
builder.services.add_scoped(ICustomerRepository, MongoCustomerRepository)
builder.services.add_scoped(IOrderRepository, MongoOrderRepository)
```

### After (MotorRepository.configure() - SCOPED)

```python
# main.py
MotorRepository.configure(
    builder,
    entity_type=Customer,
    key_type=str,
    database_name="mario_pizzeria",
    collection_name="customers"
)
# Registers both MotorRepository[Customer, str] and Repository[Customer, str] as SCOPED
```

### Handler Usage (No Change)

```python
class GetCustomerProfileHandler:
    def __init__(self, repository: Repository[Customer, str]):
        self.repository = repository  # ✅ SCOPED instance injected

    async def handle_async(self, query):
        # Same repository instance throughout this request
        customer = await self.repository.get_async(query.customer_id)
        return self.mapper.map(customer, CustomerDto)
```

---

## 🧪 Testing Behavior

### Test: Verify Scoped Lifetime

```python
@pytest.mark.asyncio
async def test_scoped_repository_same_instance_per_request():
    # Setup
    builder = WebApplicationBuilder()
    MotorRepository.configure(builder, Customer, str, "test_db")

    # Create scope (simulates HTTP request)
    with builder.services.create_scope() as scope:
        # First injection
        repo1 = scope.get_required_service(Repository[Customer, str])

        # Second injection in same scope
        repo2 = scope.get_required_service(Repository[Customer, str])

        # Same instance within scope
        assert repo1 is repo2  # ✅ SCOPED

    # New scope (new request)
    with builder.services.create_scope() as scope2:
        repo3 = scope2.get_required_service(Repository[Customer, str])

        # Different instance in different scope
        assert repo3 is not repo1  # ✅ SCOPED (new request = new instance)
```

### Test: Verify Transient Would Fail

```python
@pytest.mark.asyncio
async def test_transient_would_create_multiple_instances():
    # If we used add_transient instead:
    builder.services.add_transient(
        Repository[Customer, str],
        implementation_factory=create_motor_repository
    )

    with builder.services.create_scope() as scope:
        repo1 = scope.get_required_service(Repository[Customer, str])
        repo2 = scope.get_required_service(Repository[Customer, str])

        assert repo1 is not repo2  # ❌ TRANSIENT (different instances!)
```

---

## ✅ Best Practices

### ✅ DO: Use SCOPED for Repositories

```python
# Framework pattern
MotorRepository.configure(builder, Customer, str, "mydb")
# Internally uses add_scoped()
```

### ✅ DO: Use SINGLETON for Connection Pools

```python
# AsyncIOMotorClient is SINGLETON (connection pool)
builder.services.try_add_singleton(
    AsyncIOMotorClient,
    singleton=AsyncIOMotorClient(connection_string)
)
```

### ✅ DO: Use SCOPED for UnitOfWork

```python
builder.services.add_scoped(
    IUnitOfWork,
    implementation_factory=lambda _: UnitOfWork()
)
```

### ❌ DON'T: Use TRANSIENT for Repositories

```python
# ❌ WRONG - Breaks UnitOfWork and caching
builder.services.add_transient(
    Repository[Customer, str],
    implementation_factory=create_repository
)
```

### ❌ DON'T: Use SINGLETON for Repositories

```python
# ❌ WRONG - Shared state across requests (dangerous!)
builder.services.add_singleton(
    Repository[Customer, str],
    singleton=MotorRepository(...)
)
```

---

## 🔗 Related Documentation

- **Dependency Injection**: https://bvandewe.github.io/pyneuro/features/dependency-injection/
- **Repository Pattern**: https://bvandewe.github.io/pyneuro/features/data-access/
- **UnitOfWork Pattern**: https://bvandewe.github.io/pyneuro/patterns/unit-of-work/
- **Service Lifetimes in ASP.NET Core**: https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection

---

## 📝 Summary

**Question**: Should repositories be scoped or transient?

**Answer**: **SCOPED** ✅

**Reasons**:

1. UnitOfWork integration (event collection)
2. Request-scoped caching
3. Async context management
4. Memory efficiency
5. Domain event collection

**Motor Pattern**:

- **AsyncIOMotorClient** = SINGLETON (connection pool)
- **MotorRepository** = SCOPED (request isolation)
- **Repository Interface** = SCOPED (points to scoped concrete)

This ensures proper async operations, event sourcing, and transaction boundaries in Neuroglia applications! 🎉
