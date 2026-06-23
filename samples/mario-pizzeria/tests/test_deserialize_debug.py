"""Test aggregate deserialization with debug output"""

import sys

sys.path.insert(0, "../../src")

from domain.entities.order import Order

from neuroglia.serialization.aggregate_serializer import AggregateSerializer

# Monkey patch to add debug logging
original_reconstruct = AggregateSerializer._reconstruct_nested_aggregates


def debug_reconstruct(self, obj):
    print(f"DEBUG: _reconstruct_nested_aggregates called on {type(obj)}")
    if hasattr(obj, "__dict__"):
        for attr_name in list(obj.__dict__.keys()):
            attr_value = getattr(obj, attr_name)
            print(f"  - {attr_name}: {type(attr_value)} = {str(attr_value)[:100]}")
    result = original_reconstruct(self, obj)
    print(f"DEBUG: After reconstruction:")
    if hasattr(obj, "__dict__"):
        for attr_name in list(obj.__dict__.keys()):
            attr_value = getattr(obj, attr_name)
            print(f"  - {attr_name}: {type(attr_value)}")
    return result


AggregateSerializer._reconstruct_nested_aggregates = debug_reconstruct

# Read the saved order
with open("data/orders/order/31e63eb3-4235-4777-a452-944396387e4c.json", "r") as f:
    json_data = f.read()

# Deserialize
serializer = AggregateSerializer()
order = serializer.deserialize_from_text(json_data, Order)

print("\n=== Result ===")
print(f"Order ID: {order.id()}")
print(f"Number of pizzas: {len(order.state.pizzas)}")
if order.state.pizzas:
    pizza = order.state.pizzas[0]
    print(f"Pizza type: {type(pizza)}")
    if not isinstance(pizza, dict):
        print(f"Pizza ID: {pizza.id()}")
        print(f"SUCCESS: Pizza is properly deserialized!")
    else:
        print(f"FAILED: Pizza is still a dict")
