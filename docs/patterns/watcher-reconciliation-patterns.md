# Resource Watcher and Reconciliation Loop Patterns

> **🚧 Work in Progress**: This documentation is being updated to include beginner-friendly explanations with What & Why sections, Common Mistakes, and When NOT to Use guidance. The content below is accurate but will be enhanced soon.

This document explains how the **Resource Watcher** and **Reconciliation Loop** patterns work in our Resource Oriented Architecture (ROA) implementation, providing the foundation for Kubernetes-style declarative resource management.

## 🎯 Overview

The ROA implementation uses two complementary patterns:

1. **Resource Watcher**: Detects changes to resources and emits events
2. **Reconciliation Loop**: Continuously ensures actual state matches desired state

These patterns work together to provide:

- **Declarative Management**: Specify desired state, controllers make it happen
- **Event-Driven Processing**: React to changes as they occur
- **Self-Healing**: Automatically correct drift from desired state
- **Extensibility**: Pluggable controllers for different resource types

## 🔍 Resource Watcher Pattern

### How the Watcher Works

```python
class ResourceWatcherBase(Generic[TResourceSpec, TResourceStatus]):
    """
    The watcher follows a polling pattern:
    1. Periodically lists resources from storage
    2. Compares current state with cached state
    3. Detects changes (CREATED, UPDATED, DELETED, STATUS_UPDATED)
    4. Emits events for detected changes
    5. Updates cache with current state
    """

    async def _watch_loop(self, namespace=None, label_selector=None):
        while self._watching:
            # 1. Get current resources
            current_resources = await self._list_resources(namespace, label_selector)
            current_resource_map = {r.id: r for r in current_resources}

            # 2. Detect changes
            changes = self._detect_changes(current_resource_map)

            # 3. Process each change
            for change in changes:
                await self._process_change(change)

            # 4. Update cache
            self._resource_cache = current_resource_map

            # 5. Wait before next poll
            await asyncio.sleep(self.watch_interval)
```

### Change Detection Logic

The watcher detects four types of changes:

```python
def _detect_changes(self, current_resources):
    changes = []
    current_ids = set(current_resources.keys())
    cached_ids = set(self._resource_cache.keys())

    # 1. CREATED: New resources that weren't in cache
    for resource_id in current_ids - cached_ids:
        changes.append(ResourceChangeEvent(
            change_type=ResourceChangeType.CREATED,
            resource=current_resources[resource_id]
        ))

    # 2. DELETED: Cached resources no longer present
    for resource_id in cached_ids - current_ids:
        changes.append(ResourceChangeEvent(
            change_type=ResourceChangeType.DELETED,
            resource=self._resource_cache[resource_id]
        ))

    # 3. UPDATED: Spec changed (generation increment)
    # 4. STATUS_UPDATED: Status changed (observed generation, etc.)
    for resource_id in current_ids & cached_ids:
        current = current_resources[resource_id]
        cached = self._resource_cache[resource_id]

        if current.metadata.generation > cached.metadata.generation:
            # Spec was updated
            changes.append(ResourceChangeEvent(
                change_type=ResourceChangeType.UPDATED,
                resource=current,
                old_resource=cached
            ))
        elif self._has_status_changed(current, cached):
            # Status was updated
            changes.append(ResourceChangeEvent(
                change_type=ResourceChangeType.STATUS_UPDATED,
                resource=current,
                old_resource=cached
            ))

    return changes
```

### Event Processing and Publishing

When changes are detected, the watcher:

```python
async def _process_change(self, change):
    # 1. Call registered change handlers
    for handler in self._change_handlers:
        if asyncio.iscoroutinefunction(handler):
            await handler(change)
        else:
            handler(change)

    # 2. Publish CloudEvent
    await self._publish_change_event(change)

async def _publish_change_event(self, change):
    event_type = f"{resource.kind.lower()}.{change.change_type.value.lower()}"

    event = CloudEvent(
        source=f"watcher/{resource.kind.lower()}",
        type=event_type,  # e.g., "labinstancerequest.created"
        subject=f"{resource.metadata.namespace}/{resource.metadata.name}",
        data={
            "resourceUid": resource.id,
            "apiVersion": resource.api_version,
            "kind": resource.kind,
            "changeType": change.change_type.value,
            "generation": resource.metadata.generation,
            "observedGeneration": resource.status.observed_generation
        }
    )

    await self.event_publisher.publish_async(event)
```

## 🔄 Reconciliation Loop Pattern

### How Reconciliation Works

```python
class ResourceControllerBase(Generic[TResourceSpec, TResourceStatus]):
    """
    Controllers implement the reconciliation pattern:
    1. Receive resource change events
    2. Compare current state with desired state
    3. Take actions to move toward desired state
    4. Update resource status
    5. Emit reconciliation events
    """

    async def reconcile(self, resource):
        # 1. Check if reconciliation is needed
        if not resource.needs_reconciliation():
            return

        # 2. Execute reconciliation with timeout
        result = await asyncio.wait_for(
            self._do_reconcile(resource),
            timeout=self._reconciliation_timeout.total_seconds()
        )

        # 3. Handle result (success, failure, requeue)
        await self._handle_reconciliation_result(resource, result)
```

### Reconciliation States

Controllers can return different reconciliation results:

```python
class ReconciliationStatus(Enum):
    SUCCESS = "Success"          # Reconciliation completed successfully
    FAILED = "Failed"            # Reconciliation failed, needs attention
    REQUEUE = "Requeue"          # Retry immediately
    REQUEUE_AFTER = "RequeueAfter"  # Retry after specified delay

# Example usage in controller
async def _do_reconcile(self, resource):
    if resource.status.phase == LabInstancePhase.PENDING:
        if resource.should_start_now():
            success = await self._start_lab_instance(resource)
            return ReconciliationResult.success() if success else ReconciliationResult.requeue()
        else:
            # Not time to start yet, check again in 30 seconds
            return ReconciliationResult.requeue_after(timedelta(seconds=30))

    elif resource.status.phase == LabInstancePhase.RUNNING:
        if resource.is_expired():
            await self._stop_lab_instance(resource)
            return ReconciliationResult.success()
        else:
            # Check again when it should expire
            remaining = resource.get_remaining_duration()
            return ReconciliationResult.requeue_after(remaining)
```

## 🔧 Integration Patterns

### Pattern 1: Watcher → Controller Integration

```python
# Watcher detects changes and triggers controller
class LabInstanceWatcher(ResourceWatcherBase[LabInstanceRequestSpec, LabInstanceRequestStatus]):
    def __init__(self, repository, controller, event_publisher):
        super().__init__(event_publisher)
        self.repository = repository
        self.controller = controller

        # Register controller as change handler
        self.add_change_handler(self._handle_resource_change)

    async def _list_resources(self, namespace=None, label_selector=None):
        return await self.repository.list_async(namespace=namespace)

    async def _handle_resource_change(self, change):
        """Called when resource changes are detected."""
        resource = change.resource

        if change.change_type in [ResourceChangeType.CREATED, ResourceChangeType.UPDATED]:
            # Trigger reconciliation for created or updated resources
            await self.controller.reconcile(resource)
        elif change.change_type == ResourceChangeType.DELETED:
            # Trigger finalization for deleted resources
            await self.controller.finalize(resource)
```

### Pattern 2: Background Scheduler as Reconciliation Loop

```python
class LabInstanceSchedulerService(HostedService):
    """
    Background service that acts as a reconciliation loop:
    1. Periodically scans all resources
    2. Identifies resources that need reconciliation
    3. Applies appropriate actions
    4. Updates resource status
    """

    async def _run_scheduler_loop(self):
        while self._running:
            # Reconciliation phases
            await self._process_scheduled_instances()  # PENDING → PROVISIONING
            await self._process_running_instances()    # RUNNING monitoring
            await self._cleanup_expired_instances()    # TIMEOUT/CLEANUP

            await asyncio.sleep(self._scheduler_interval)

    async def _process_scheduled_instances(self):
        """Reconcile PENDING resources that should be started."""
        pending_instances = await self.repository.find_by_phase_async(LabInstancePhase.PENDING)

        for instance in pending_instances:
            if instance.should_start_now():
                # Move toward desired state: PENDING → PROVISIONING → RUNNING
                await self._start_lab_instance(instance)

    async def _process_running_instances(self):
        """Reconcile RUNNING resources for completion/errors."""
        running_instances = await self.repository.find_by_phase_async(LabInstancePhase.RUNNING)

        for instance in running_instances:
            # Check actual container state vs desired state
            container_status = await self.container_service.get_container_status_async(
                instance.status.container_id
            )

            if container_status == "stopped":
                # Actual state differs from desired, reconcile
                await self._complete_lab_instance(instance)
            elif instance.is_expired():
                # Policy violation, enforce timeout
                await self._timeout_lab_instance(instance)
```

### Pattern 3: Event-Driven Reconciliation

```python
class LabInstanceEventHandler:
    """Handle resource events and trigger reconciliation."""

    async def handle_lab_instance_created(self, event):
        """When a lab instance is created, ensure it's properly scheduled."""
        resource_id = event.data["resourceUid"]
        resource = await self.repository.get_by_id_async(resource_id)

        if resource and resource.status.phase == LabInstancePhase.PENDING:
            # Ensure resource is in scheduling queue
            await self.controller.reconcile(resource)

    async def handle_lab_instance_updated(self, event):
        """When a lab instance is updated, re-reconcile."""
        resource_id = event.data["resourceUid"]
        resource = await self.repository.get_by_id_async(resource_id)

        if resource:
            await self.controller.reconcile(resource)

    async def handle_container_event(self, event):
        """When container state changes, update resource status."""
        container_id = event.data["containerId"]

        # Find resource with this container
        instances = await self.repository.find_by_container_id_async(container_id)

        for instance in instances:
            # Reconcile to reflect new container state
            await self.controller.reconcile(instance)
```

## 🚀 Complete Integration Example

Here's how all patterns work together:

```python
# 1. Setup watcher and controller
watcher = LabInstanceWatcher(repository, controller, event_publisher)
scheduler = LabInstanceSchedulerService(repository, container_service, event_bus)

# 2. Start background processes
await watcher.watch(namespace="default")
await scheduler.start_async()

# 3. Create a resource (triggers CREATED event)
lab_instance = LabInstanceRequest(...)
await repository.save_async(lab_instance)

# 4. Watcher detects CREATED event
# 5. Watcher calls controller.reconcile(lab_instance)
# 6. Controller checks if action needed (should_start_now?)
# 7. If not time yet, controller returns REQUEUE_AFTER
# 8. Scheduler loop independently checks all PENDING resources
# 9. When time arrives, scheduler starts the lab instance
# 10. Status update triggers STATUS_UPDATED event
# 11. Watcher publishes CloudEvent
# 12. Other services can react to the event
```

## 📊 Observability and Monitoring

Both patterns provide rich observability:

### Watcher Metrics

```python
watcher_metrics = {
    "is_watching": watcher.is_watching(),
    "cached_resources": watcher.get_cached_resource_count(),
    "watch_interval": watcher.watch_interval,
    "events_published": watcher.events_published_count,
    "change_handlers": len(watcher._change_handlers)
}
```

### Controller Metrics

```python
controller_metrics = {
    "reconciliations_total": controller.reconciliation_count,
    "reconciliations_successful": controller.success_count,
    "reconciliations_failed": controller.failure_count,
    "average_reconciliation_duration": controller.avg_duration,
    "pending_reconciliations": controller.queue_size
}
```

### Scheduler Metrics

```python
scheduler_metrics = {
    "running": scheduler._running,
    "scheduler_interval": scheduler._scheduler_interval,
    "instances_by_phase": {
        phase.value: await repository.count_by_phase_async(phase)
        for phase in LabInstancePhase
    },
    "processed_this_cycle": scheduler.processed_count
}
```

## ⚙️ Configuration and Tuning

### Watcher Configuration

```python
watcher = LabInstanceWatcher(
    repository=repository,
    controller=controller,
    event_publisher=event_publisher,
    watch_interval=5.0  # Poll every 5 seconds
)
```

### Controller Configuration

```python
controller = LabInstanceController(
    service_provider=service_provider,
    event_publisher=event_publisher
)
controller._reconciliation_timeout = timedelta(minutes=10)
controller._max_retry_attempts = 5
```

### Scheduler Configuration

```python
scheduler = LabInstanceSchedulerService(
    repository=repository,
    container_service=container_service,
    event_bus=event_bus
)
scheduler._scheduler_interval = 30      # 30 second reconciliation loop
scheduler._cleanup_interval = 300       # 5 minute cleanup cycle
```

This architecture provides a robust, observable, and extensible foundation for managing resources in a declarative, Kubernetes-style manner while integrating seamlessly with traditional CQRS patterns.
