#!/usr/bin/env python3
"""Test script to verify etcd3-py watch API."""

import etcd3

# Connect to etcd
client = etcd3.Client(host="localhost", port=2479, timeout=10)

print("✅ Connected to etcd")

# Test basic operations
print("\n1️⃣ Testing basic operations...")
client.put("/test/key1", "value1")
response = client.range("/test/key1")
print(f"   PUT and GET: {response.kvs[0].value.decode('utf-8')}")

# Test watch API - check what methods are available
print("\n2️⃣ Checking watch-related methods...")
watch_methods = [x for x in dir(client) if "watch" in x.lower() or "Watch" in x]
print(f"   Available: {watch_methods}")

# Try to create a watch
print("\n3️⃣ Testing watch creation...")
try:
    # Try different watch APIs
    if hasattr(client, "watch"):
        print("   ✅ Found watch() method")
        result = client.watch("/test/key1")
        print(f"   Watch result type: {type(result)}")
        print(f"   Watch result value: {result}")

        # Check if it's a tuple (iterator, cancel_function)
        if isinstance(result, tuple):
            print(f"   ✅ Watch returns tuple with {len(result)} elements")
            if len(result) >= 2:
                watch_iter, cancel_func = result
                print(f"   Iterator type: {type(watch_iter)}")
                print(f"   Cancel func type: {type(cancel_func)}")
        else:
            print(f"   Watch result methods: {[x for x in dir(result) if not x.startswith('_')]}")

    if hasattr(client, "watch_prefix"):
        print("   ✅ Found watch_prefix() method")

    if hasattr(client, "Watcher"):
        print("   ✅ Found Watcher class")
        print(f"   Watcher: {client.Watcher}")

except Exception as e:
    import traceback

    print(f"   ❌ Error: {e}")
    print(f"   Traceback: {traceback.format_exc()}")


# Clean up
client.delete_range("/test/key1")
print("\n✅ Test complete")
