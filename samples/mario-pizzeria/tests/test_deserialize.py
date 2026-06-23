"""Test aggregate deserialization to debug the nested Pizza issue"""

import sys

sys.path.insert(0, "../../src")

from domain.entities.order import Order

from neuroglia.serialization.aggregate_serializer import AggregateSerializer

# Read the saved order
with open("data/orders/order/31e63eb3-4235-4777-a452-944396387e4c.json", "r") as f:
    json_data = f.read()

print("=== JSON Data ===")
print(json_data[:500])

# Deserialize
serializer = AggregateSerializer()
order = serializer.deserialize_from_text(json_data, Order)

print("\n=== Deserialized Order ===")
print(f"Order ID: {order.id()}")
print(f"Order type: {type(order)}")
print(f"State type: {type(order.state)}")
print(f"Customer ID: {order.state.customer_id}")
print(f"Number of pizzas: {len(order.state.pizzas)}")

if order.state.pizzas:
    pizza = order.state.pizzas[0]
    print(f"\n=== First Pizza ===")
    print(f"Pizza type: {type(pizza)}")
    print(f"Is dict: {isinstance(pizza, dict)}")

    if isinstance(pizza, dict):
        print(f"Pizza keys: {pizza.keys()}")
        print(f"Pizza data: {pizza}")
    else:
        print(f"Pizza ID: {pizza.id()}")
        print(f"Pizza name: {pizza.state.name}")
