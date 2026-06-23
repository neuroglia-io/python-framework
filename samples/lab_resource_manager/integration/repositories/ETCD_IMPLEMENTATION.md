# Lab Worker Resource Repository Implementation with etcd

## Overview

This document describes the implementation of the **etcd-based** persistence layer for managing LabWorker resources in the Lab Resource Manager sample application.

## Why etcd Instead of MongoDB?

The Lab Resource Manager uses **etcd** as its primary persistence layer to leverage native features that are ideal for resource-oriented architectures:

### Key Benefits of etcd

| Feature                | Description                                 | Benefit for Lab Resource Manager                                 |
| ---------------------- | ------------------------------------------- | ---------------------------------------------------------------- |
| **Native Watch API**   | Built-in watch capabilities for key changes | Real-time notifications when workers are created/updated/deleted |
| **Strong Consistency** | Raft consensus algorithm                    | Ensures all nodes see the same data at the same time             |
| **Atomic Operations**  | Compare-And-Swap (CAS) operations           | Safe concurrent updates with optimistic locking                  |
| **Kubernetes-Style**   | Same storage backend as Kubernetes          | Familiar patterns for resource management                        |
| **High Availability**  | Built-in clustering support                 | Fault tolerance and redundancy                                   |
| **TTL Support**        | Lease-based expiration                      | Automatic cleanup of temporary resources                         |
| **Hierarchical Keys**  | Directory-like key structure                | Natural organization of resources by type/namespace              |

### Comparison: etcd vs MongoDB

| Aspect             | etcd                                    | MongoDB                               |
| ------------------ | --------------------------------------- | ------------------------------------- |
| **Watch API**      | Native, efficient (gRPC streams)        | Change streams (requires replica set) |
| **Consistency**    | Linearizable reads                      | Eventual consistency (configurable)   |
| **Data Model**     | Key-value with hierarchy                | Document-oriented                     |
| **Use Case**       | Configuration, coordination, small data | General-purpose, large datasets       |
| **Kubernetes**     | Native (used by K8s)                    | External integration                  |
| **Atomic Updates** | Built-in CAS                            | findAndModify or transactions         |

## Architecture

```
┌─────────────────────────────────────────────┐
│         Application Layer                   │
│  (Commands, Queries, Handlers)              │
└──────────────────┬──────────────────────────┘
                   │ depends on
                   ▼
┌─────────────────────────────────────────────┐
│   EtcdLabWorkerResourceRepository           │
│   (Domain Repository Implementation)        │
└──────────────────┬──────────────────────────┘
                   │ extends
                   ▼
┌─────────────────────────────────────────────┐
│  ResourceRepository[LabWorkerSpec, Status]  │
│  (Framework Base Class)                     │
└──────────────────┬──────────────────────────┘
                   │ uses
                   ▼
┌─────────────────────────────────────────────┐
│       EtcdStorageBackend                    │
│  (etcd Key-Value Adapter)                   │
└──────────────────┬──────────────────────────┘
                   │ wraps
                   ▼
┌─────────────────────────────────────────────┐
│      etcd3.Etcd3Client                      │
│    (etcd v3 gRPC Client)                    │
└─────────────────────────────────────────────┘
```

## Implementation Details

### 1. EtcdStorageBackend

**File**: `integration/repositories/etcd_storage_backend.py`

Provides the storage interface that ResourceRepository expects:

```python
class EtcdStorageBackend:
    """Storage backend adapter for etcd.

    Features:
    - Native watchable API (etcd watch)
    - Strong consistency (etcd Raft consensus)
    - Atomic operations (Compare-And-Swap)
    - Lease-based TTL support
    - High availability (etcd clustering)
    """
```

**Key Methods**:

| Method                       | Description              | etcd Operation                 |
| ---------------------------- | ------------------------ | ------------------------------ |
| `exists(name)`               | Check if resource exists | `get(key)`                     |
| `get(name)`                  | Retrieve resource        | `get(key)`                     |
| `set(name, value)`           | Store/update resource    | `put(key, value)`              |
| `delete(name)`               | Delete resource          | `delete(key)`                  |
| `keys(pattern)`              | List matching resources  | `get_prefix(prefix)`           |
| `watch(callback)`            | **Watch for changes**    | `add_watch_prefix_callback()`  |
| `list_with_labels(selector)` | Filter by labels         | Custom filtering on get_prefix |
| `compare_and_swap()`         | Atomic update            | `replace()` transaction        |

**Key Prefix Strategy**:

```
/lab-resource-manager/lab-workers/worker-001
/lab-resource-manager/lab-workers/worker-002
/lab-resource-manager/lab-instances/instance-001
```

Each resource type has its own prefix for logical organization and efficient prefix-based queries.

### 2. EtcdLabWorkerResourceRepository

**File**: `integration/repositories/etcd_lab_worker_repository.py`

Extends `ResourceRepository[LabWorkerSpec, LabWorkerStatus]` with LabWorker-specific operations:

**Custom Query Methods**:

```python
# Find by lab track (uses label selector)
workers = await repository.find_by_lab_track_async("comp-sci-101")

# Find by phase (in-memory filtering)
ready_workers = await repository.find_by_phase_async(LabWorkerPhase.READY)

# Find active workers (Ready or Draining)
active = await repository.find_active_workers_async()

# Count operations
count = await repository.count_by_phase_async(LabWorkerPhase.READY)
```

**Real-time Watch**:

```python
def on_worker_change(event):
    if event.type == etcd3.events.PutEvent:
        print(f"Worker added/updated: {event.key}")
    elif event.type == etcd3.events.DeleteEvent:
        print(f"Worker deleted: {event.key}")

# Start watching for changes
watch_id = repository.watch_workers(on_worker_change)

# Later: cancel watch
watch_id.cancel()
```

### 3. Service Registration

**File**: `main.py`

#### etcd Client Registration (Singleton)

```python
# Register etcd client as singleton for resource persistence
etcd_client = etcd3.client(
    host=app_settings.etcd_host,
    port=app_settings.etcd_port,
    timeout=app_settings.etcd_timeout
)
builder.services.try_add_singleton(etcd3.Etcd3Client, singleton=etcd_client)
```

**Why Singleton?**

- Single connection pool shared across application
- Efficient resource usage
- Thread-safe client instance
- Follows etcd best practices

#### Repository Registration (Scoped)

```python
def create_lab_worker_repository(sp):
    """Factory function for EtcdLabWorkerResourceRepository with DI."""
    return EtcdLabWorkerResourceRepository.create_with_json_serializer(
        etcd_client=sp.get_required_service(etcd3.Etcd3Client),
        prefix=f"{app_settings.etcd_prefix}/lab-workers/",
    )

builder.services.add_scoped(
    EtcdLabWorkerResourceRepository,
    implementation_factory=create_lab_worker_repository
)
```

**Why Scoped?**

- One instance per HTTP request
- Proper async context isolation
- Request-scoped caching
- Integration with UnitOfWork patterns

## Configuration

### Application Settings

**File**: `application/settings.py`

```python
# etcd Configuration (Primary persistence for resources)
etcd_host: str = "localhost"
etcd_port: int = 2379
etcd_prefix: str = "/lab-resource-manager"
etcd_timeout: int = 10  # Connection timeout in seconds
```

### Docker Compose

**File**: `deployment/docker-compose/docker-compose.lab-resource-manager.yml`

```yaml
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.10
    container_name: lab-resource-manager-etcd
    environment:
      - ETCD_DATA_DIR=/etcd-data
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd:2379
    ports:
      - "2479:2379" # Client port
      - "2480:2380" # Peer port
    volumes:
      - etcd_data:/etcd-data
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Environment Variables

```bash
# Local development
ETCD_HOST=localhost
ETCD_PORT=2379
ETCD_PREFIX=/lab-resource-manager

# Docker environment
ETCD_HOST=etcd
ETCD_PORT=2379
ETCD_PREFIX=/lab-resource-manager
```

## Usage Examples

### Basic CRUD Operations

```python
# Create a worker
worker = LabWorker(metadata=..., spec=..., status=...)
await repository.add_async(worker)

# Get a worker
worker = await repository.get_async("worker-001")

# Update a worker
worker.status.phase = LabWorkerPhase.READY
await repository.update_async(worker)

# Delete a worker
await repository.delete_async("worker-001")

# List all workers
workers = await repository.list_async()
```

### Custom Queries

```python
# Find workers by lab track
comp_sci_workers = await repository.find_by_lab_track_async("comp-sci-101")

# Find ready workers
ready_workers = await repository.find_ready_workers_async()

# Count workers in a phase
ready_count = await repository.count_by_phase_async(LabWorkerPhase.READY)
```

### Real-time Watching

```python
class WorkerWatchService(HostedService):
    def __init__(self, repository: EtcdLabWorkerResourceRepository):
        self.repository = repository
        self.watch_id = None

    async def start_async(self):
        self.watch_id = self.repository.watch_workers(self.on_worker_change)

    async def stop_async(self):
        if self.watch_id:
            self.watch_id.cancel()

    def on_worker_change(self, event):
        # Handle worker changes in real-time
        logger.info(f"Worker changed: {event.key}")
```

## Dependencies

### Python Package

```toml
# pyproject.toml
[tool.poetry.dependencies]
etcd3 = { version = "^0.12.0", optional = true }

[tool.poetry.extras]
etcd = ["etcd3"]
```

### Installation

```bash
# Install with etcd support
poetry install -E etcd

# Or install directly
pip install etcd3
```

## Testing

### Unit Tests

```python
# Mock etcd client
mock_etcd = Mock(spec=etcd3.Etcd3Client)
backend = EtcdStorageBackend(mock_etcd, "/test/")

# Test operations
await backend.set("worker-001", {"metadata": {...}})
mock_etcd.put.assert_called_once()
```

### Integration Tests

```python
# Use real etcd instance for integration tests
@pytest.fixture
async def etcd_client():
    client = etcd3.client(host="localhost", port=2379)
    yield client
    # Cleanup
    client.delete_prefix("/test/")

async def test_repository_crud(etcd_client):
    repo = EtcdLabWorkerResourceRepository.create_with_json_serializer(
        etcd_client=etcd_client,
        prefix="/test/workers/"
    )

    # Test full CRUD workflow
    worker = LabWorker(...)
    await repo.add_async(worker)
    retrieved = await repo.get_async(worker.id)
    assert retrieved.metadata.name == worker.metadata.name
```

## Performance Considerations

### etcd Best Practices

1. **Key Size**: Keep keys under 1.5 KB
2. **Value Size**: Keep values under 1 MB (etcd default limit)
3. **Watch Efficiency**: Use prefix watches instead of watching individual keys
4. **Batching**: Use transactions for multiple operations
5. **Compaction**: Regularly compact etcd history to free space

### Indexing Strategy

etcd doesn't have secondary indexes, so:

- **Use hierarchical keys** for natural organization
- **Leverage prefix queries** for filtering by resource type
- **Implement label filtering** at application layer
- **Cache frequently accessed data** in memory

## Monitoring

### etcd Metrics

```bash
# Check etcd health
etcdctl endpoint health

# Check etcd status
etcdctl endpoint status

# Monitor key count
etcdctl get / --prefix --keys-only | wc -l
```

### Application Metrics

- Repository operation latency
- Watch callback execution time
- etcd connection pool usage
- Error rates for etcd operations

## Migration from MongoDB

If migrating from MongoDB:

1. **Data Export**: Export resources from MongoDB
2. **Transform**: Convert to etcd key-value format
3. **Import**: Load into etcd with proper key prefixes
4. **Verify**: Test all repository operations
5. **Switch**: Update configuration to use etcd client

## Benefits Summary

✅ **Native Watch API**: Real-time resource updates without polling
✅ **Strong Consistency**: Guaranteed read-after-write consistency
✅ **Atomic Operations**: Safe concurrent updates with CAS
✅ **Kubernetes Alignment**: Same patterns as K8s resource management
✅ **Operational Simplicity**: Less complex than MongoDB replica sets
✅ **Resource Efficiency**: Lower memory footprint for small datasets
✅ **Built-in HA**: Clustering without additional configuration

## References

- **etcd Documentation**: https://etcd.io/docs/
- **etcd3 Python Client**: https://python-etcd3.readthedocs.io/
- **Kubernetes API Patterns**: Uses etcd for all resource storage
- **Lab Resource Manager Sample**: `samples/lab_resource_manager/`
- **ResourceRepository Base**: `src/neuroglia/data/infrastructure/resources/`
