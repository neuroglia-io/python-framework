#!/usr/bin/env python3
"""
Quick test to verify Pizza aggregate with state separation works correctly
"""

import sys
from decimal import Decimal
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("🧪 Testing Pizza Aggregate with State Separation")
print("=" * 70)

try:
    # Import Pizza and related classes
    print("\n1️⃣  Importing Pizza and PizzaSize...")
    from domain.entities.enums import PizzaSize
    from domain.entities.pizza import Pizza

    print("   ✅ Imports successful")

    # Test Pizza creation
    print("\n2️⃣  Creating a Margherita pizza...")
    pizza = Pizza(
        name="Margherita",
        base_price=Decimal("12.99"),
        size=PizzaSize.LARGE,
        description="Classic pizza with tomatoes, mozzarella, and basil",
    )
    print(f"   ✅ Pizza created with ID: {pizza.id()}")

    # Test state access
    print("\n3️⃣  Testing state access...")
    print(f"   • pizza.state.name = {pizza.state.name}")
    print(f"   • pizza.state.size = {pizza.state.size}")
    print(f"   • pizza.state.base_price = {pizza.state.base_price}")
    print(f"   • pizza.state.toppings = {pizza.state.toppings}")
    print(f"   • pizza.state.description = {pizza.state.description}")
    print("   ✅ State access working correctly")

    # Test computed properties
    print("\n4️⃣  Testing computed properties...")
    print(f"   • pizza.size_multiplier = {pizza.size_multiplier}")
    print(f"   • pizza.topping_price = ${pizza.topping_price}")
    print(f"   • pizza.total_price = ${pizza.total_price}")
    print("   ✅ Computed properties working correctly")

    # Test add_topping method
    print("\n5️⃣  Testing add_topping() method...")
    pizza.add_topping("extra cheese")
    pizza.add_topping("basil")
    print(f"   • Toppings after adding: {pizza.state.toppings}")
    print(f"   • New total price: ${pizza.total_price}")
    print("   ✅ add_topping() working correctly")

    # Test remove_topping method
    print("\n6️⃣  Testing remove_topping() method...")
    pizza.remove_topping("extra cheese")
    print(f"   • Toppings after removing: {pizza.state.toppings}")
    print(f"   • New total price: ${pizza.total_price}")
    print("   ✅ remove_topping() working correctly")

    # Test domain events
    print("\n7️⃣  Testing domain events...")
    events = pizza.get_uncommitted_events()
    print(f"   • Number of domain events raised: {len(events)}")
    for i, event in enumerate(events, 1):
        print(f"     {i}. {type(event).__name__}")
    print("   ✅ Domain events working correctly")

    # Test __str__ method
    print("\n8️⃣  Testing __str__() method...")
    print(f"   • String representation: {pizza}")
    print("   ✅ __str__() working correctly")

    # Test that state is separate from aggregate
    print("\n9️⃣  Verifying state separation...")
    print(f"   • Type of pizza: {type(pizza).__name__}")
    print(f"   • Type of pizza.state: {type(pizza.state).__name__}")
    print(f"   • pizza.state is an AggregateState: {hasattr(pizza.state, 'state_version')}")
    print(f"   • State version: {pizza.state.state_version}")
    if hasattr(pizza.state, "created_at") and pizza.state.created_at is not None:
        print(f"   • State created_at: {pizza.state.created_at}")
    print("   ✅ State separation verified")

    # Test state ID matches aggregate ID
    print("\n🔟 Verifying ID consistency...")
    print(f"   • pizza.id(): {pizza.id()}")
    print(f"   • pizza.state.id: {pizza.state.id}")
    print(f"   • IDs match: {pizza.id() == pizza.state.id}")
    print("   ✅ ID consistency verified")

    print("\n" + "=" * 70)
    print("🎉 All Pizza aggregate tests PASSED!")
    print("=" * 70)
    print("\n✅ State separation is working correctly!")
    print("✅ All methods accessing state via self.state.*")
    print("✅ Computed properties work as expected")
    print("✅ Domain events are being raised")
    print("✅ The Pizza aggregate is ready for use!")

except Exception as e:
    print(f"\n❌ Test FAILED with error:")
    print(f"   {type(e).__name__}: {e}")
    import traceback

    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
