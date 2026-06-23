# 🧪 Lab Resource Manager Sample Application

The Lab Resource Manager demonstrates Resource Oriented Architecture (ROA) patterns using Neuroglia's advanced features. It simulates a system for managing ephemeral lab environments for students, showcasing watchers, controllers, and reconciliation loops.

## 🎯 What You'll Learn

- **Resource Oriented Architecture**: Declarative resource management patterns
- **Watcher Pattern**: Continuous monitoring of resource changes
- **Controller Pattern**: Event-driven business logic responses
- **Reconciliation Loops**: Periodic consistency checks and drift correction
- **State Machine Implementation**: Resource lifecycle management
- **Asynchronous Coordination**: Multiple concurrent components working together

## 🏗️ Architecture

```text
┌────────────────────────────────────────────────────────────────────┐
│                    Lab Resource Manager                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Watcher       │    │   Controller    │    │  Reconciler     │ │
│  │   (2s polling)  │───▶│   (immediate)   │    │   (10s loop)    │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│           │                       │                       │        │
│           ▼                       ▼                       ▼        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Resource Storage                           │ │
│  │            (Kubernetes-like API with versioning)              │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## 🎯 Domain Model

### LabInstance Resource

The core resource representing a student lab environment:

```python
@dataclass
class LabInstanceResource:
    api_version: str = "lab.neuroglia.com/v1"
    kind: str = "LabInstance"
    metadata: Dict[str, Any] = None  # Name, namespace, timestamps, versions
    spec: Dict[str, Any] = None      # Desired state: template, duration, student
    status: Dict[str, Any] = None    # Current state: phase, endpoint, conditions
```

### Resource States

Lab instances progress through a defined lifecycle:

```text
PENDING ──→ PROVISIONING ──→ READY ──→ DELETING ──→ DELETED
   │              │             │
   ▼              ▼             ▼
FAILED        FAILED         FAILED
```

### Sample Resource

```json
{
  "apiVersion": "lab.neuroglia.com/v1",
  "kind": "LabInstance",
  "metadata": {
    "name": "python-basics-lab",
    "namespace": "student-labs",
    "resourceVersion": "1",
    "creationTimestamp": "2025-09-09T21:34:19Z"
  },
  "spec": {
    "template": "python-basics",
    "studentEmail": "student@example.com",
    "duration": "60m",
    "environment": {
      "PYTHON_VERSION": "3.11"
    }
  },
  "status": {
    "state": "ready",
    "message": "Lab instance is ready",
    "endpoint": "https://lab-python-basics.example.com",
    "readyAt": "2025-09-09T21:34:25Z"
  }
}
```

## 🔧 Component Implementation

### 1. Watcher: LabInstanceWatcher

Continuously monitors for resource changes:

```python
class LabInstanceWatcher:
    async def start_watching(self):
        while self.is_running:
            # Poll for changes since last known version
            changes = self.storage.list_resources(since_version=self.last_resource_version)

            for resource in changes:
                resource_version = int(resource.metadata.get('resourceVersion', '0'))
                if resource_version > self.last_resource_version:
                    await self._handle_resource_change(resource)
                    self.last_resource_version = max(self.last_resource_version, resource_version)

            await asyncio.sleep(self.poll_interval)
```

**Key Features:**

- Polls every 2 seconds for near-real-time responsiveness
- Uses resource versioning to detect changes efficiently
- Notifies multiple event handlers when changes occur
- Handles errors gracefully with continued monitoring

### 2. Controller: LabInstanceController

Implements business logic for state transitions:

```python
class LabInstanceController:
    async def handle_resource_event(self, resource: LabInstanceResource):
        current_state = resource.status.get('state')

        if current_state == ResourceState.PENDING.value:
            await self._start_provisioning(resource)
        elif current_state == ResourceState.PROVISIONING.value:
            await self._check_provisioning_status(resource)
        elif current_state == ResourceState.READY.value:
            await self._monitor_lab_instance(resource)
```

**Key Features:**

- Event-driven processing responding immediately to changes
- State machine implementation with clear transitions
- Business rule enforcement (timeouts, validation, etc.)
- Integration with external provisioning systems

### 3. Reconciler: LabInstanceScheduler

Provides safety and eventual consistency:

```python
class LabInstanceScheduler:
    async def start_reconciliation(self):
        while self.is_running:
            await self._reconcile_all_resources()
            await asyncio.sleep(self.reconcile_interval)

    async def _reconcile_resource(self, resource):
        # Check for stuck states
        if self._is_stuck_provisioning(resource):
            await self._mark_as_failed(resource, "Provisioning timeout")

        # Check for expiration
        if self._is_expired(resource):
            await self._schedule_deletion(resource)
```

**Key Features:**

- Runs every 10 seconds scanning all resources
- Detects stuck states and takes corrective action
- Enforces business policies (lab expiration, cleanup)
- Provides safety net for controller failures

## ⚡ Execution Flow

### 1. Resource Creation

```text
1. API creates LabInstance resource (state: PENDING)
2. Storage backend assigns resource version and timestamps
3. Watcher detects new resource on next poll cycle (≤2s)
4. Controller receives sevent and starts provisioning
5. Resource state transitions to PROVISIONING
```

### 2. State Progression

```text
6. Watcher detects state change to PROVISIONING
7. Controller checks provisioning status periodically
8. When provisioning completes, state transitions to READY
9. Watcher detects READY state
10. Controller begins monitoring ready lab instance
```

### 3. Reconciliation Safety

```text
11. Reconciler runs every 10 seconds checking all resources
12. Detects if any resource is stuck in PROVISIONING too long
13. Marks stuck resources as FAILED with timeout message
14. Detects expired READY resources and schedules deletion
```

## 🚀 Running the Sample

### Prerequisites

```bash
cd samples/lab-resource-manager
```

### Option 1: Full Interactive Demo

```bash
python run_watcher_demo.py
```

This runs the complete demonstration showing:

- Resource creation and state transitions
- Watcher detecting changes in real-time
- Controller responding with business logic
- Reconciler providing safety and cleanup

### Option 2: Simple Patterns Demo

```bash
python simple_demo.py
```

A simplified version focusing on the core patterns without framework dependencies.

### Expected Output

```text
🎯 Resource Oriented Architecture: Watcher & Reconciliation Demo
============================================================
👀 LabInstance Watcher started
🔄 LabInstance Scheduler started reconciliation
📦 Created resource: student-labs/python-basics-lab
🔍 Watcher detected change: student-labs/python-basics-lab -> pending
🎮 Controller processing: student-labs/python-basics-lab (state: pending)
🚀 Starting provisioning for: student-labs/python-basics-lab
🔄 Updated resource: student-labs/python-basics-lab -> {'status': {'state': 'provisioning'}}
🔍 Watcher detected change: student-labs/python-basics-lab -> provisioning
🎮 Controller processing: student-labs/python-basics-lab (state: provisioning)
🔄 Reconciling 2 lab instances
⚠️ Reconciler: Lab instance stuck in provisioning: student-labs/python-basics-lab
```

## 💡 Key Implementation Details

### Resource Versioning

Each resource change increments the version:

```python
def update_resource(self, resource_id: str, updates: Dict[str, Any]):
    resource = self.resources[resource_id]
    self.resource_version += 1
    resource.metadata['resourceVersion'] = str(self.resource_version)
```

### Event Handling

Watchers notify multiple handlers:

```python
watcher.add_event_handler(controller.handle_resource_event)
watcher.add_event_handler(audit_logger.log_change)
watcher.add_event_handler(metrics_collector.record_event)
```

### Error Resilience

All components handle errors gracefully:

```python
try:
    await self._provision_lab_instance(resource)
except Exception as e:
    logger.error(f"Provisioning failed: {e}")
    await self._mark_as_failed(resource, str(e))
```

### Concurrent Processing

Components run independently:

```python
async def main():
    watcher_task = asyncio.create_task(watcher.start_watching())
    scheduler_task = asyncio.create_task(scheduler.start_reconciliation())

    # Both run concurrently until stopped
    await asyncio.gather(watcher_task, scheduler_task)
```

## 🎯 Design Patterns Demonstrated

### 1. **Observer Pattern**

Watchers observe storage and notify controllers of changes.

### 2. **State Machine**

Resources progress through well-defined states with clear transitions.

### 3. **Command Pattern**

Controllers execute commands based on resource state.

### 4. **Strategy Pattern**

Different provisioning strategies for different lab templates.

### 5. **Circuit Breaker**

Reconcilers detect failures and prevent cascade issues.

## 🔧 Configuration Options

### Timing Configuration

```python
# Development: Fast feedback
watcher = LabInstanceWatcher(storage, poll_interval=1.0)
scheduler = LabInstanceScheduler(storage, reconcile_interval=5.0)

# Production: Optimized performance
watcher = LabInstanceWatcher(storage, poll_interval=5.0)
scheduler = LabInstanceScheduler(storage, reconcile_interval=30.0)
```

### Timeout Configuration

```python
class LabInstanceController:
    PROVISIONING_TIMEOUT = 300  # 5 minutes
    MAX_RETRIES = 3
    RETRY_BACKOFF = 30  # seconds
```

### Resource Policies

```python
class LabInstanceScheduler:
    DEFAULT_LAB_DURATION = 3600  # 1 hour
    CLEANUP_GRACE_PERIOD = 300   # 5 minutes
    MAX_CONCURRENT_PROVISIONS = 10
```

## 🧪 Testing the Sample

The sample includes comprehensive tests:

```bash
# Run all sample tests
pytest samples/lab-resource-manager/tests/

# Test individual components
pytest samples/lab-resource-manager/tests/test_watcher.py
pytest samples/lab-resource-manager/tests/test_controller.py
pytest samples/lab-resource-manager/tests/test_reconciler.py
```

## 🔗 Related Documentation

- **[🎯 Resource Oriented Architecture](../features/resource-oriented-architecture.md)** - Core ROA concepts
- **[🏗️ Watcher & Reconciliation Patterns](../features/watcher-reconciliation-patterns.md)** - Detailed patterns
- **[⚡ Execution Flow](../features/watcher-reconciliation-execution.md)** - Component coordination
- **[🎯 CQRS & Mediation](../patterns/cqrs.md)** - Command/Query handling
- **[🗄️ Data Access](../features/data-access.md)** - Storage patterns
- **[📋 Source Code Naming Conventions](../references/source_code_naming_convention.md)** - Consistent naming patterns used in this sample

## 🚀 Next Steps

After exploring this sample:

1. **Extend the Domain**: Add more resource types (LabTemplate, StudentSession)
2. **Add Persistence**: Integrate with MongoDB or Event Store
3. **Implement Authentication**: Add student authentication and authorization
4. **Add Monitoring**: Integrate metrics collection and alerting
5. **Scale Horizontally**: Implement resource sharding for multiple instances
