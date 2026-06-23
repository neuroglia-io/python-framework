# Repository Abstract Methods Fix - v0.6.12

**Date:** December 1, 2025
**Priority:** High (Blocking Issue)
**Status:** ✅ Fixed

---

## Summary

Fixed critical instantiation issues in neuroglia-python v0.6.12 where repository implementations could not be instantiated due to missing abstract method implementations. The base `Repository` class was updated to use a Template Method Pattern, but concrete implementations were not updated accordingly.

## Issues Fixed

### Issue 1: EventSourcingRepository Cannot Be Instantiated

**Error:**

```
TypeError: Can't instantiate abstract class EventSourcingRepository with abstract methods _do_add_async, _do_remove_async, _do_update_async
```

**Root Cause:**
The `Repository` base class defines abstract methods `_do_add_async`, `_do_update_async`, `_do_remove_async` that follow a Template Method Pattern. `EventSourcingRepository` was overriding `add_async`, `update_async`, `remove_async` directly without implementing the abstract `_do_*` methods.

**Fix Applied:**

- Renamed `add_async` → `_do_add_async`
- Renamed `update_async` → `_do_update_async`
- Renamed `remove_async` → `_do_remove_async`
- Added mediator parameter to constructor: `__init__(eventstore, aggregator, mediator=None)`
- Called `super().__init__(mediator)` to initialize base class
- Added `TYPE_CHECKING` import for `Mediator` type hint
- Updated error messages for clarity

**File Modified:** `src/neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py`

---

### Issue 2: MongoRepository Cannot Be Instantiated

**Error:**

```
TypeError: Can't instantiate abstract class MongoRepository with abstract methods _do_add_async, _do_remove_async, _do_update_async
```

**Root Cause:**
Same as EventSourcingRepository - `MongoRepository` was overriding methods directly without implementing the required abstract `_do_*` methods.

**Fix Applied:**

- Renamed `add_async` → `_do_add_async`
- Renamed `update_async` → `_do_update_async`
- Renamed `remove_async` → `_do_remove_async`
- Added mediator parameter to constructor: `__init__(options, mongo_client, serializer, mediator=None)`
- Called `super().__init__(mediator)` to initialize base class
- Added `TYPE_CHECKING` import for `Mediator` type hint
- Added docstrings to template method implementations

**File Modified:** `src/neuroglia/data/infrastructure/mongo/mongo_repository.py`

---

### Issue 3: Missing `List` Import in queryable.py

**Error:**

```
NameError: name 'List' is not defined
```

**Root Cause:**
`queryable.py` uses `List` at line 230 (`return self.provider.execute(self.expression, List)`) but was not importing it from `typing`.

**Fix Applied:**

- Added `List` to imports: `from typing import Any, Generic, List, Optional, TypeVar`

**File Modified:** `src/neuroglia/data/queryable.py`

---

### Issue 4: Missing `List` Import in mongo_repository.py

**Error:**

```
NameError: name 'List' is not defined
```

**Root Cause:**
`mongo_repository.py` uses `List` at lines 118-119 (`type_ = query_type if isclass(query_type) or query_type == List else type(query_type)`) but was not importing it from `typing`.

**Fix Applied:**

- Added `List` to imports: `from typing import TYPE_CHECKING, Any, Generic, List, Optional`

**File Modified:** `src/neuroglia/data/infrastructure/mongo/mongo_repository.py`

---

## Technical Details

### Template Method Pattern Implementation

The `Repository` base class now follows the Template Method Pattern:

```python
# Base class template methods (neuroglia/data/infrastructure/abstractions.py)
async def add_async(self, entity: TEntity) -> TEntity:
    """Template method that handles persistence and event publishing"""
    result = await self._do_add_async(entity)  # Call hook method
    await self._publish_domain_events(entity)   # Publish events automatically
    return result

@abstractmethod
async def _do_add_async(self, entity: TEntity) -> TEntity:
    """Hook method - subclasses implement persistence logic"""
    raise NotImplementedError()
```

Concrete implementations now implement the `_do_*` hook methods:

```python
# EventSourcingRepository implementation
async def _do_add_async(self, aggregate: TAggregate) -> TAggregate:
    """Adds and persists the specified aggregate"""
    stream_id = self._build_stream_id_for(aggregate.id())
    events = aggregate._pending_events
    if len(events) < 1:
        raise Exception("No pending events to persist")
    encoded_events = [self._encode_event(e) for e in events]
    await self._eventstore.append_async(stream_id, encoded_events)
    aggregate.state.state_version = events[-1].aggregate_version
    aggregate.clear_pending_events()
    return aggregate
```

### Benefits of Template Method Pattern

1. **Automatic Event Publishing:** The base class automatically publishes domain events after successful persistence
2. **Consistent Behavior:** All repository implementations follow the same workflow
3. **Separation of Concerns:** Persistence logic is separate from event publishing
4. **Testability:** Event publishing can be disabled by passing `mediator=None`

---

## Testing

### Validation Script

A comprehensive validation script was created to verify all fixes:

**File:** `scripts/validate_repository_fixes.py`

**Run:**

```bash
poetry run python scripts/validate_repository_fixes.py
```

**Output:**

```
🎉 ALL VALIDATIONS PASSED!

The following issues have been successfully fixed:
  1. EventSourcingRepository implements _do_add_async, _do_update_async, _do_remove_async
  2. MongoRepository implements _do_add_async, _do_update_async, _do_remove_async
  3. List import added to queryable.py
  4. List import added to mongo_repository.py

No runtime patches are needed. Repositories can be instantiated normally.
```

### Automated Tests

**File:** `tests/cases/test_repository_abstract_methods_fix.py`

**Coverage:**

- ✅ EventSourcingRepository instantiation without mediator
- ✅ EventSourcingRepository instantiation with mediator
- ✅ All abstract methods are implemented
- ✅ `_do_remove_async` raises NotImplementedError (event sourcing doesn't support hard deletes)
- ✅ MongoRepository instantiation
- ✅ List imports available in both modules
- ✅ Template Method Pattern properly implemented

---

## Migration Guide

### Before (v0.6.11 and earlier)

```python
# Required runtime patches
from patches import apply_patches
apply_patches()  # Must be called before importing neuroglia

from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository

# Would fail without patches:
# TypeError: Can't instantiate abstract class EventSourcingRepository
```

### After (v0.6.12 with fixes)

```python
# No patches needed!
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import EventSourcingRepository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository

# Works without errors
repo = EventSourcingRepository(eventstore, aggregator, mediator=None)
mongo_repo = MongoRepository(options, client, serializer, mediator=None)
```

### Constructor Signature Changes

**EventSourcingRepository:**

```python
# Before
def __init__(self, eventstore: EventStore, aggregator: Aggregator)

# After (added optional mediator parameter)
def __init__(self, eventstore: EventStore, aggregator: Aggregator, mediator: Optional["Mediator"] = None)
```

**MongoRepository:**

```python
# Before
def __init__(self, options: MongoRepositoryOptions, mongo_client: MongoClient, serializer: JsonSerializer)

# After (added optional mediator parameter)
def __init__(self, options: MongoRepositoryOptions, mongo_client: MongoClient, serializer: JsonSerializer, mediator: Optional["Mediator"] = None)
```

**Breaking Change:** If you have custom code that instantiates repositories directly (not through DI), you may need to add `mediator=None` to your constructor calls. However, the parameter is optional and defaults to `None`, so existing code will continue to work.

---

## Files Changed

| File                                                                            | Lines Changed | Change Type                                            |
| ------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------ |
| `src/neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py` | ~30           | Modified - Implemented abstract methods                |
| `src/neuroglia/data/infrastructure/mongo/mongo_repository.py`                   | ~40           | Modified - Implemented abstract methods, added imports |
| `src/neuroglia/data/queryable.py`                                               | 1             | Modified - Added List import                           |
| `scripts/validate_repository_fixes.py`                                          | 250           | New - Validation script                                |
| `tests/cases/test_repository_abstract_methods_fix.py`                           | 320           | New - Comprehensive test suite                         |

---

## Verification Checklist

- [x] EventSourcingRepository can be instantiated without errors
- [x] MongoRepository can be instantiated without errors
- [x] List imports work in queryable.py
- [x] List imports work in mongo_repository.py
- [x] Template Method Pattern properly implemented
- [x] Event publishing works automatically for aggregates
- [x] Mediator can be disabled (mediator=None) for testing
- [x] All validation tests pass
- [x] No runtime patches needed
- [x] Backward compatible (optional mediator parameter)

---

## References

- **Original Issue:** Neuroglia Framework Change Request - December 1, 2025
- **Pattern:** Template Method Pattern (Gang of Four)
- **Documentation:** `docs/patterns/repository.md`
- **Validation:** `scripts/validate_repository_fixes.py`
- **Tests:** `tests/cases/test_repository_abstract_methods_fix.py`

---

## Contact

For questions or issues related to these fixes, please contact the neuroglia development team.
