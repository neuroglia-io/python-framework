"""Test deserialization directly"""

import sys

sys.path.insert(
    0,
    "/Users/bvandewe/Documents/Work/Systems/Mozart/src/building-blocks/Python/pyneuro/samples/mario-pizzeria",
)

from decimal import Decimal

from domain.entities.enums import PizzaSize
from domain.entities.order import OrderItem, OrderState

from neuroglia.serialization.json import JsonSerializer

# Create a state with OrderItems
state = OrderState()
state.order_items = [
    OrderItem(
        line_item_id="item1",
        name="Margherita",
        size=PizzaSize.LARGE,
        base_price=Decimal("12.00"),
        toppings=["basil", "mozzarella"],
    )
]

# Serialize
serializer = JsonSerializer()
json_text = serializer.serialize_to_text(state)
print("Serialized:")
print(json_text[:200])

# Deserialize
deserialized = serializer.deserialize_from_text(json_text, OrderState)
print(f"\nDeserialized type: {type(deserialized)}")
print(f"Order items: {len(deserialized.order_items)}")
print(f"First item type: {type(deserialized.order_items[0])}")
print(f"First item is OrderItem: {isinstance(deserialized.order_items[0], OrderItem)}")

if isinstance(deserialized.order_items[0], OrderItem):
    print(f"✅ SUCCESS: OrderItem deserialized correctly!")
    print(f"Total price: {deserialized.order_items[0].total_price}")
else:
    print(f"❌ FAIL: Got {type(deserialized.order_items[0])} instead of OrderItem")
    print(f"Value: {deserialized.order_items[0]}")
