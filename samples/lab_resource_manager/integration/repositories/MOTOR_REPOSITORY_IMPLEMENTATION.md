# Lab Worker Resource Repository Implementation (etcd)

## Overview

This document describes the implementation of the **etcd-based** `EtcdLabWorkerResourceRepository` for managing LabWorker resources in the Lab Resource Manager sample application.

## Why etcd?

The Lab Resource Manager uses **etcd** as its primary persistence layer instead of MongoDB to leverage etcd's native features that are ideal for resource-oriented architectures:

### Key Benefits of etcd

1. **Native Watchable API**: etcd provides built-in watch capabilities for real-time resource change notifications
2. **Strong Consistency**: Raft consensus algorithm ensures strong consistency across distributed systems
3. **Atomic Operations**: Compare-And-Swap (CAS) operations for optimistic concurrency control
4. **Kubernetes-Style**: Same storage backend used by Kubernetes for resource management
5. **High Availability**: Built-in clustering support for fault tolerance
6. **TTL Support**: Lease-based expiration for temporary resources

## Implementation Summary

### 1. Storage Backend Implementation

**File**: `integration/repositories/etcd_storage_backend.py`

The implementation consists of an etcd storage backend that bridges etcd's API with the ResourceRepository interface:

#### EtcdStorageBackend

A wrapper class that bridges etcd's API with the ResourceRepository's storage backend interface:

```python
class EtcdStorageBackend:
    """Storage backend adapter for etcd.

    Provides a key-value interface that ResourceRepository expects,
    while using etcd as the underlying storage with native watch capabilities.
    """
```

**Key Methods**:

- `exists(name: str) -> bool`: Check if a resource exists by name
- `get(name: str) -> Optional[dict]`: Retrieve resource by name
- `set(name: str, value: dict)`: Store or update a resource
- `delete(name: str) -> bool`: Delete a resource by name
- `keys(pattern: str) -> List[str]`: List resource names matching a pattern
- `watch(callback, key_prefix: str)`: **Native etcd watch** for real-time updates
- `list_with_labels(label_selector: dict) -> List[dict]`: Filter resources by labels
- `compare_and_swap(name, expected, new) -> bool`: Atomic CAS operation

#### EtcdLabWorkerResourceRepository

Extends `ResourceRepository[LabWorkerSpec, LabWorkerStatus]` to provide custom query methods specific to LabWorker resources:**Custom Query Methods**:

- `find_by_lab_track_async(lab_track: str)`: Find workers assigned to a specific lab track
- `find_by_phase_async(phase: LabWorkerPhase)`: Find workers in a specific lifecycle phase
- `find_active_workers_async()`: Find all workers in Ready or Draining phases
- `find_ready_workers_async()`: Find workers available for assignment
- `find_draining_workers_async()`: Find workers being decommissioned
- `count_by_phase_async(phase: LabWorkerPhase)`: Count workers in a specific phase
- `count_by_lab_track_async(lab_track: str)`: Count workers assigned to a lab track

**Factory Methods**:

- `create_with_json_serializer()`: Create repository with JSON serialization
- `create_with_yaml_serializer()`: Create repository with YAML serialization

### 2. Service Registration

**File**: `main.py`

The repository is registered following the Neuroglia framework patterns used in Mario's Pizzeria:

#### Connection Strings Setup

```python
# Setup connection strings dictionary for Motor repository configuration
if "mongo" not in app_settings.connection_strings:
    app_settings.connection_strings["mongo"] = app_settings.mongodb_connection_string
    log.info(f"Connection strings configured: mongo={app_settings.mongodb_connection_string}")
```

#### Motor Client Registration (Singleton)

```python
# Register AsyncIOMotorClient as singleton (following MotorRepository.configure pattern)
# This ensures all repositories share the same connection pool
builder.services.try_add_singleton(
    AsyncIOMotorClient,
    singleton=AsyncIOMotorClient(app_settings.mongodb_connection_string)
)
```

**Why Singleton?**

- Shares connection pool across all repository instances
- More efficient resource usage
- Follows MongoDB best practices for connection management

#### Repository Registration (Scoped)

```python
# Register LabWorkerResourceRepository as scoped service (one per request)
# Scoped lifetime ensures proper async context and integration with UnitOfWork
def create_lab_worker_repository(sp):
    """Factory function for LabWorkerResourceRepository with DI."""
    return LabWorkerResourceRepository.create_with_json_serializer(
        motor_client=sp.get_required_service(AsyncIOMotorClient),
        database_name=database_name,
        collection_name="lab_workers",
    )

builder.services.add_scoped(
    LabWorkerResourceRepository,
    implementation_factory=create_lab_worker_repository
)
```

**Why Scoped?**

- One repository instance per request/scope
- Proper async context management
- Integration with UnitOfWork for domain event collection
- Request-scoped caching and transaction boundaries

## Architecture Pattern

This implementation follows the **Repository Pattern** as used throughout the Neuroglia framework:

```
┌─────────────────────────────────────────────┐
│         Application Layer                   │
│  (Commands, Queries, Handlers)              │
└──────────────────┬──────────────────────────┘
                   │ depends on
                   ▼
┌─────────────────────────────────────────────┐
│    LabWorkerResourceRepository              │
│    (Domain Repository Interface)            │
└──────────────────┬──────────────────────────┘
                   │ implements
                   ▼
┌─────────────────────────────────────────────┐
│  ResourceRepository[LabWorkerSpec, Status]  │
│  (Framework Base Class)                     │
└──────────────────┬──────────────────────────┘
                   │ uses
                   ▼
┌─────────────────────────────────────────────┐
│       MongoStorageBackend                   │
│  (Motor Collection Adapter)                 │
└──────────────────┬──────────────────────────┘
                   │ wraps
                   ▼
┌─────────────────────────────────────────────┐
│      AsyncIOMotorClient                     │
│    (MongoDB Async Driver)                   │
└─────────────────────────────────────────────┘
```

## Service Lifetimes

| Component                   | Lifetime  | Reason                                                             |
| --------------------------- | --------- | ------------------------------------------------------------------ |
| AsyncIOMotorClient          | Singleton | Shared connection pool, efficient resource usage                   |
| LabWorkerResourceRepository | Scoped    | Per-request instance, proper async context, UnitOfWork integration |
| MongoStorageBackend         | N/A       | Created by repository, lifetime tied to repository                 |

## Usage in Handlers

The repository is automatically injected into command and query handlers:

```python
class CreateLabWorkerHandler(CommandHandler):
    def __init__(self, repository: LabWorkerResourceRepository):
        super().__init__()
        self.repository = repository

    async def handle_async(self, command: CreateLabWorkerCommand):
        # Use repository methods
        worker = LabWorker(...)
        await self.repository.add_async(worker)
```

## Benefits

1. **Async/Await Support**: Full async support via Motor driver
2. **Type Safety**: Generic typing with LabWorkerSpec and LabWorkerStatus
3. **Custom Queries**: Domain-specific query methods (find_by_phase, find_by_lab_track)
4. **Resource Abstraction**: Kubernetes-style resource management
5. **Serialization Flexibility**: JSON or YAML serialization support
6. **Connection Pooling**: Efficient MongoDB connection management
7. **Proper Lifetimes**: Singleton client, scoped repositories
8. **Framework Integration**: Full integration with Neuroglia patterns

## Testing

To test the repository implementation:

1. **Unit Tests**: Mock MongoStorageBackend and test repository methods
2. **Integration Tests**: Use real MongoDB instance and test CRUD operations
3. **Query Tests**: Verify custom query methods return correct results
4. **Serialization Tests**: Test both JSON and YAML serialization

## Configuration

### Development (Local)

```python
mongodb_connection_string: str = "mongodb://localhost:27017"
mongodb_database_name: str = "lab_manager"
```

### Production (Docker)

```yaml
environment:
  CONNECTION_STRINGS: '{"mongo": "mongodb://root:password@mongodb:27017/?authSource=admin"}'
```

## References

- **Mario's Pizzeria Sample**: `samples/mario-pizzeria/main.py` (MotorRepository.configure pattern)
- **MotorRepository Source**: `src/neuroglia/data/infrastructure/mongo/motor_repository.py`
- **ResourceRepository Source**: `src/neuroglia/data/infrastructure/resources/resource_repository.py`
- **Lab Instance Repository**: `integration/repositories/lab_instance_resource_repository.py` (similar pattern)

## Next Steps

1. **Update Commands/Queries**: Ensure handlers use `LabWorkerResourceRepository` type hint
2. **Integration Testing**: Test repository with actual MongoDB instance
3. **Performance Tuning**: Add indexes for common query patterns (phase, lab_track)
4. **Monitoring**: Add OpenTelemetry instrumentation for repository operations
5. **Error Handling**: Implement retry logic and circuit breakers for resilience
