#!/usr/bin/env python3
"""Explore etcd3-py watch utilities and classes."""

import etcd3

print("=" * 80)
print("ETCD3-PY MODULE EXPLORATION")
print("=" * 80)

# List all public attributes in etcd3 module
print("\n1. All public attributes in etcd3 module:")
print("-" * 80)
attrs = [x for x in dir(etcd3) if not x.startswith("_")]
for attr in sorted(attrs):
    obj = getattr(etcd3, attr)
    print(f"  {attr:30} -> {type(obj).__name__}")

# Look for Watch-related classes
print("\n2. Watch-related classes and functions:")
print("-" * 80)
watch_related = [x for x in attrs if "watch" in x.lower() or "Watch" in x]
if watch_related:
    for name in watch_related:
        obj = getattr(etcd3, name)
        print(f"  {name}: {type(obj)}")
        if hasattr(obj, "__doc__") and obj.__doc__:
            doc = obj.__doc__.strip().split("\n")[0]
            print(f"    -> {doc}")
else:
    print("  No watch-related attributes found in top-level module")

# Check Client class methods
print("\n3. Client class watch-related methods:")
print("-" * 80)
client_methods = [x for x in dir(etcd3.Client) if not x.startswith("_")]
watch_methods = [x for x in client_methods if "watch" in x.lower()]
if watch_methods:
    for method_name in watch_methods:
        method = getattr(etcd3.Client, method_name)
        print(f"  {method_name}")
        if hasattr(method, "__doc__") and method.__doc__:
            doc_lines = method.__doc__.strip().split("\n")
            for line in doc_lines[:3]:  # First 3 lines
                print(f"    {line}")
else:
    print("  No watch methods found")

# Check for utils submodule
print("\n4. Checking for utils or watch_util:")
print("-" * 80)
try:
    import etcd3.utils

    print("  ✓ etcd3.utils exists")
    utils_attrs = [x for x in dir(etcd3.utils) if not x.startswith("_")]
    watch_utils = [x for x in utils_attrs if "watch" in x.lower()]
    if watch_utils:
        print(f"  Watch-related utils: {watch_utils}")
    else:
        print(f"  All utils: {utils_attrs[:10]}...")  # First 10
except ImportError as e:
    print(f"  ✗ etcd3.utils not found: {e}")

try:
    import etcd3.watch_util

    print("  ✓ etcd3.watch_util exists")
    print(f"  Attributes: {[x for x in dir(etcd3.watch_util) if not x.startswith('_')]}")
except ImportError:
    print("  ✗ etcd3.watch_util not found")

# Look for Watch class
print("\n5. Looking for Watch class:")
print("-" * 80)
if hasattr(etcd3, "Watch"):
    print("  ✓ etcd3.Watch found")
    watch_cls = etcd3.Watch
    print(f"  Type: {type(watch_cls)}")
    print(f"  Methods: {[x for x in dir(watch_cls) if not x.startswith('_')][:10]}")
else:
    print("  ✗ etcd3.Watch not found")

# Check if there's a Watcher class
if hasattr(etcd3, "Watcher"):
    print("  ✓ etcd3.Watcher found")
    watcher_cls = etcd3.Watcher
    print(f"  Type: {type(watcher_cls)}")
    print(f"  Methods: {[x for x in dir(watcher_cls) if not x.startswith('_')][:10]}")
else:
    print("  ✗ etcd3.Watcher not found")

print("\n" + "=" * 80)
print("EXPLORATION COMPLETE")
print("=" * 80)
