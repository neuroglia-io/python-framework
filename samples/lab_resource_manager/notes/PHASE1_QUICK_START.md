# Phase 1 Features - Quick Start Guide

This guide helps you quickly get started with the new Phase 1 production-ready features:

- Finalizers
- Leader Election
- Watch Bookmarks
- Conflict Resolution

## Prerequisites

```bash
# Install Redis (required for leader election and bookmarks)
docker run -d -p 6379:6379 --name redis redis:latest

# Install MongoDB (for resource storage)
docker run -d -p 27017:27017 --name mongo mongo:latest

# Verify connectivity
redis-cli ping  # Should return PONG
mongo --eval "db.version()"  # Should show MongoDB version
```

## Quick Start: Finalizers

### 1. Add Finalizer to Controller

```python
from neuroglia.data.resources.controller import ResourceControllerBase

class MyController(ResourceControllerBase):
    def __init__(self, service_provider):
        super().__init__(service_provider)
        # Set finalizer name for automatic management
        self.finalizer_name = "my-controller.example.com"

    async def finalize(self, resource) -> bool:
        """Called when resource is being deleted."""
        # Clean up external resources
        await self.cleanup_containers(resource)
        await self.release_storage(resource)
        return True  # True = cleanup successful
```

### 2. Controller Automatically Manages Finalizer

```python
# During reconciliation:
# - Finalizer is added to resources
# - On deletion, finalize() is called
# - Finalizer is removed after successful cleanup
# - Resource can then be deleted

await controller.reconcile(resource)
```

### 3. Manual Finalizer Management

```python
# Check for finalizers
if resource.metadata.has_finalizer("my-controller.example.com"):
    # Do something

# Add custom finalizer
resource.metadata.add_finalizer("storage.example.com")

# Remove finalizer
resource.metadata.remove_finalizer("storage.example.com")

# Check if being deleted
if resource.metadata.is_being_deleted():
    # Resource has deletion_timestamp set
    await cleanup_resources(resource)
```

## Quick Start: Leader Election

### 1. Setup Redis Backend

```python
from redis.asyncio import Redis
from neuroglia.coordination import (
    LeaderElection,
    LeaderElectionConfig,
    RedisCoordinationBackend
)

# Create Redis client
redis_client = Redis.from_url("redis://localhost:6379")
backend = RedisCoordinationBackend(redis_client)
```

### 2. Configure Leader Election

```python
from datetime import timedelta

config = LeaderElectionConfig(
    lock_name="my-controller-leader",  # Shared across all instances
    identity="instance-1",             # Unique per instance
    lease_duration=timedelta(seconds=15),
    renew_deadline=timedelta(seconds=10),
    retry_period=timedelta(seconds=2)
)
```

### 3. Create Election and Attach to Controller

```python
election = LeaderElection(
    config=config,
    backend=backend,
    on_start_leading=lambda: print("🎉 Became leader!"),
    on_stop_leading=lambda: print("🔄 Lost leadership")
)

# Attach to controller
controller.leader_election = election

# Start election in background
election_task = asyncio.create_task(election.run())
```

### 4. Check Leadership

```python
if election.is_leader():
    # This instance is the active leader
    await perform_reconciliation()
else:
    # This instance is on standby
    await wait_for_leadership()
```

## Quick Start: Watch Bookmarks

### 1. Setup Bookmark Storage

```python
from redis.asyncio import Redis
from neuroglia.data.resources import ResourceWatcherBase

# Create Redis client for bookmarks (use separate DB)
redis_bookmarks = Redis.from_url("redis://localhost:6379/1", decode_responses=True)
```

### 2. Create Watcher with Bookmark Support

```python
class MyResourceWatcher(ResourceWatcherBase):
    def __init__(self, controller, redis_client, instance_id):
        super().__init__(
            controller=controller,
            poll_interval=timedelta(seconds=5),
            bookmark_storage=redis_client,  # Enable bookmarks
            bookmark_key=f"my-watcher:{instance_id}"  # Unique per instance
        )

    async def handle_async(self, resource):
        # Process resource
        await self.controller.reconcile(resource)
        # Bookmark automatically saved after this completes
```

### 3. Start Watcher

```python
watcher = MyResourceWatcher(
    controller=controller,
    redis_client=redis_bookmarks,
    instance_id="instance-1"
)

# watch() automatically loads bookmark on start
await watcher.watch()

# After crash/restart:
# - Bookmark is loaded
# - Watcher resumes from last processed version
# - No events are lost or duplicated
```

### 4. Monitor Bookmarks

```python
# Check current bookmark
bookmark = await redis_bookmarks.get("my-watcher:instance-1")
print(f"Last processed version: {bookmark}")

# Clear bookmark (force reprocessing)
await redis_bookmarks.delete("my-watcher:instance-1")
```

## Quick Start: Conflict Resolution

### 1. Basic Update with Conflict Detection

```python
from neuroglia.data.resources import ResourceConflictError
from neuroglia.data.infrastructure.resources import ResourceRepository

repository = ResourceRepository(...)

try:
    await repository.update_async(resource)
except ResourceConflictError as e:
    # Resource was modified by another instance
    print(f"Conflict: {e}")
    # Load fresh version
    fresh_resource = await repository.get_by_id_async(resource.metadata.name)
    # Retry with fresh data
    await repository.update_async(fresh_resource)
```

### 2. Automatic Retry on Conflict

```python
# update_with_retry_async automatically handles conflicts
# Retries up to 3 times with fresh version on each attempt
await repository.update_with_retry_async(resource)

# This is equivalent to:
# for attempt in range(3):
#     try:
#         await repository.update_async(resource)
#         break
#     except ResourceConflictError:
#         if attempt < 2:
#             resource = await repository.get_by_id_async(resource.metadata.name)
#         else:
#             raise
```

### 3. Custom Retry Logic

```python
async def update_with_custom_retry(repository, resource, max_retries=5):
    for attempt in range(max_retries):
        try:
            await repository.update_async(resource)
            return True
        except ResourceConflictError:
            if attempt < max_retries - 1:
                # Load fresh version
                resource = await repository.get_by_id_async(
                    resource.metadata.name,
                    resource.metadata.namespace
                )
                # Apply changes to fresh version
                resource.status.phase = "UPDATED"
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
            else:
                raise
    return False
```

## Complete Example: Production-Ready Controller

```python
import asyncio
from datetime import timedelta
from redis.asyncio import Redis

from neuroglia.coordination import (
    LeaderElection, LeaderElectionConfig, RedisCoordinationBackend
)
from neuroglia.data.resources import ResourceWatcherBase, ResourceControllerBase

class ProductionController(ResourceControllerBase):
    def __init__(self, service_provider, instance_id: str):
        super().__init__(service_provider)
        self.instance_id = instance_id
        self.finalizer_name = f"my-controller.example.com/{instance_id}"

    async def _do_reconcile(self, resource):
        # Your reconciliation logic
        return ReconciliationResult.success()

    async def finalize(self, resource) -> bool:
        # Cleanup logic
        await self.cleanup_external_resources(resource)
        return True

class ProductionWatcher(ResourceWatcherBase):
    def __init__(self, controller, bookmark_storage, instance_id):
        super().__init__(
            controller=controller,
            poll_interval=timedelta(seconds=5),
            bookmark_storage=bookmark_storage,
            bookmark_key=f"watcher:{instance_id}"
        )

    async def handle_async(self, resource):
        await self.controller.reconcile(resource)

async def main():
    instance_id = "instance-1"

    # Setup Redis
    redis = Redis.from_url("redis://localhost:6379")
    redis_bookmarks = Redis.from_url("redis://localhost:6379/1", decode_responses=True)

    # Create controller
    controller = ProductionController(service_provider, instance_id)

    # Setup leader election
    election = LeaderElection(
        config=LeaderElectionConfig(
            lock_name="my-controller-leader",
            identity=instance_id,
            lease_duration=timedelta(seconds=15)
        ),
        backend=RedisCoordinationBackend(redis)
    )
    controller.leader_election = election

    # Create watcher with bookmarks
    watcher = ProductionWatcher(controller, redis_bookmarks, instance_id)

    # Start everything
    election_task = asyncio.create_task(election.run())
    watcher_task = asyncio.create_task(watcher.watch())

    await asyncio.gather(election_task, watcher_task)

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### Leader Election Issues

```bash
# Check Redis connectivity
redis-cli ping

# Monitor leader election in Redis
redis-cli GET my-controller-leader

# Check lease expiration
redis-cli TTL my-controller-leader
```

### Bookmark Issues

```bash
# Check bookmark value
redis-cli -n 1 GET "watcher:instance-1"

# List all bookmarks
redis-cli -n 1 KEYS "watcher:*"

# Reset bookmark
redis-cli -n 1 DEL "watcher:instance-1"
```

### Conflict Resolution Issues

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Monitor conflict rate
conflict_count = 0
try:
    await repository.update_async(resource)
except ResourceConflictError:
    conflict_count += 1
    print(f"Conflicts: {conflict_count}")
```

## Next Steps

- Read the [ROA Implementation Status](../../../notes/ROA_IMPLEMENTATION_STATUS_AND_ROADMAP.md)
- Review [Lab Resource Manager demos](README.md#-demo-applications)
- Check [Production Deployment](README.md#-production-deployment) guide
- Explore Phase 2 features (coming soon)
