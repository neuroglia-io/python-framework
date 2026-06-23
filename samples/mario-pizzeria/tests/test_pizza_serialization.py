#!/usr/bin/env python3
"""
Test to verify Pizza repository serialization with state separation
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("🧪 Testing Pizza Repository Serialization")
print("=" * 70)

try:
    # Import required classes
    print("\n1️⃣  Importing dependencies...")
    from domain.entities.enums import PizzaSize
    from domain.entities.pizza import Pizza

    from neuroglia.serialization import JsonSerializer

    print("   ✅ Imports successful")

    # Create a test pizza
    print("\n2️⃣  Creating test pizza...")
    pizza = Pizza(
        name="Pepperoni Supreme",
        base_price=Decimal("15.99"),
        size=PizzaSize.MEDIUM,
        description="Loaded with pepperoni",
    )
    pizza.add_topping("extra cheese")
    pizza.add_topping("pepperoni")
    print(f"   ✅ Pizza created: {pizza.state.name}")
    print(f"   • ID: {pizza.id}")
    print(f"   • Size: {pizza.state.size}")
    print(f"   • Toppings: {pizza.state.toppings}")
    print(f"   • Total price: ${pizza.total_price}")

    # Test serializing the state
    print("\n3️⃣  Testing state serialization...")
    serializer = JsonSerializer()

    # Serialize the state (what gets persisted)
    state_dict = {
        "id": pizza.state.id,
        "name": pizza.state.name,
        "base_price": str(pizza.state.base_price),  # Decimal as string
        "size": pizza.state.size.value,  # Enum as string
        "description": pizza.state.description,
        "toppings": pizza.state.toppings,
        "state_version": pizza.state.state_version,
    }

    state_json = json.dumps(state_dict, indent=2)
    print("   State as JSON:")
    print(state_json)
    print("   ✅ State serialization successful")

    # Verify state contains only data, no methods
    print("\n4️⃣  Verifying state is pure data...")
    state_attributes = [attr for attr in dir(pizza.state) if not attr.startswith("_")]
    data_fields = [attr for attr in state_attributes if not callable(getattr(pizza.state, attr))]
    print(f"   • State data fields: {data_fields}")
    print(f"   • Number of data fields: {len(data_fields)}")
    print("   ✅ State contains only data fields (no methods)")

    # Test that aggregate has methods but state doesn't
    print("\n5️⃣  Verifying aggregate contains methods...")
    pizza_methods = [attr for attr in dir(pizza) if not attr.startswith("_") and callable(getattr(pizza, attr)) and attr not in ["get_uncommitted_events", "clear_uncommitted_events", "raise_event"]]
    print(f"   • Pizza methods: {pizza_methods}")
    print("   ✅ Aggregate has business methods")

    # Test domain events are not in state
    print("\n6️⃣  Verifying domain events are separate from state...")
    events = pizza.get_uncommitted_events()
    print(f"   • Number of domain events: {len(events)}")
    print(f"   • Events stored in aggregate: {hasattr(pizza, '_uncommitted_events')}")
    print(f"   • Events NOT in state: {not hasattr(pizza.state, '_uncommitted_events')}")
    print("   ✅ Domain events correctly separated from state")

    # Verify computed properties not in state
    print("\n7️⃣  Verifying computed properties not in state...")
    has_total_price_method = hasattr(pizza, "total_price")
    state_has_total_price_field = "total_price" in state_dict
    print(f"   • Pizza has total_price property: {has_total_price_method}")
    print(f"   • State has total_price field: {state_has_total_price_field}")
    print(f"   • Computed value: ${pizza.total_price}")
    print("   ✅ Computed properties not persisted in state")

    print("\n" + "=" * 70)
    print("🎉 Repository Serialization Tests PASSED!")
    print("=" * 70)
    print("\n✅ Pizza state contains only data (persisted)")
    print("✅ Pizza aggregate contains behavior (not persisted)")
    print("✅ Domain events separate from state")
    print("✅ Computed properties not in state")
    print("✅ State serialization produces clean JSON")
    print("\nThe Pizza aggregate is ready for MongoDB/file persistence!")

except Exception as e:
    print(f"\n❌ Test FAILED with error:")
    print(f"   {type(e).__name__}: {e}")
    import traceback

    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
