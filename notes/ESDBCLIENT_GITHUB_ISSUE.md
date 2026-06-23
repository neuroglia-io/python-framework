# Bug Report: AsyncPersistentSubscription.init() Missing subscription_id Propagation

**Severity**: Critical
**Affects**: esdbclient 1.1.7 (likely all async versions)
**Component**: `esdbclient/persistent.py` - `AsyncPersistentSubscription`

---

## Summary

`AsyncPersistentSubscription.init()` is missing a critical line that exists in the synchronous `PersistentSubscription.__init__()`. This causes **all persistent subscription ACKs to fail silently**, preventing checkpoints from advancing.

---

## Bug Description

The sync version correctly propagates the `subscription_id` to `_read_reqs`:

**Sync version (CORRECT)** - `PersistentSubscription.__init__()` (~line 632):

```python
self._read_reqs.subscription_id = subscription_id.encode()
```

The async version is missing this line:

**Async version (BUG)** - `AsyncPersistentSubscription.init()` (~lines 517-518):

```python
async def init(self) -> None:
    confirmation = await anext(self._read_resps)
    # MISSING: self._read_reqs.subscription_id = self._subscription_id.encode()
```

---

## Impact

### Symptoms

1. Events are redelivered every `message_timeout` seconds despite being processed successfully
2. `lastCheckpointedEventPosition` never advances in EventStoreDB
3. `totalInFlightMessages` stays high
4. Events eventually get parked after `maxRetryCount` attempts
5. ACK calls appear to succeed (no errors) but do nothing

### Root Cause

- `BaseSubscriptionReadReqs.__init__()` initializes `subscription_id = b""` (empty bytes)
- The sync version overwrites this with the correct value
- The async version only sets `self._subscription_id` without updating `_read_reqs`
- ACK messages are sent with `subscription_id = b""`
- EventStoreDB **silently ignores** ACKs with empty subscription IDs (no error returned!)

---

## Reproduction

### Minimal Example

```python
import asyncio
from esdbclient import AsyncioEventStoreDBClient

async def main():
    client = await AsyncioEventStoreDBClient(uri="esdb://localhost:2113")

    # Create subscription
    await client.create_subscription_to_stream(
        group_name="test_group",
        stream_name="test_stream",
    )

    # Read from subscription
    subscription = await client.read_subscription_to_stream(
        group_name="test_group",
        stream_name="test_stream",
    )

    # Process events
    async for event in subscription:
        print(f"Processing event: {event.id}")

        # ACK the event
        await subscription.ack(event.id)
        print(f"ACKed event: {event.id}")

        break  # Process just one for testing

    # Check EventStoreDB admin UI: checkpoint will NOT have advanced!

asyncio.run(main())
```

### Verification

1. Run the above code
2. Check EventStoreDB admin UI (`http://localhost:2113`)
3. Go to **Persistent Subscriptions** → `test_stream::test_group`
4. Observe:
   - ✅ `totalInFlightMessages`: 1 (event was delivered)
   - ❌ `lastCheckpointedEventPosition`: Stuck at initial value (ACK was ignored!)
   - ❌ After `message_timeout`: Event is redelivered

---

## Expected Behavior

After calling `await subscription.ack(event.id)`:

- EventStoreDB should receive ACK with correct `subscription_id`
- Checkpoint should advance to the ACKed event's position
- Event should NOT be redelivered

---

## Actual Behavior

After calling `await subscription.ack(event.id)`:

- EventStoreDB receives ACK with `subscription_id = b""` (empty)
- EventStoreDB silently ignores the ACK
- Checkpoint does NOT advance
- Event is redelivered after `message_timeout`

---

## Proposed Fix

**File**: `esdbclient/persistent.py`
**Method**: `AsyncPersistentSubscription.init()`
**Line**: ~518

Add the missing line:

```python
async def init(self) -> None:
    confirmation = await anext(self._read_resps)

    # ADD THIS LINE (matching the sync version):
    self._read_reqs.subscription_id = self._subscription_id.encode()
```

This single line will fix the issue by ensuring the subscription ID is propagated to the request builder, matching the behavior of the sync version.

---

## Workaround (for users)

Until this is fixed upstream, apply this runtime monkey-patch:

```python
import logging

log = logging.getLogger(__name__)

def patch_esdbclient_async_subscription_id():
    """Workaround for esdbclient AsyncPersistentSubscription bug."""
    from esdbclient.persistent import AsyncPersistentSubscription

    original_init = AsyncPersistentSubscription.init

    async def patched_init(self) -> None:
        await original_init(self)
        # Add the missing line
        if hasattr(self, "_subscription_id") and hasattr(self, "_read_reqs"):
            self._read_reqs.subscription_id = self._subscription_id.encode()
            log.debug(f"Patched subscription_id: {self._subscription_id}")

    AsyncPersistentSubscription.init = patched_init
    log.info("Applied esdbclient AsyncPersistentSubscription patch")

# Call this before creating any subscriptions
patch_esdbclient_async_subscription_id()
```

---

## Environment

- **esdbclient version**: 1.1.7
- **Python version**: 3.11.11
- **EventStoreDB version**: 24.10.0 (but affects all versions - bug is client-side)
- **OS**: macOS 15.1 (but reproducible on Linux/Windows)

---

## Additional Context

### Why This Wasn't Caught Earlier

1. **Silent failure**: EventStoreDB doesn't return an error for invalid ACKs
2. **Sync version works**: Most examples/tests use the sync client
3. **Idempotent handlers**: Duplicate processing often succeeds without obvious errors
4. **Timeout-based redelivery**: Looks like transient network issues

### Comparison with Sync Version

The sync version has always worked correctly because it sets `subscription_id` in `__init__`:

```python
# Sync version - esdbclient/persistent.py line ~632
def __init__(
    self,
    client: AbstractEventStoreDBClient,
    call_credentials: Optional[grpc.CallCredentials],
    subscription_id: str,
):
    self._subscription_id = subscription_id
    # ... other initialization ...
    self._read_reqs.subscription_id = subscription_id.encode()  # ✅ Present
```

The async version splits initialization across `__init__` and `init()`, but forgot to add this line to `init()`:

```python
# Async version - esdbclient/persistent.py line ~515
async def init(self) -> None:
    confirmation = await anext(self._read_resps)
    # ❌ Missing: self._read_reqs.subscription_id = self._subscription_id.encode()
```

---

## References

- **Affected code**: `esdbclient/persistent.py` lines ~515-520
- **Working reference**: `esdbclient/persistent.py` line ~632 (sync version)
- **EventStoreDB docs**: https://developers.eventstore.com/clients/grpc/persistent-subscriptions.html

---

## Thank You

This bug has caused significant issues in production systems. A fix would be greatly appreciated!

If you need any additional information or testing, please let me know.
