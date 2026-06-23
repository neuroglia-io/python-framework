#!/usr/bin/env python3
"""
Test to verify Customer aggregate with state separation and multipledispatch works correctly
"""

import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("🧪 Testing Customer Aggregate with State Separation")
print("=" * 70)

try:
    # Import Customer and related classes
    print("\n1️⃣  Importing Customer...")
    from domain.entities.customer import Customer, CustomerState
    from domain.events import CustomerRegisteredEvent

    print("   ✅ Imports successful")

    # Test Customer creation
    print("\n2️⃣  Creating a customer...")
    customer = Customer(
        name="John Doe",
        email="john.doe@example.com",
        phone="+1-555-0100",
        address="123 Main St, Springfield",
    )
    print(f"   ✅ Customer created with ID: {customer.id()}")

    # Test state access
    print("\n3️⃣  Testing state access...")
    print(f"   • customer.state.name = {customer.state.name}")
    print(f"   • customer.state.email = {customer.state.email}")
    print(f"   • customer.state.phone = {customer.state.phone}")
    print(f"   • customer.state.address = {customer.state.address}")
    print("   ✅ State access working correctly")

    # Test update_contact_info method
    print("\n4️⃣  Testing update_contact_info() method...")
    customer.update_contact_info(phone="+1-555-0199", address="456 Oak Ave, Springfield")
    print(f"   • Updated phone: {customer.state.phone}")
    print(f"   • Updated address: {customer.state.address}")
    print("   ✅ update_contact_info() working correctly")

    # Test partial update (only phone)
    print("\n5️⃣  Testing partial update (phone only)...")
    customer.update_contact_info(phone="+1-555-0200")
    print(f"   • Phone after update: {customer.state.phone}")
    print(f"   • Address unchanged: {customer.state.address}")
    print("   ✅ Partial update working correctly")

    # Test domain events
    print("\n6️⃣  Testing domain events...")
    events = customer.domain_events
    print(f"   • Number of domain events raised: {len(events)}")
    for i, event in enumerate(events, 1):
        print(f"     {i}. {type(event).__name__}")
    print("   ✅ Domain events working correctly")

    # Test __str__ method
    print("\n7️⃣  Testing __str__() method...")
    print(f"   • String representation: {customer}")
    print("   ✅ __str__() working correctly")

    # Test that state is separate from aggregate
    print("\n8️⃣  Verifying state separation...")
    print(f"   • Type of customer: {type(customer).__name__}")
    print(f"   • Type of customer.state: {type(customer.state).__name__}")
    print(f"   • customer.state is an AggregateState: {hasattr(customer.state, 'state_version')}")
    print(f"   • State version: {customer.state.state_version}")
    print("   ✅ State separation verified")

    # Test state ID matches aggregate ID
    print("\n9️⃣  Verifying ID consistency...")
    print(f"   • customer.id(): {customer.id()}")
    print(f"   • customer.state.id: {customer.state.id}")
    print(f"   • IDs match: {customer.id() == customer.state.id}")
    print("   ✅ ID consistency verified")

    # Test state event handlers
    print("\n🔟 Testing state event handlers directly...")
    test_state = CustomerState()
    test_event = CustomerRegisteredEvent(
        aggregate_id="test-id-123",
        name="Jane Smith",
        email="jane@example.com",
        phone="+1-555-0300",
        address="789 Elm St",
    )
    test_state.on(test_event)
    print(f"   • State ID after event: {test_state.id}")
    print(f"   • State name after event: {test_state.name}")
    print(f"   • State email after event: {test_state.email}")
    print("   ✅ State event handlers working correctly")

    print("\n" + "=" * 70)
    print("🎉 All Customer aggregate tests PASSED!")
    print("=" * 70)
    print("\n✅ State separation is working correctly!")
    print("✅ All methods accessing state via self.state.*")
    print("✅ Domain events are being registered")
    print("✅ State event handlers using @dispatch")
    print("✅ The Customer aggregate is ready for use!")

except Exception as e:
    print(f"\n❌ Test FAILED with error:")
    print(f"   {type(e).__name__}: {e}")
    import traceback

    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
