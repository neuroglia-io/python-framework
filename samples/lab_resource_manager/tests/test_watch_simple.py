#!/usr/bin/env python3
"""Simple test to verify etcd watch functionality works end-to-end."""

import asyncio
import sys

import etcd3

# Add the integration module to path
from integration.repositories.etcd_storage_backend import EtcdStorageBackend

# Track events received
events_received = []


def on_event(event):
    """Callback for watch events."""
    print(f"\n🔔 EVENT: {event}")
    print(f"   Type: {type(event)}")
    if hasattr(event, "__dict__"):
        print(f"   Attributes: {list(event.__dict__.keys())}")
    events_received.append(event)


async def test_watch():
    """Test the watch functionality."""
    print("=" * 80)
    print("TESTING ETCD WATCH FUNCTIONALITY")
    print("=" * 80)

    # Create client and backend
    client = etcd3.Client(host="localhost", port=2479)
    backend = EtcdStorageBackend(client, prefix="/test-watch/")

    print("\n1️⃣  Starting watch...")
    watcher = backend.watch(on_event)

    if not watcher:
        print("   ❌ Failed to create watcher")
        return False

    print(f"   ✅ Watcher created: {type(watcher)}")

    # Give watch time to initialize
    await asyncio.sleep(1)

    print("\n2️⃣  Creating resource (should trigger watch)...")
    await backend.set("test-001", {"name": "test", "value": "hello"})
    await asyncio.sleep(1)

    print("\n3️⃣  Updating resource (should trigger watch)...")
    await backend.set("test-001", {"name": "test", "value": "updated"})
    await asyncio.sleep(1)

    print("\n4️⃣  Deleting resource (should trigger watch)...")
    await backend.delete("test-001")
    await asyncio.sleep(1)

    print("\n5️⃣  Cancelling watcher...")
    watcher.cancel()
    print("   ✅ Watcher cancelled")

    print(f"\n📊 RESULTS: Received {len(events_received)} events")

    if len(events_received) >= 3:
        print("   ✅ SUCCESS: Watch functionality working!")
        return True
    else:
        print(f"   ⚠️  WARNING: Expected 3+ events, got {len(events_received)}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_watch())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as ex:
        print(f"\n\n❌ Test failed: {ex}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
