# MotorRepository Enhancement - Configure Method & Scoped Lifetime

## 🎯 Overview

Enhanced the MotorRepository framework implementation with:

1. Static `configure()` method for consistent DI registration
2. Proper AggregateRoot vs Entity detection and handling
3. **SCOPED lifetime** (not transient) for proper async context and UnitOfWork integration

## 🔧 Changes Made

### 1. Added `configure()` Static Method

**File**: `src/neuroglia/data/infrastructure/mongo/motor_repository.py`

**Purpose**: Provide a fluent API for registering Motor repositories with the DI container, following the same pattern as EnhancedMongoRepository.

**Signature**:

```python
@staticmethod
def configure(
    builder: ApplicationBuilderBase,
    entity_type: Type[TEntity],
    key_type: Type[TKey],
    database_name: str,
    collection_name: Optional[str] = None,
    connection_string_name: str = "mongo"
) -> ApplicationBuilderBase
```

**What It Does**:

1. Retrieves MongoDB connection string from `builder.settings.connection_strings`
2. Registers `AsyncIOMotorClient` as **SINGLETON** (shared connection pool)
3. Registers `MotorRepository[entity_type, key_type]` as **SCOPED**
4. Registers `Repository[entity_type, key_type]` as **SCOPED** (abstract interface)
5. Auto-generates collection name from entity name if not provided

### 2. AggregateRoot vs Entity Support

**Added Helper Methods**:

```python
def _is_aggregate_root(self, obj: object) -> bool:
    """Check if an object is an AggregateRoot instance."""
    return isinstance(obj, AggregateRoot)

def _serialize_entity(self, entity: TEntity) -> dict:
    """
    Serialize entity handling both Entity and AggregateRoot.
    - AggregateRoot: Serializes only the state
    - Entity: Serializes the whole object
    """

def _deserialize_entity(self, doc: dict) -> TEntity:
    """
    Deserialize document handling both Entity and AggregateRoot.
    - AggregateRoot: Reconstructs from state
    - Entity: Deserializes directly
    """
```

**Why This Matters**:

- **AggregateRoot**: Has a `state` property that should be persisted (not the wrapper with domain events)
- **Entity**: Plain objects without state separation
- Repository now handles both transparently

### 3. SCOPED Lifetime (Critical Fix)

**Before** (incorrect):

```python
builder.services.add_transient(
    MotorRepository[entity_type, key_type],
    implementation_factory=create_motor_repository,
)
```

**After** (correct):

```python
builder.services.add_scoped(
    MotorRepository[entity_type, key_type],
    implementation_factory=create_motor_repository,
)
```

**Why SCOPED is Required**:

1. **UnitOfWork Integration**: Repositories must share the same scope to participate in domain event collection
2. **Request-Scoped Caching**: Same repository instance can cache entities within a request
3. **Async Context Management**: Proper async context per request
4. **Memory Efficiency**: One instance per request, not per injection
5. **Domain Event Collection**: Middleware's UnitOfWork must see aggregates from scoped repositories

See `notes/SERVICE_LIFETIMES_REPOSITORIES.md` for comprehensive explanation.

### 4. Updated Mario's Pizzeria main.py

**Before** (manual configuration):

```python
# Register MongoDB client manually
mongo_client = AsyncIOMotorClient(mongo_connection_string)
builder.services.add_singleton(
    AsyncIOMotorClient,
    implementation_factory=lambda _: mongo_client
)

# Register repositories manually
builder.services.add_scoped(ICustomerRepository, MongoCustomerRepository)
builder.services.add_scoped(IOrderRepository, MongoOrderRepository)
```

**After** (using configure):

```python
# Configure repositories using MotorRepository.configure()
MotorRepository.configure(
    builder,
    entity_type=Customer,
    key_type=str,
    database_name="mario_pizzeria",
    collection_name="customers"
)

MotorRepository.configure(
    builder,
    entity_type=Order,
    key_type=str,
    database_name="mario_pizzeria",
    collection_name="orders"
)

# Register domain-specific implementations
builder.services.add_scoped(ICustomerRepository, MongoCustomerRepository)
builder.services.add_scoped(IOrderRepository, MongoOrderRepository)
```

**Benefits**:

- ✅ Consistent with other Neuroglia repository patterns
- ✅ Automatic AsyncIOMotorClient registration
- ✅ Proper scoped lifetime
- ✅ Auto-collection name generation
- ✅ Cleaner, more declarative configuration

## 📋 Service Lifetime Pattern

### Singleton Layer (Connection Pool)

```
AsyncIOMotorClient (SINGLETON)
        ↓
   Connection Pool
   (Shared across all requests)
```

### Scoped Layer (Repositories)

```
Request 1:                Request 2:
  MotorRepository[Customer] MotorRepository[Customer]
  MotorRepository[Order]    MotorRepository[Order]
  UnitOfWork               UnitOfWork
  (Same instances)         (Different instances)
```

### Why This Architecture?

1. **AsyncIOMotorClient** = SINGLETON

   - Expensive to create
   - Thread-safe connection pool
   - Reused across all requests

2. **MotorRepository** = SCOPED

   - Lightweight wrapper
   - Request-isolated
   - Shares scope with UnitOfWork

3. **Repository Interface** = SCOPED
   - Points to scoped concrete implementation
   - Handlers get request-scoped instances

## 🧪 Testing Status

✅ Application starts successfully with new configuration
✅ API endpoints accessible at http://localhost:8080/api/docs
✅ MongoDB repositories registered with proper scoped lifetime
✅ Custom domain repositories (MongoCustomerRepository, MongoOrderRepository) extend framework base class

## 📊 Code Metrics

### MotorRepository.py

- **Lines added**: ~150 (configure method + helper methods)
- **Total lines**: ~532
- **Key features**: AggregateRoot support, scoped lifetime, fluent configuration

### main.py

- **Lines removed**: ~15 (manual AsyncIOMotorClient registration)
- **Lines added**: ~25 (MotorRepository.configure calls)
- **Net change**: +10 lines, but much cleaner and more maintainable

## 🔗 Related Files

### Created Documentation

- `notes/SERVICE_LIFETIMES_REPOSITORIES.md` - Comprehensive guide on scoped vs transient
- `notes/MONGODB_SCHEMA_AND_MOTOR_REPOSITORY_SUMMARY.md` - MongoDB schema and repository patterns

### Modified Framework Files

- `src/neuroglia/data/infrastructure/mongo/motor_repository.py` - Added configure() and AggregateRoot support

### Modified Sample Files

- `samples/mario-pizzeria/main.py` - Updated to use MotorRepository.configure()

## ✅ Verification Checklist

- [x] MotorRepository has configure() method
- [x] configure() uses add_scoped (not add_transient)
- [x] AsyncIOMotorClient registered as singleton
- [x] Repository[entity, key] registered as scoped
- [x] AggregateRoot detection and state serialization
- [x] Entity serialization without state wrapper
- [x] Mario's Pizzeria uses new configure() method
- [x] Application starts without errors
- [x] API endpoints accessible
- [x] Comprehensive documentation created

## 🎓 Key Learnings

1. **Service Lifetime Matters**: Repositories MUST be scoped for proper UnitOfWork integration
2. **Connection Pool Singleton**: Database clients should be singleton (expensive, thread-safe)
3. **AggregateRoot vs Entity**: Repositories must handle both with different serialization logic
4. **Fluent Configuration**: Static configure() methods provide clean, consistent DI registration
5. **Framework Patterns**: Following established patterns (like EnhancedMongoRepository) ensures consistency

## 🚀 Next Steps

1. **Integration Testing**: Test Keycloak login with profile auto-creation
2. **Unit Tests**: Add tests for MotorRepository.configure() method
3. **Documentation**: Update framework docs with MotorRepository usage examples
4. **EnhancedMongoRepository**: Consider updating it to also use scoped lifetime
5. **Performance Testing**: Verify scoped lifetime doesn't cause memory issues under load

---

## 📝 Summary

Successfully enhanced MotorRepository with:

- ✅ Static `configure()` method for fluent DI registration
- ✅ Proper **SCOPED** lifetime (critical for UnitOfWork)
- ✅ AggregateRoot vs Entity handling
- ✅ Updated Mario's Pizzeria to use new pattern
- ✅ Comprehensive documentation on service lifetimes

The framework now provides a consistent, clean pattern for async MongoDB repositories with proper async context management and domain event integration! 🎉
