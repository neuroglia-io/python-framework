# KurrentDB Client Bug Report: AsyncPersistentSubscription ACK Delivery

## Status: ✅ FIXED in kurrentdbclient 1.1.2

This document describes a critical bug that **was present** in earlier versions of esdbclient/kurrentdbclient but **has been fixed** in kurrentdbclient 1.1.2.

## Executive Summary

**Bug**: `AsyncPersistentSubscription.init()` failed to propagate `subscription_id` to `_read_reqs`, causing all ACK/NACK operations to be silently ignored by EventStoreDB/KurrentDB.

**Impact**:

- Events redelivered every `message_timeout` seconds (default 30s)
- Checkpoint never advances
- Events eventually parked after `maxRetryCount` attempts
- Read models process same events multiple times

**Root Cause**: Missing line in `AsyncPersistentSubscription.init()`:

```python
self._read_reqs.subscription_id = subscription_id.encode()
```

**Fix Status**: ✅ Fixed in kurrentdbclient 1.1.2 (line 20 of `AsyncPersistentSubscription.init()`)

## Bug Description

### What Happened

The async version of `PersistentSubscription` (`AsyncPersistentSubscription`) had a critical initialization bug where the `subscription_id` received from EventStoreDB was not propagated to the `_read_reqs` object that generates ACK/NACK requests.

### Comparison: Sync vs Async Implementation

**Sync Version** (`PersistentSubscription.__init__()`) - ✅ WORKING:

```python
def __init__(self, ...):
    # ... initialization code ...
    first_read_resp = self._get_next_read_resp()

    if first_read_resp.WhichOneof("content") == "subscription_confirmation":
        subscription_id = first_read_resp.subscription_confirmation.subscription_id
        self._subscription_id = subscription_id
        self._read_reqs.subscription_id = subscription_id.encode()  # ✅ PRESENT
```

**Async Version** (`AsyncPersistentSubscription.init()`) - ✅ NOW FIXED:

```python
async def init(self) -> None:
    # ... initialization code ...
    first_read_resp = await self._get_next_read_resp()

    if first_read_resp.WhichOneof("content") == "subscription_confirmation":
        subscription_id = first_read_resp.subscription_confirmation.subscription_id
        self._subscription_id = subscription_id
        self._read_reqs.subscription_id = subscription_id.encode()  # ✅ NOW PRESENT (line 20)
```

The fix adds the missing line at line 20 of `AsyncPersistentSubscription.init()`.

## Impact Analysis

### Without the Fix

When `subscription_id` is not propagated to `_read_reqs`:

1. **ACK/NACK requests sent with empty subscription_id**

   - ACK messages: `Ack { subscription_id: b"", ids: [event_uuid] }`
   - EventStoreDB/KurrentDB ignores these because it doesn't know which subscription is acknowledging

2. **EventStoreDB behavior**

   - Treats events as unacknowledged
   - Redelivers events after `message_timeout` (default 30 seconds)
   - Eventually parks events after `maxRetryCount` attempts (default 10)

3. **Application-level symptoms**
   - Event handlers receive same event multiple times
   - Read models become inconsistent
   - Logs show repeated processing of same events
   - Subscription info shows checkpoint not advancing
   - Parked events accumulate in EventStoreDB

### Production Impact (Historical)

In systems using esdbclient 1.1.7 or earlier versions of kurrentdbclient:

- Read models processed events 10+ times before parking
- 30-second redelivery loops caused performance degradation
- Manual replay from parked messages required
- Checkpoint divergence between application state and EventStoreDB

## Test Suite

A comprehensive test suite is provided in `test_kurrentdb_subscription_id_bug.py` that:

1. **Compares sync vs async implementations** - Shows whether the fix is present
2. **Displays source code side-by-side** - Highlights the critical line
3. **Can be run standalone** - Easy to share and reproduce

### Running the Tests

```bash
# As a pytest test
pytest tests/cases/test_kurrentdb_subscription_id_bug.py -v -s

# As a standalone script
python tests/cases/test_kurrentdb_subscription_id_bug.py
```

### Expected Output (with fix present)

```
================================================================================
KURRENTDBCLIENT SUBSCRIPTION_ID PROPAGATION ANALYSIS
================================================================================

Sync PersistentSubscription.__init__():
  - Propagates subscription_id to _read_reqs: True

Async AsyncPersistentSubscription.init():
  - Propagates subscription_id to _read_reqs: True

✅ BUG FIXED:
   Async version now propagates subscription_id correctly!
   The Neuroglia patch may no longer be necessary.
================================================================================
```

## Workaround (Historical)

For users stuck on older versions, a runtime monkey-patch was required:

```python
def patch_kurrentdbclient_async_subscription_id():
    """
    Patch AsyncPersistentSubscription.init() to propagate subscription_id.

    This is a runtime workaround for the missing line in the library.
    """
    from kurrentdbclient.persistent import AsyncPersistentSubscription

    original_init = AsyncPersistentSubscription.init

    async def patched_init(self):
        await original_init(self)
        # Add the missing line
        self._read_reqs.subscription_id = self._subscription_id.encode()

    AsyncPersistentSubscription.init = patched_init
```

**Note**: This workaround is **no longer necessary** with kurrentdbclient 1.1.2+

## Timeline

- **Unknown Date**: Bug introduced (present in esdbclient 1.1.7)
- **~2024**: Bug reported in production systems
- **December 2, 2025**: Bug confirmed fixed in kurrentdbclient 1.1.2
- **Status**: ✅ Resolved

## Version Recommendations

- **✅ kurrentdbclient >= 1.1.2**: Bug fixed, use without workarounds
- **⚠️ esdbclient <= 1.1.7**: Bug present, apply monkey-patch workaround
- **⚠️ kurrentdbclient < 1.1.2**: Bug present, upgrade to 1.1.2+

## Verification

To verify if your version has the fix:

```python
import inspect
from kurrentdbclient.persistent import AsyncPersistentSubscription

source = inspect.getsource(AsyncPersistentSubscription.init)
if "_read_reqs.subscription_id" in source:
    print("✅ Bug is fixed in your version!")
else:
    print("❌ Bug is present - consider upgrading to kurrentdbclient 1.1.2+")
```

## References

- **Package**: https://pypi.org/project/kurrentdbclient/
- **Repository**: https://github.com/pyeventsourcing/kurrentdb-client
- **EventStoreDB Docs**: https://developers.eventstore.com/clients/grpc/persistent-subscriptions.html

## Test Files

- `tests/cases/test_kurrentdb_subscription_id_bug.py` - Portable test suite
- `tests/cases/test_persistent_subscription_ack_delivery.py` - Integration tests
- `src/neuroglia/data/infrastructure/event_sourcing/patches.py` - Historical workaround

## Acknowledgments

Thanks to the kurrentdbclient maintainers for fixing this critical issue in version 1.1.2.

---

**Last Updated**: December 2, 2025
**Test Status**: ✅ All tests passing with kurrentdbclient 1.1.2
**Production Status**: ✅ Safe to use without workarounds
