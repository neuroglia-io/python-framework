#!/usr/bin/env python3
"""Test etcd3.Watcher class usage."""

import time

import etcd3

print("=" * 80)
print("TESTING ETCD3 WATCHER CLASS")
print("=" * 80)

# Create client
client = etcd3.Client(host="localhost", port=2479)
print("✓ Client created")

# Put initial value
client.put("/watch-test/key1", "initial")
print("✓ Put initial value")

# Create Watcher
print("\nCreating Watcher...")
try:
    watcher = etcd3.Watcher(client=client, key="/watch-test/", prefix=True)  # Enable prefix watching
    print(f"✓ Watcher created: {watcher}")
    print(f"  Type: {type(watcher)}")
    print(f"  Methods: {[m for m in dir(watcher) if not m.startswith('_')]}")

    # Register callback
    print("\nRegistering event callback...")
    events_received = []

    def on_watch_event(event):
        print(f"\n🔔 EVENT RECEIVED: {event}")
        print(f"  Event type: {type(event)}")
        if hasattr(event, "__dict__"):
            print(f"  Event dict: {event.__dict__}")
        events_received.append(event)

    watcher.onEvent(on_watch_event)
    print("✓ Callback registered")

    # Start watcher in daemon thread
    print("\nStarting watcher daemon...")
    watcher.runDaemon()
    print("✓ Watcher daemon started")

    # Wait a bit for watcher to initialize
    time.sleep(0.5)

    # Trigger some events
    print("\n" + "-" * 80)
    print("TRIGGERING EVENTS")
    print("-" * 80)

    print("\n1. PUT /watch-test/key1 = 'updated'")
    client.put("/watch-test/key1", "updated")
    time.sleep(0.5)

    print("\n2. PUT /watch-test/key2 = 'new'")
    client.put("/watch-test/key2", "new")
    time.sleep(0.5)

    print("\n3. DELETE /watch-test/key1")
    client.delete_range("/watch-test/key1")
    time.sleep(0.5)

    # Check results
    print("\n" + "-" * 80)
    print(f"RESULTS: Received {len(events_received)} events")
    print("-" * 80)

    for i, event in enumerate(events_received):
        print(f"\nEvent {i+1}: {event}")

    # Cancel watch
    print("\n" + "-" * 80)
    print("Cancelling watcher...")
    watcher.cancel()
    print("✓ Watcher cancelled")

except Exception as ex:
    print(f"\n✗ ERROR: {ex}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
