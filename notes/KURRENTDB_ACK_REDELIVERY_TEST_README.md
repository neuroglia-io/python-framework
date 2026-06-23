# KurrentDB ACK Redelivery Bug Reproduction

This test reproduces the actual redelivery behavior that was observed in Neuroglia production **BEFORE** the Nov 30, 2025 workaround.

## The Bug

**Issue**: Events were redelivered every 30 seconds despite ACKs being sent

**Root Cause**: `AsyncPersistentSubscription.init()` in kurrentdbclient 1.1.1 didn't propagate `subscription_id` to `_read_reqs`, causing EventStoreDB to ignore ACKs.

**Fixed In**: kurrentdbclient 1.1.2 (line 20 of AsyncPersistentSubscription.init())

## Original Configuration (Pre-Nov 30, 2025)

The bug occurred with this configuration:

```python
await client.create_subscription_to_stream(
    group_name=consumer_group,
    stream_name=stream_name,
    resolve_links=True,
    # NO consumer_strategy → defaults to DispatchToSingle
    # NO min/max checkpoint counts → uses default batching
    # message_timeout=30.0 → 30 seconds before redelivery
)
```

**NOT** with RoundRobin (that was the workaround added on Nov 30).

## Prerequisites

1. **EventStoreDB Running**:

   ```bash
   # Use the test docker-compose (on default network, port 2114)
   cd tests/tmp
   docker-compose -f docker-compose.test.yaml up -d eventstoredb

   # Verify it's running
   docker ps | grep eventstore
   curl http://localhost:2114/health/live
   ```

2. **Python Environment**:

   ```bash
   # Activate your poetry environment
   poetry shell
   ```

## Running the Test

### Test with kurrentdbclient 1.1.1 (Bug Present)

```bash
# Install the broken version
pip install kurrentdbclient==1.1.1

# Run the reproduction test
pytest tests/integration/test_kurrentdb_ack_redelivery_reproduction.py::test_reproduce_ack_redelivery_with_original_config -v -s

# Expected: Events WILL be redelivered (bug reproduced)
```

### Test with kurrentdbclient 1.1.2 (Bug Fixed)

```bash
# Install the fixed version
pip install kurrentdbclient==1.1.2

# Run the same test
pytest tests/integration/test_kurrentdb_ack_redelivery_reproduction.py::test_reproduce_ack_redelivery_with_original_config -v -s

# Expected: Events will NOT be redelivered (bug fixed)
```

### Run All Tests

```bash
# Run both the reproduction test and baseline test
pytest tests/integration/test_kurrentdb_ack_redelivery_reproduction.py -v -s -m integration
```

## What the Test Does

1. **Creates a test stream** with 10 events
2. **Creates a persistent subscription** using the ORIGINAL configuration:
   - DispatchToSingle (default consumer strategy)
   - Default checkpoint batching
   - 30-second message timeout
   - Link resolution enabled
3. **Subscribes and ACKs all events** as they arrive
4. **Monitors for 60 seconds** to detect redeliveries
5. **Reports results**:
   - With 1.1.1: Should see redeliveries (bug present)
   - With 1.1.2: Should see NO redeliveries (bug fixed)

## Expected Output

### With kurrentdbclient 1.1.1 (Bug Present)

```
🔍 kurrentdbclient version: 1.1.1

📝 Creating test stream 'test-stream-...' with 10 events...
✅ Created 10 events

🔧 Creating persistent subscription with ORIGINAL configuration...
   Consumer Strategy: DispatchToSingle (default)
   Checkpoint Config: Default batching
   Message Timeout: 30 seconds

📡 Subscribing to stream...
   ✅ Received event #0
   → ACK sent for event #0
   ✅ Received event #1
   → ACK sent for event #1
   ...
   ⚠️  REDELIVERY #2 of event #0 (after 30.5s)
   → ACK sent for event #0
   ⚠️  REDELIVERY #2 of event #1 (after 30.6s)
   → ACK sent for event #1

🎯 Test Results:
   Total Events: 10
   Redelivered Events: 10

   ⚠️  REDELIVERIES DETECTED
   This indicates the subscription_id bug is PRESENT.

✅ TEST PASSED: Bug reproduced with kurrentdbclient 1.1.1
```

### With kurrentdbclient 1.1.2 (Bug Fixed)

```
🔍 kurrentdbclient version: 1.1.2

📡 Subscribing to stream...
   ✅ Received event #0
   → ACK sent for event #0
   ✅ Received event #1
   → ACK sent for event #1
   ...

⏱️  Monitoring duration (60s) reached

🎯 Test Results:
   Total Events: 10
   Redelivered Events: 0

   ✅ NO REDELIVERIES DETECTED
   This indicates the subscription_id bug is FIXED.

✅ TEST PASSED: Bug fixed in kurrentdbclient 1.1.2
```

## Troubleshooting

### EventStoreDB Not Running

```bash
# Check if container is running
docker ps | grep eventstore

# Start it
cd deployment/docker-compose
docker-compose -f docker-compose.openbank.yml up -d eventstoredb

# Check logs
docker-compose -f docker-compose.openbank.yml logs -f eventstoredb
```

### Connection Refused

Make sure EventStoreDB is accessible:

```bash
curl http://localhost:2113/health/live
# Should return: 200 OK
```

If port 2113 is not available, check docker-compose configuration.

### Test Hangs

The test monitors for 60 seconds. If it seems to hang:

- Check EventStoreDB logs for errors
- Verify the subscription was created (check EventStoreDB UI at http://localhost:2113)
- Use Ctrl+C to interrupt and check test output

## Sharing with Maintainer

To share this reproduction with the kurrentdbclient maintainer:

1. **Package the test**:

   ```bash
   # Copy just the test file
   cp tests/integration/test_kurrentdb_ack_redelivery_reproduction.py /tmp/
   ```

2. **Provide setup instructions**:

   ```bash
   # They need:
   # 1. EventStoreDB running (docker or local)
   # 2. pip install kurrentdbclient==1.1.1
   # 3. pip install pytest pytest-asyncio
   # 4. python test_kurrentdb_ack_redelivery_reproduction.py
   ```

3. **Key Points to Mention**:
   - Bug occurs with **DispatchToSingle** (default), not RoundRobin
   - Requires **category streams** or **high event volume** or **link resolution** to trigger
   - Simple tests may not reproduce it (that's why maintainer couldn't reproduce)
   - Fixed in 1.1.2 by adding: `self._read_reqs.subscription_id = subscription_id.encode()`

## Timeline Context

- **Before Nov 30, 2025**: DispatchToSingle + default checkpointing → redelivery issues
- **Nov 30, 2025**: Switched to RoundRobin + aggressive checkpointing as workaround
- **Dec 1, 2025**: Further improvements (increased timeout to 60s)
- **Current**: Using kurrentdbclient 1.1.2 with subscription_id fix

This test reproduces the **original** issue (before the workaround).
