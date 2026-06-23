# How Watcher and Reconciliation Loop Execute

> **🚧 Work in Progress**: This documentation is being updated to include beginner-friendly explanations with What & Why sections, Common Mistakes, and When NOT to Use guidance. The content below is accurate but will be enhanced soon.

This document provides a detailed explanation of how the **Resource Watcher** and **Reconciliation Loop** patterns execute in our Resource Oriented Architecture (ROA) implementation.

## 🔄 Execution Flow Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Resource       │    │  Resource       │    │  Background     │
│  Watcher        │    │  Controller     │    │  Scheduler      │
│                 │    │                 │    │                 │
│ • Polls storage │───▶│ • Reconciles    │◄──▶│ • Monitors all  │
│ • Detects Δ     │    │   resources     │    │   resources     │
│ • Emits events  │    │ • Updates state │    │ • Enforces      │
│ • Triggers      │    │ • Publishes     │    │   lifecycle     │
│   reconciliation│    │   events        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │    Event Bus &          │
                    │  Cloud Events           │
                    │                         │
                    │ • Resource created      │
                    │ • Resource updated      │
                    │ • Status changed        │
                    │ • Reconciliation done   │
                    └─────────────────────────┘
```

## 1️⃣ Resource Watcher Execution

### Polling Loop Implementation

```python
class ResourceWatcherBase:
    async def _watch_loop(self, namespace=None, label_selector=None):
        """
        Main watch loop - executes continuously:

        1. List current resources from storage
        2. Compare with cached resources
        3. Detect changes (CREATED, UPDATED, DELETED, STATUS_UPDATED)
        4. Process each change
        5. Update cache
        6. Sleep until next poll
        """
        while self._watching:
            try:
                # STEP 1: Get current state from storage
                current_resources = await self._list_resources(namespace, label_selector)
                current_resource_map = {r.id: r for r in current_resources}

                # STEP 2: Detect changes by comparing with cache
                changes = self._detect_changes(current_resource_map)

                # STEP 3: Process each detected change
                for change in changes:
                    await self._process_change(change)

                # STEP 4: Update cache with current state
                self._resource_cache = current_resource_map

                # STEP 5: Wait before next poll
                await asyncio.sleep(self.watch_interval)

            except Exception as e:
                log.error(f"Error in watch loop: {e}")
                await asyncio.sleep(self.watch_interval)
```

### Change Detection Algorithm

```python
def _detect_changes(self, current_resources):
    """
    Change detection compares current vs cached state:

    • CREATED: resource_id in current but not in cache
    • DELETED: resource_id in cache but not in current
    • UPDATED: generation increased (spec changed)
    • STATUS_UPDATED: status fields changed
    """
    changes = []
    current_ids = set(current_resources.keys())
    cached_ids = set(self._resource_cache.keys())

    # New resources (CREATED)
    for resource_id in current_ids - cached_ids:
        changes.append(ResourceChangeEvent(
            change_type=ResourceChangeType.CREATED,
            resource=current_resources[resource_id]
        ))

    # Deleted resources (DELETED)
    for resource_id in cached_ids - current_ids:
        changes.append(ResourceChangeEvent(
            change_type=ResourceChangeType.DELETED,
            resource=self._resource_cache[resource_id]
        ))

    # Modified resources (UPDATED/STATUS_UPDATED)
    for resource_id in current_ids & cached_ids:
        current = current_resources[resource_id]
        cached = self._resource_cache[resource_id]

        # Spec changed (generation incremented)
        if current.metadata.generation > cached.metadata.generation:
            changes.append(ResourceChangeEvent(
                change_type=ResourceChangeType.UPDATED,
                resource=current,
                old_resource=cached
            ))
        # Status changed
        elif self._has_status_changed(current, cached):
            changes.append(ResourceChangeEvent(
                change_type=ResourceChangeType.STATUS_UPDATED,
                resource=current,
                old_resource=cached
            ))

    return changes
```

### Event Processing and Controller Triggering

```python
async def _process_change(self, change):
    """
    When changes are detected:

    1. Call registered change handlers (like controllers)
    2. Publish CloudEvents to event bus
    3. Handle errors gracefully
    """
    # STEP 1: Call all registered handlers
    for handler in self._change_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(change)  # Triggers controller reconciliation
            else:
                handler(change)
        except Exception as e:
            log.error(f"Change handler failed: {e}")

    # STEP 2: Publish event to broader system
    await self._publish_change_event(change)

# Example: Lab Instance Watcher
class LabInstanceWatcher(ResourceWatcherBase):
    def __init__(self, repository, controller, event_publisher):
        super().__init__(event_publisher)
        # Register controller as change handler
        self.add_change_handler(self._handle_resource_change)

    async def _handle_resource_change(self, change):
        """Called automatically when changes detected"""
        if change.change_type in [ResourceChangeType.CREATED, ResourceChangeType.UPDATED]:
            # Trigger reconciliation for new/updated resources
            await self.controller.reconcile(change.resource)
        elif change.change_type == ResourceChangeType.DELETED:
            # Trigger cleanup for deleted resources
            await self.controller.finalize(change.resource)
```

## 2️⃣ Reconciliation Loop Execution

### Controller Reconciliation Pattern

```python
class ResourceControllerBase:
    async def reconcile(self, resource):
        """
        Main reconciliation entry point:

        1. Check if reconciliation is needed
        2. Execute reconciliation logic with timeout
        3. Handle results (success, failure, requeue)
        4. Update resource status
        5. Emit reconciliation events
        """
        start_time = datetime.now()

        try:
            # STEP 1: Check if reconciliation needed
            if not resource.needs_reconciliation():
                log.debug(f"Resource {resource.metadata.name} does not need reconciliation")
                return

            # STEP 2: Execute reconciliation with timeout
            result = await asyncio.wait_for(
                self._do_reconcile(resource),
                timeout=self._reconciliation_timeout.total_seconds()
            )

            # STEP 3: Handle reconciliation result
            await self._handle_reconciliation_result(resource, result, start_time)

        except asyncio.TimeoutError:
            await self._handle_reconciliation_error(resource, TimeoutError(), start_time)
        except Exception as e:
            await self._handle_reconciliation_error(resource, e, start_time)
```

### Lab Instance Controller Implementation

```python
class LabInstanceController(ResourceControllerBase):
    async def _do_reconcile(self, resource: LabInstanceRequest):
        """
        Lab-specific reconciliation logic:

        • PENDING → PROVISIONING: Check if should start
        • PROVISIONING → RUNNING: Start container
        • RUNNING → COMPLETED: Monitor completion
        • Handle errors and timeouts
        """
        current_phase = resource.status.phase

        if current_phase == LabInstancePhase.PENDING:
            if resource.should_start_now():
                # Time to start - provision container
                success = await self._provision_lab_instance(resource)
                return ReconciliationResult.success() if success else ReconciliationResult.requeue()
            else:
                # Not time yet - requeue when it should start
                remaining_time = resource.get_time_until_start()
                return ReconciliationResult.requeue_after(remaining_time)

        elif current_phase == LabInstancePhase.PROVISIONING:
            # Check if container is ready
            if await self._is_container_ready(resource):
                resource.transition_to_running()
                await self._repository.save_async(resource)
                return ReconciliationResult.success()
            else:
                # Still provisioning - check again soon
                return ReconciliationResult.requeue_after(timedelta(seconds=30))

        elif current_phase == LabInstancePhase.RUNNING:
            # Monitor for completion or timeout
            if resource.is_expired():
                await self._timeout_lab_instance(resource)
                return ReconciliationResult.success()
            else:
                # Check again when it should expire
                remaining_time = resource.get_remaining_duration()
                return ReconciliationResult.requeue_after(remaining_time)

        # No action needed for terminal phases
        return ReconciliationResult.success()
```

## 3️⃣ Background Scheduler as Reconciliation Loop

### Scheduler Service Implementation

```python
class LabInstanceSchedulerService(HostedService):
    """
    Background service that acts as a reconciliation loop:

    • Runs independently of watchers
    • Periodically scans all resources
    • Applies policies and enforces state
    • Handles bulk operations
    """

    async def _run_scheduler_loop(self):
        """Main scheduler loop - runs continuously"""
        cleanup_counter = 0

        while self._running:
            try:
                # PHASE 1: Process scheduled instances (PENDING → PROVISIONING)
                await self._process_scheduled_instances()

                # PHASE 2: Monitor running instances (RUNNING state health)
                await self._process_running_instances()

                # PHASE 3: Periodic cleanup (expired/failed instances)
                cleanup_counter += self._scheduler_interval
                if cleanup_counter >= self._cleanup_interval:
                    await self._cleanup_expired_instances()
                    cleanup_counter = 0

                # Wait before next iteration
                await asyncio.sleep(self._scheduler_interval)

            except Exception as e:
                log.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self._scheduler_interval)

    async def _process_scheduled_instances(self):
        """Reconcile PENDING instances that should start"""
        try:
            # Find all pending instances that are scheduled
            pending_instances = await self._repository.find_scheduled_pending_async()

            for instance in pending_instances:
                if instance.should_start_now():
                    # Move toward desired state: PENDING → PROVISIONING → RUNNING
                    await self._start_lab_instance(instance)

        except Exception as e:
            log.error(f"Error processing scheduled instances: {e}")

    async def _process_running_instances(self):
        """Reconcile RUNNING instances for health/completion"""
        try:
            running_instances = await self._repository.find_running_instances_async()

            for instance in running_instances:
                # Check actual container state vs desired state
                container_status = await self._container_service.get_container_status_async(
                    instance.status.container_id
                )

                # Reconcile based on actual vs desired state
                if container_status == "stopped":
                    # Container stopped - instance should complete
                    await self._complete_lab_instance(instance)
                elif container_status == "error":
                    # Container errored - instance should fail
                    await self._fail_lab_instance(instance, "Container error")
                elif instance.is_expired():
                    # Policy violation - enforce timeout
                    await self._timeout_lab_instance(instance)

        except Exception as e:
            log.error(f"Error processing running instances: {e}")
```

## 4️⃣ Integration Patterns and Event Flow

### Complete Event Flow Example

```
1. User creates LabInstanceRequest
   └─ Resource saved to storage

2. Watcher detects CREATED event (next poll cycle)
   ├─ Publishes labinstancerequest.created CloudEvent
   └─ Triggers controller.reconcile(resource)

3. Controller reconciliation
   ├─ Checks: resource.should_start_now() → false (scheduled for later)
   └─ Returns: ReconciliationResult.requeue_after(delay)

4. Scheduler loop (independent polling)
   ├─ Finds pending instances that should start
   ├─ Calls _start_lab_instance(resource)
   │  ├─ Transitions: PENDING → PROVISIONING
   │  ├─ Creates container
   │  └─ Transitions: PROVISIONING → RUNNING
   └─ Updates resource status in storage

5. Watcher detects STATUS_UPDATED event
   ├─ Publishes labinstancerequest.status_updated CloudEvent
   └─ Triggers controller.reconcile(resource) again

6. Controller reconciliation (RUNNING phase)
   ├─ Calculates when instance should expire
   └─ Returns: ReconciliationResult.requeue_after(remaining_time)

7. Time passes... scheduler monitors container health

8. Container completes/fails/times out
   ├─ Scheduler detects state change
   ├─ Updates resource: RUNNING → COMPLETED/FAILED/TIMEOUT
   └─ Cleans up container resources

9. Watcher detects final STATUS_UPDATED event
   ├─ Publishes final CloudEvent
   └─ Controller reconciliation confirms no action needed
```

### Timing and Coordination

| Component      | Frequency     | Purpose                                         |
| -------------- | ------------- | ----------------------------------------------- |
| **Watcher**    | 5-10 seconds  | Detect changes, trigger reactive reconciliation |
| **Scheduler**  | 30-60 seconds | Proactive reconciliation, policy enforcement    |
| **Controller** | Event-driven  | Handle specific resource changes                |

### Error Handling and Resilience

```python
# Watcher error handling
async def _watch_loop(self):
    while self._watching:
        try:
            # Process changes
            pass
        except Exception as e:
            log.error(f"Watch loop error: {e}")
            await asyncio.sleep(self.watch_interval)  # Continue watching

# Controller error handling
async def reconcile(self, resource):
    try:
        result = await asyncio.wait_for(self._do_reconcile(resource), timeout=300)
    except asyncio.TimeoutError:
        # Handle timeout - mark for retry
        result = ReconciliationResult.requeue()
    except Exception as e:
        # Handle error - exponential backoff
        result = ReconciliationResult.failed(e)

# Scheduler error handling
async def _run_scheduler_loop(self):
    while self._running:
        try:
            # Process all phases
            pass
        except Exception as e:
            log.error(f"Scheduler error: {e}")
            await asyncio.sleep(self._scheduler_interval)  # Continue scheduling
```

## 📊 Observability and Monitoring

### Key Metrics to Monitor

```python
# Watcher metrics
{
    "watch_loop_iterations": 1234,
    "changes_detected": 56,
    "events_published": 78,
    "cache_hit_ratio": 0.95,
    "average_poll_duration": "150ms"
}

# Controller metrics
{
    "reconciliations_total": 234,
    "reconciliations_successful": 220,
    "reconciliations_failed": 4,
    "reconciliations_requeued": 10,
    "average_reconciliation_time": "2.3s"
}

# Scheduler metrics
{
    "scheduler_loop_iterations": 567,
    "resources_processed": 890,
    "state_transitions": 123,
    "cleanup_operations": 45,
    "average_loop_duration": "5.2s"
}
```

This architecture provides a robust, scalable foundation for declarative resource management that automatically maintains desired state while being resilient to failures and providing comprehensive observability.
