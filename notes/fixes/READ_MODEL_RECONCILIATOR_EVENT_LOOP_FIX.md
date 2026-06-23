# ReadModelReconciliator Event Loop Fix

**Issue:** #5
**Date:** December 1, 2025
**Severity:** CRITICAL
**Status:** ✅ FIXED

---

## Summary

Fixed `ReadModelReconciliator` breaking Motor's MongoDB event loop by replacing `asyncio.run()` with proper async task scheduling using `loop.call_soon_threadsafe()` and `asyncio.create_task()`.

---

## The Problem

### Error Message

```
RuntimeError: Event loop is closed
```

This error occurs when querying MongoDB after the `ReadModelReconciliator` has processed events.

### Root Cause Analysis

The `ReadModelReconciliator.subscribe_async()` method was using `asyncio.run()` inside its RxPY subscription callback:

```python
# BROKEN CODE (before fix)
async def subscribe_async(self):
    observable = await self._event_store.observe_async(...)
    self._subscription = AsyncRx.subscribe(
        observable,
        lambda e: asyncio.run(self.on_event_record_stream_next_async(e))
    )
```

**Why this breaks Motor:**

1. `asyncio.run()` creates a **new event loop** every time it's called
2. When the coroutine completes, `asyncio.run()` **closes the event loop**
3. Motor's async MongoDB client is bound to the main application event loop
4. When `asyncio.run()` closes its temporary loop, Motor's internal state becomes corrupted
5. All subsequent Motor operations fail with `RuntimeError: Event loop is closed`

**Event loop lifecycle:**

```
Main Loop (FastAPI/uvicorn)
    │
    ├── Motor client created ✅ (bound to main loop)
    │
    ├── Event arrives from EventStore
    │   │
    │   └── RxPY callback executes
    │       │
    │       └── asyncio.run() called ❌
    │           │
    │           ├── Creates NEW loop
    │           ├── Runs coroutine
    │           └── CLOSES the new loop ❌❌❌
    │
    └── Motor tries to use its loop... 💥 RuntimeError!
```

---

## The Solution

Replace `asyncio.run()` with thread-safe task scheduling on the main event loop:

```python
# FIXED CODE (after fix)
async def subscribe_async(self):
    observable = await self._event_store.observe_async(
        f'$ce-{self._event_store_options.database_name}',
        self._event_store_options.consumer_group
    )

    # Get the current event loop to schedule tasks on
    loop = asyncio.get_event_loop()

    def on_next(e):
        """Schedule the async handler on the main event loop without closing it."""
        try:
            # Use call_soon_threadsafe to schedule the coroutine on the main loop
            # This prevents creating/closing new event loops which breaks Motor
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.on_event_record_stream_next_async(e))
            )
        except RuntimeError as ex:
            logging.warning(
                f"Event loop closed, skipping event: "
                f"{type(e.data).__name__ if hasattr(e, 'data') else 'unknown'} - {ex}"
            )

    self._subscription = AsyncRx.subscribe(observable, on_next)
```

### How the Fix Works

1. **Capture main loop reference**: `loop = asyncio.get_event_loop()` gets the application's main loop
2. **Thread-safe scheduling**: `loop.call_soon_threadsafe()` schedules work on the main loop from any thread
3. **Create task**: `asyncio.create_task()` schedules the coroutine on the main loop without blocking
4. **No loop closure**: The main event loop is never closed, keeping Motor alive

**Fixed event flow:**

```
Main Loop (FastAPI/uvicorn)
    │
    ├── Motor client created ✅ (bound to main loop)
    │
    ├── Event arrives from EventStore
    │   │
    │   └── RxPY callback executes
    │       │
    │       └── on_next() called ✅
    │           │
    │           └── loop.call_soon_threadsafe() ✅
    │               │
    │               └── Task scheduled on MAIN loop ✅
    │                   │
    │                   └── Coroutine executes when loop is ready ✅
    │
    └── Motor continues to work normally ✅
```

---

## Technical Details

### Why `call_soon_threadsafe()`?

- **Thread Safety**: RxPY callbacks may execute in different threads
- **Non-Blocking**: Doesn't wait for the task to complete
- **Main Loop Preservation**: Schedules work on the existing loop, never closes it

### Why `create_task()`?

- **Async Execution**: Properly handles async coroutines
- **Background Processing**: Task runs independently without blocking
- **Error Handling**: Tasks can be awaited, cancelled, or monitored

### Error Handling

The fix includes graceful error handling if the loop is closed:

```python
except RuntimeError as ex:
    logging.warning(f"Event loop closed, skipping event: ... - {ex}")
```

This prevents crashes during application shutdown when the loop may already be closed.

---

## Impact

### Before Fix

```python
# Application flow
1. ReadModelReconciliator starts
2. Events arrive from EventStore
3. asyncio.run() closes event loop
4. Motor queries fail: RuntimeError: Event loop is closed
5. Application becomes unusable ❌
```

### After Fix

```python
# Application flow
1. ReadModelReconciliator starts
2. Events arrive from EventStore
3. Tasks scheduled on main loop
4. Motor queries work normally ✅
5. Application remains stable ✅
```

---

## Testing

### Automated Tests

**File:** `tests/cases/test_read_model_reconciliator_event_loop_fix.py`

**Coverage:**

- ✅ Verifies `asyncio.run()` is removed from source code
- ✅ Tests event handler scheduling on main loop
- ✅ Verifies event loop remains open after event processing
- ✅ Tests graceful RuntimeError handling
- ✅ Validates backward compatibility

**Run tests:**

```bash
poetry run pytest tests/cases/test_read_model_reconciliator_event_loop_fix.py -v
```

### Manual Validation

```python
# Before fix - this would crash
reconciliator = ReadModelReconciliator(...)
await reconciliator.start_async()
# ... events processed ...
result = await motor_repository.get_async(id)  # ❌ RuntimeError: Event loop is closed

# After fix - this works
reconciliator = ReadModelReconciliator(...)
await reconciliator.start_async()
# ... events processed ...
result = await motor_repository.get_async(id)  # ✅ Works normally
```

---

## Migration Guide

### No Code Changes Required

This fix is **100% backward compatible**. No changes needed in application code.

### Before (v0.6.12 and earlier)

```python
# Applications would crash with:
# RuntimeError: Event loop is closed
reconciliator = ReadModelReconciliator(
    service_provider=service_provider,
    mediator=mediator,
    event_store_options=options,
    event_store=event_store
)
await reconciliator.start_async()
# Motor queries would fail after event processing
```

### After (v0.6.13 with fix)

```python
# Same code, now works without crashes
reconciliator = ReadModelReconciliator(
    service_provider=service_provider,
    mediator=mediator,
    event_store_options=options,
    event_store=event_store
)
await reconciliator.start_async()
# Motor queries work normally ✅
```

---

## Related Issues

This fix is critical for:

- ✅ Applications using `ReadModelReconciliator` with Motor-based repositories
- ✅ Event-driven architectures with CQRS read model reconciliation
- ✅ Any async application using RxPY with asyncio

### Similar Pattern in Codebase

**Note:** A similar issue was identified (but already commented out) in:

- `neuroglia/eventing/cloud_events/infrastructure/cloud_event_publisher.py` (line 59)

That file already has the correct pattern implemented.

---

## File Modified

- `src/neuroglia/data/infrastructure/event_sourcing/read_model_reconciliator.py`

**Changes:**

- Lines 48-63: Replaced `asyncio.run()` with proper async scheduling
- Added inline documentation explaining the fix
- Added error handling for edge cases

---

## References

- **Issue Report:** Neuroglia Framework Change Request - December 1, 2025
- **Pattern:** Event Loop Management in AsyncIO
- **Motor Documentation:** https://motor.readthedocs.io/en/stable/asyncio-application.html
- **AsyncIO Best Practices:** https://docs.python.org/3/library/asyncio-eventloop.html

---

## Verification Checklist

- [x] `asyncio.run()` removed from `subscribe_async()`
- [x] `loop.call_soon_threadsafe()` implemented correctly
- [x] `asyncio.create_task()` used for async execution
- [x] Error handling for RuntimeError added
- [x] Tests validate the fix
- [x] Motor queries work after event processing
- [x] No event loop closure issues
- [x] Backward compatible (no API changes)
- [x] Documentation complete

---

**Status:** ✅ FIXED - ReadModelReconciliator no longer breaks Motor's event loop in v0.6.13
