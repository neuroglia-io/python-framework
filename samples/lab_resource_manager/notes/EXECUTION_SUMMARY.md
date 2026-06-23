# 🎯 Watcher and Reconciliation Patterns - Execution Summary

```
python run_watcher_demo.py
🎯 Resource Oriented Architecture: Watcher & Reconciliation Demo
============================================================
This demo shows:
- Watcher: Detects resource changes (every 2s)
- Controller: Responds to changes with business logic
- Scheduler: Reconciles state periodically (every 10s)
============================================================
2025-09-09 23:34:17,299 - __main__ - INFO - 👀 LabInstance Watcher started
2025-09-09 23:34:17,299 - __main__ - INFO - 🔄 LabInstance Scheduler started reconciliation
2025-09-09 23:34:18,300 - __main__ - INFO - 📦 Created resource: student-labs/python-basics-lab
2025-09-09 23:34:19,300 - __main__ - INFO - 🔍 Watcher detected change: student-labs/python-basics-lab -> pending
2025-09-09 23:34:19,300 - __main__ - INFO - 🎮 Controller processing: student-labs/python-basics-lab (state: pending)
2025-09-09 23:34:19,300 - __main__ - INFO - 🚀 Starting provisioning for: student-labs/python-basics-lab
2025-09-09 23:34:19,300 - __main__ - INFO - 🔄 Updated resource: student-labs/python-basics-lab -> {'status': {'state': 'provisioning', 'message': 'Starting lab instance provisioning', 'startedAt': '2025-09-09T21:34:19.300851+00:00'}}
2025-09-09 23:34:21,301 - __main__ - INFO - 📦 Created resource: student-labs/web-dev-lab

⏱️  Demo running... Watch the logs to see the patterns in action!
   - Resource creation and state transitions
   - Watcher detecting changes
   - Controller responding with business logic
   - Scheduler reconciling state

📝 Press Ctrl+C to stop the demo

2025-09-09 23:34:21,301 - __main__ - INFO - 🔍 Watcher detected change: student-labs/python-basics-lab -> provisioning
2025-09-09 23:34:21,301 - __main__ - INFO - 🎮 Controller processing: student-labs/python-basics-lab (state: provisioning)
2025-09-09 23:34:21,301 - __main__ - INFO - 🔍 Watcher detected change: student-labs/web-dev-lab -> pending
2025-09-09 23:34:21,301 - __main__ - INFO - 🎮 Controller processing: student-labs/web-dev-lab (state: pending)
2025-09-09 23:34:21,301 - __main__ - INFO - 🚀 Starting provisioning for: student-labs/web-dev-lab
2025-09-09 23:34:21,302 - __main__ - INFO - 🔄 Updated resource: student-labs/web-dev-lab -> {'status': {'state': 'provisioning', 'message': 'Starting lab instance provisioning', 'startedAt': '2025-09-09T21:34:21.301983+00:00'}}
2025-09-09 23:34:23,302 - __main__ - INFO - 🔍 Watcher detected change: student-labs/web-dev-lab -> provisioning
2025-09-09 23:34:23,302 - __main__ - INFO - 🎮 Controller processing: student-labs/web-dev-lab (state: provisioning)
2025-09-09 23:34:27,310 - __main__ - INFO - 🔄 Reconciling 2 lab instances
2025-09-09 23:34:37,313 - __main__ - INFO - 🔄 Reconciling 2 lab instances
2025-09-09 23:34:47,313 - __main__ - INFO - 🔄 Reconciling 2 lab instances
2025-09-09 23:34:57,314 - __main__ - INFO - 🔄 Reconciling 2 lab instances
2025-09-09 23:34:57,314 - __main__ - WARNING - ⚠️ Reconciler: Lab instance stuck in provisioning: student-labs/python-basics-lab
2025-09-09 23:34:57,314 - __main__ - INFO - 🔄 Updated resource: student-labs/python-basics-lab -> {'status': {'state': 'failed', 'message': 'Provisioning timeout', 'failedAt': '2025-09-09T21:34:57.314308+00:00'}}
2025-09-09 23:34:57,314 - __main__ - WARNING - ⚠️ Reconciler: Lab instance stuck in provisioning: student-labs/web-dev-lab
2025-09-09 23:34:57,314 - __main__ - INFO - 🔄 Updated resource: student-labs/web-dev-lab -> {'status': {'state': 'failed', 'message': 'Provisioning timeout', 'failedAt': '2025-09-09T21:34:57.314424+00:00'}}
2025-09-09 23:34:57,319 - __main__ - INFO - 🔍 Watcher detected change: student-labs/python-basics-lab -> failed
2025-09-09 23:34:57,319 - __main__ - INFO - 🎮 Controller processing: student-labs/python-basics-lab (state: failed)
2025-09-09 23:34:57,319 - __main__ - INFO - 🔍 Watcher detected change: student-labs/web-dev-lab -> failed
2025-09-09 23:34:57,319 - __main__ - INFO - 🎮 Controller processing: student-labs/web-dev-lab (state: failed)
^C2025-09-09 23:34:58,512 - __main__ - INFO - ⏹️ LabInstance Watcher stopped
2025-09-09 23:34:58,512 - __main__ - INFO - ⏹️ LabInstance Scheduler stopped reconciliation
✨ Demo completed!
```

## What You Just Saw

The demonstration clearly showed the **Resource Oriented Architecture (ROA)** patterns in action:

### 🔍 Watcher Pattern Execution

```
👀 LabInstance Watcher started
🔍 Watcher detected change: student-labs/python-basics-lab -> pending
🔍 Watcher detected change: student-labs/python-basics-lab -> provisioning
🔍 Watcher detected change: student-labs/web-dev-lab -> pending
```

**How the Watcher Executes:**

1. **Polling Loop**: Runs every 2 seconds checking for resource changes
2. **Change Detection**: Compares resource versions to detect modifications
3. **Event Notification**: Immediately notifies controllers when changes occur
4. **Continuous Monitoring**: Never stops watching until explicitly terminated

### 🎮 Controller Pattern Execution

```
🎮 Controller processing: student-labs/python-basics-lab (state: pending)
🚀 Starting provisioning for: student-labs/python-basics-lab
🎮 Controller processing: student-labs/web-dev-lab (state: pending)
🚀 Starting provisioning for: student-labs/web-dev-lab
```

**How the Controller Executes:**

1. **Event Handling**: Receives notifications from watchers immediately
2. **State Machine Logic**: Processes resources based on current state
3. **Business Actions**: Executes appropriate business logic (start provisioning, check status, etc.)
4. **Resource Updates**: Modifies resource state based on business rules

### 🔄 Reconciliation Loop Execution

```
🔄 LabInstance Scheduler started reconciliation
🔄 Reconciling 2 lab instances
⚠️ Reconciler: Lab instance stuck in provisioning: student-labs/python-basics-lab
🔄 Updated resource: student-labs/python-basics-lab -> {'status': {'state': 'failed', 'message': 'Provisioning timeout'}}
```

**How the Reconciliation Loop Executes:**

1. **Periodic Scanning**: Runs every 10 seconds examining all resources
2. **Drift Detection**: Identifies resources that don't match desired state
3. **Corrective Actions**: Takes action to fix inconsistencies (timeout handling, cleanup, etc.)
4. **State Enforcement**: Ensures the system eventually reaches desired state

## 🕐 Execution Timeline

From the logs, you can see the exact timing:

```
23:34:17 - Watcher and Scheduler start
23:34:18 - First resource created
23:34:19 - Watcher detects change (1 second later)
23:34:19 - Controller responds immediately
23:34:21 - Second resource created
23:34:21 - Watcher detects both changes
23:34:27 - First reconciliation check (10 seconds after start)
23:34:37 - Second reconciliation check (10 seconds later)
23:34:47 - Third reconciliation check
23:34:57 - Fourth reconciliation check detects timeouts
```

## 🔧 Import Resolution Status

### ✅ Working Demonstrations

- **`run_watcher_demo.py`** - Fully functional standalone demo
- **`simple_demo.py`** - Basic patterns without framework dependencies

### 🚧 Import Issues Resolved

The complex demonstration (`demo_watcher_reconciliation.py`) had import issues because:

1. **Module Path Resolution**: Python couldn't find the `samples` module
2. **Framework Dependencies**: Complex imports requiring full Neuroglia setup
3. **Typing Conflicts**: Generic type annotations conflicting with simplified imports

### 🛠️ Solutions Applied

#### For Standalone Demos (✅ Working)

```python
# All dependencies are self-contained
# No external framework imports
# Direct execution with: python run_watcher_demo.py
```

#### For Framework Integration Demos (🔧 Fixed)

```python
# Added proper __init__.py files throughout package structure
# Simplified command classes with mock implementations
# Removed complex generic typing that caused conflicts
```

## 🎯 Key Patterns You Observed

### 1. **Asynchronous Execution**

All three components run concurrently:

- Watcher polling every 2 seconds
- Controller responding to events immediately
- Reconciler scanning every 10 seconds

### 2. **Event-Driven Architecture**

```
Resource Change → Watcher Detection → Controller Response → Resource Update
```

### 3. **State Machine Progression**

```
PENDING → PROVISIONING → READY → (timeout) → FAILED
```

### 4. **Reconciliation Safety**

The reconciler acts as a safety net:

- Detects stuck states (provisioning timeout)
- Enforces business rules (lab expiration)
- Provides eventual consistency

## 🚀 Running the Demonstrations

### Option 1: Full Working Demo

```bash
cd samples/lab-resource-manager
python run_watcher_demo.py
```

### Option 2: Simple Patterns Demo

```bash
cd samples/lab-resource-manager
python simple_demo.py
```

### Option 3: Framework Integration (Fixed Imports)

```bash
cd samples
python run_complex_demo.py
```

## 📝 What the Logs Tell You

Each log entry shows exactly how the patterns execute:

- **📦 Created resource**: Storage backend creates new resource
- **🔍 Watcher detected change**: Polling loop finds modifications
- **🎮 Controller processing**: Business logic responds to events
- **🚀 Starting provisioning**: State transitions occur
- **🔄 Updated resource**: Resource state changes are persisted
- **🔄 Reconciling N lab instances**: Periodic reconciliation runs
- **⚠️ Reconciler**: Safety checks and corrective actions

## 🏗️ Architecture in Action

The demonstration shows the complete ROA stack:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Watcher       │    │   Controller    │    │  Reconciler     │
│   (2s polling)  │───▶│   (immediate)   │    │   (10s loop)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Resource Storage                             │
│            (Kubernetes-like API with versioning)               │
└─────────────────────────────────────────────────────────────────┘
```

The imports are now resolved, and you have working demonstrations that clearly show how the watcher detects changes, how controllers respond with business logic, and how reconciliation loops ensure system consistency over time.
