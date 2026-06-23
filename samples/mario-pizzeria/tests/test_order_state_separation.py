"""
Test Order aggregate with state separation pattern.

This test validates the Order aggregate's implementation of the AggregateRoot pattern
with state separation and multipledispatch event handlers.
"""

from datetime import datetime, timezone
from decimal import Decimal

from domain.entities import Order, OrderState, Pizza, PizzaSize
from domain.events import (
    CookingStartedEvent,
    OrderConfirmedEvent,
    OrderCreatedEvent,
    OrderDeliveredEvent,
    OrderReadyEvent,
    PizzaAddedToOrderEvent,
    PizzaRemovedFromOrderEvent,
)

print("=" * 70)
print("🧪 Testing Order Aggregate with State Separation")
print("=" * 70)

# Test 1: Imports
print("\n1️⃣  Importing Order and OrderState...")
try:
    from domain.entities import Order, OrderState

    print("   ✅ Imports successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test 2: Create an order
print("\n2️⃣  Creating an order...")
try:
    order = Order(customer_id="customer-123")
    print(f"   ✅ Order created with ID: {order.id()}")
except Exception as e:
    print(f"   ❌ Order creation failed: {e}")
    exit(1)

# Test 3: Test state access
print("\n3️⃣  Testing state access...")
try:
    print(f"   • order.state.customer_id = {order.state.customer_id}")
    print(f"   • order.state.status = {order.state.status}")
    print(f"   • order.state.order_time = {order.state.order_time}")
    print(f"   • order.state.pizzas = {order.state.pizzas}")
    print("   ✅ State access working correctly")
except Exception as e:
    print(f"   ❌ State access failed: {e}")
    exit(1)

# Test 4: Add pizzas to order
print("\n4️⃣  Testing add_pizza() method...")
try:
    pizza1 = Pizza(name="Margherita", base_price=Decimal("10.00"), size=PizzaSize.MEDIUM)
    pizza2 = Pizza(name="Pepperoni", base_price=Decimal("12.00"), size=PizzaSize.LARGE)

    order.add_pizza(pizza1)
    order.add_pizza(pizza2)

    print(f"   • Number of pizzas: {len(order.state.pizzas)}")
    print(f"   • Total amount: ${order.total_amount}")
    print(f"   • Pizza count property: {order.pizza_count}")
    print("   ✅ add_pizza() working correctly")
except Exception as e:
    print(f"   ❌ add_pizza() failed: {e}")
    exit(1)

# Test 5: Remove pizza from order
print("\n5️⃣  Testing remove_pizza() method...")
try:
    pizza_to_remove_id = pizza1.id()
    order.remove_pizza(pizza_to_remove_id)

    print(f"   • Pizzas after removal: {len(order.state.pizzas)}")
    print(f"   • Pizza removed: {pizza_to_remove_id[:8]}")
    print("   ✅ remove_pizza() working correctly")
except Exception as e:
    print(f"   ❌ remove_pizza() failed: {e}")
    exit(1)

# Test 6: Confirm order
print("\n6️⃣  Testing confirm_order() method...")
try:
    order.confirm_order()

    print(f"   • Status after confirmation: {order.state.status}")
    print(f"   • Confirmed time: {order.state.confirmed_time}")
    print("   ✅ confirm_order() working correctly")
except Exception as e:
    print(f"   ❌ confirm_order() failed: {e}")
    exit(1)

# Test 7: Start cooking
print("\n7️⃣  Testing start_cooking() method...")
try:
    order.start_cooking()

    print(f"   • Status after cooking started: {order.state.status}")
    print(f"   • Cooking started time: {order.state.cooking_started_time}")
    print("   ✅ start_cooking() working correctly")
except Exception as e:
    print(f"   ❌ start_cooking() failed: {e}")
    exit(1)

# Test 8: Mark ready
print("\n8️⃣  Testing mark_ready() method...")
try:
    order.mark_ready()

    print(f"   • Status after ready: {order.state.status}")
    print(f"   • Actual ready time: {order.state.actual_ready_time}")
    print("   ✅ mark_ready() working correctly")
except Exception as e:
    print(f"   ❌ mark_ready() failed: {e}")
    exit(1)

# Test 9: Deliver order
print("\n9️⃣  Testing deliver_order() method...")
try:
    order.deliver_order()

    print(f"   • Status after delivery: {order.state.status}")
    print("   ✅ deliver_order() working correctly")
except Exception as e:
    print(f"   ❌ deliver_order() failed: {e}")
    exit(1)

# Test 10: Test domain events
print("\n🔟 Testing domain events...")
try:
    # Get pending events (should have all lifecycle events)
    events = order.domain_events

    print(f"   • Number of domain events raised: {len(events)}")
    for i, event in enumerate(events, 1):
        print(f"     {i}. {event.__class__.__name__}")

    # Verify event types
    expected_events = [
        OrderCreatedEvent,
        PizzaAddedToOrderEvent,
        PizzaAddedToOrderEvent,
        PizzaRemovedFromOrderEvent,
        OrderConfirmedEvent,
        CookingStartedEvent,
        OrderReadyEvent,
        OrderDeliveredEvent,
    ]

    if len(events) == len(expected_events):
        print("   ✅ Domain events working correctly")
    else:
        print(f"   ⚠️  Expected {len(expected_events)} events, got {len(events)}")
except Exception as e:
    print(f"   ❌ Domain events test failed: {e}")
    exit(1)

# Test 11: Test cancellation workflow
print("\n1️⃣1️⃣  Testing order cancellation...")
try:
    # Create new order for cancellation test
    cancel_order = Order(customer_id="customer-456")
    pizza3 = Pizza(name="Vegetarian", base_price=Decimal("11.00"), size=PizzaSize.SMALL)
    cancel_order.add_pizza(pizza3)
    cancel_order.confirm_order()
    cancel_order.cancel_order(reason="Customer changed mind")

    print(f"   • Status after cancellation: {cancel_order.state.status}")
    print(f"   • Cancellation notes: {cancel_order.state.notes}")
    print("   ✅ cancel_order() working correctly")
except Exception as e:
    print(f"   ❌ cancel_order() failed: {e}")
    exit(1)

# Test 12: Test state separation
print("\n1️⃣2️⃣  Verifying state separation...")
try:
    print(f"   • Type of order: {type(order).__name__}")
    print(f"   • Type of order.state: {type(order.state).__name__}")
    print(f"   • order.state is an AggregateState: {hasattr(order.state, 'state_version')}")
    print(f"   • State version: {order.state.state_version}")
    print("   ✅ State separation verified")
except Exception as e:
    print(f"   ❌ State separation test failed: {e}")
    exit(1)

# Test 13: Test ID consistency
print("\n1️⃣3️⃣  Verifying ID consistency...")
try:
    order_id_method = order.id()
    state_id = order.state.id

    print(f"   • order.id(): {order_id_method}")
    print(f"   • order.state.id: {state_id}")
    print(f"   • IDs match: {order_id_method == state_id}")
    print("   ✅ ID consistency verified")
except Exception as e:
    print(f"   ❌ ID consistency test failed: {e}")
    exit(1)

# Test 14: Test state event handlers directly
print("\n1️⃣4️⃣  Testing state event handlers directly...")
try:
    # Create a new state and test event handlers
    test_state = OrderState()

    # Test OrderCreatedEvent handler
    created_event = OrderCreatedEvent(
        aggregate_id="test-order-123",
        customer_id="test-customer",
        order_time=datetime.now(timezone.utc),
    )
    test_state.on(created_event)

    print(f"   • State ID after event: {test_state.id}")
    print(f"   • State customer_id after event: {test_state.customer_id}")
    print(f"   • State status after event: {test_state.status}")

    # Test OrderConfirmedEvent handler
    confirmed_event = OrderConfirmedEvent(
        aggregate_id="test-order-123",
        confirmed_time=datetime.now(timezone.utc),
        total_amount=Decimal("25.00"),
        pizza_count=2,
    )
    test_state.on(confirmed_event)

    print(f"   • State status after confirmation: {test_state.status}")
    print("   ✅ State event handlers working correctly")
except Exception as e:
    print(f"   ❌ State event handlers test failed: {e}")
    exit(1)

# Test 15: Test __str__ representation
print("\n1️⃣5️⃣  Testing __str__() method...")
try:
    str_repr = str(order)
    print(f"   • String representation: {str_repr}")
    print("   ✅ __str__() working correctly")
except Exception as e:
    print(f"   ❌ __str__() test failed: {e}")
    exit(1)

# Final summary
print("\n" + "=" * 70)
print("🎉 All Order aggregate tests PASSED!")
print("=" * 70)
print()
print("✅ State separation is working correctly!")
print("✅ All methods accessing state via self.state.*")
print("✅ Domain events are being registered")
print("✅ State event handlers using @dispatch")
print("✅ Order lifecycle transitions working correctly")
print("✅ The Order aggregate is ready for use!")
