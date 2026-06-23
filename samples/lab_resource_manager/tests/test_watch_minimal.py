"""Minimal test to understand etcd3-py watch API."""

import threading
import time

import etcd3


def test_watch_return_type():
    """Test what watch() actually returns."""
    print("=" * 80)
    print("TEST 1: Understanding watch() return type")
    print("=" * 80)

    client = etcd3.Client(host="localhost", port=2479)

    # Put a test value
    client.put("/test-watch/key1", "initial")
    print("✓ Put initial value")

    # Call watch and inspect return value
    watch_result = client.watch("/test-watch/")
    print(f"\nwatch() returned type: {type(watch_result)}")
    print(f"watch() returned value: {watch_result}")

    # Check if it's a tuple
    if isinstance(watch_result, tuple):
        print(f"✓ It's a tuple with {len(watch_result)} elements")
        for i, elem in enumerate(watch_result):
            print(f"  Element {i}: type={type(elem)}, value={elem}")

    # Check if it's iterable
    try:
        iter(watch_result)
        print("✓ It's iterable")
    except TypeError:
        print("✗ It's NOT iterable")

    # Check what attributes/methods it has
    if hasattr(watch_result, "__dict__"):
        print(f"\nAttributes: {watch_result.__dict__}")

    print(f"\nDir (watch_result): {[x for x in dir(watch_result) if not x.startswith('_')]}")


def test_watch_consumption():
    """Test consuming watch events."""
    print("\n" + "=" * 80)
    print("TEST 2: Consuming watch events")
    print("=" * 80)

    client = etcd3.Client(host="localhost", port=2479)

    # Start watch
    watch_result = client.watch("/test-watch2/")
    print(f"Started watch, type: {type(watch_result)}")

    # Background thread to modify key
    def modify_key():
        time.sleep(1)
        print("\n[Background] Putting value...")
        client.put("/test-watch2/key", "value1")
        time.sleep(1)
        print("[Background] Putting updated value...")
        client.put("/test-watch2/key", "value2")

    modifier = threading.Thread(target=modify_key, daemon=True)
    modifier.start()

    # Try to consume events
    print("\nAttempting to consume watch events...")
    event_count = 0
    timeout = time.time() + 5  # 5 second timeout

    try:
        # If it's a tuple, try unpacking
        if isinstance(watch_result, tuple):
            print("✓ Watch returned a tuple, attempting to unpack...")
            events_iterator = watch_result[0] if len(watch_result) > 0 else watch_result
            cancel_func = watch_result[1] if len(watch_result) > 1 else None
            print(f"  events_iterator type: {type(events_iterator)}")
            print(f"  cancel_func type: {type(cancel_func)}")

            for event in events_iterator:
                event_count += 1
                print(f"\n✓ Event {event_count}: {event}")
                print(f"  Event type: {type(event)}")
                if hasattr(event, "__dict__"):
                    print(f"  Event dict: {event.__dict__}")

                if event_count >= 2 or time.time() > timeout:
                    print("\n✓ Cancelling watch...")
                    if cancel_func and callable(cancel_func):
                        cancel_func()
                    break
        else:
            # Try consuming directly
            print("✓ Attempting to iterate watch_result directly...")
            for event in watch_result:
                event_count += 1
                print(f"\n✓ Event {event_count}: {event}")
                if event_count >= 2 or time.time() > timeout:
                    break

    except Exception as ex:
        print(f"\n✗ Error consuming watch: {ex}")
        import traceback

        traceback.print_exc()

    print(f"\nReceived {event_count} events")
    modifier.join(timeout=1)


def test_watch_prefix():
    """Test watch_prefix if it exists."""
    print("\n" + "=" * 80)
    print("TEST 3: Testing watch_prefix method")
    print("=" * 80)

    client = etcd3.Client(host="localhost", port=2479)

    # Check if watch_prefix exists
    if hasattr(client, "watch_prefix"):
        print("✓ watch_prefix method exists")
        try:
            watch_result = client.watch_prefix("/test-watch3/")
            print(f"watch_prefix() returned type: {type(watch_result)}")
            print(f"watch_prefix() returned value: {watch_result}")
        except Exception as ex:
            print(f"✗ watch_prefix failed: {ex}")
    else:
        print("✗ watch_prefix method does NOT exist")


def test_watcher_class():
    """Test Watcher class if it exists."""
    print("\n" + "=" * 80)
    print("TEST 4: Testing Watcher class")
    print("=" * 80)

    client = etcd3.Client(host="localhost", port=2479)

    if hasattr(client, "Watcher"):
        print("✓ Watcher class exists")
        try:
            watcher = client.Watcher(client, "/test-watch4/")
            print(f"Watcher created: type={type(watcher)}")
            print(f"Watcher dir: {[x for x in dir(watcher) if not x.startswith('_')]}")
        except Exception as ex:
            print(f"✗ Watcher creation failed: {ex}")
            import traceback

            traceback.print_exc()
    else:
        print("✗ Watcher class does NOT exist")


if __name__ == "__main__":
    try:
        test_watch_return_type()
        test_watch_consumption()
        test_watch_prefix()
        test_watcher_class()
        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED")
        print("=" * 80)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as ex:
        print(f"\n\nFATAL ERROR: {ex}")
        import traceback

        traceback.print_exc()
