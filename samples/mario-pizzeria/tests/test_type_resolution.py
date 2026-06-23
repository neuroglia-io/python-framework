"""Test type resolution"""

import sys

sys.path.insert(0, "../../src")

from neuroglia.serialization.aggregate_serializer import AggregateSerializer

serializer = AggregateSerializer()

# Test resolving Pizza
pizza_type = serializer._resolve_aggregate_type("Pizza")
print(f"Pizza type resolved: {pizza_type}")

if pizza_type:
    print(f"Pizza type name: {pizza_type.__name__}")
    print(f"Pizza type module: {pizza_type.__module__}")
else:
    print("FAILED: Could not resolve Pizza type")
    print("\nSearching for Pizza in sys.modules:")

    import sys

    for module_name, module in list(sys.modules.items()):
        if module and "pizza" in module_name.lower():
            print(f"  Found module: {module_name}")
            if hasattr(module, "Pizza"):
                print(f"    - Has Pizza attribute!")
