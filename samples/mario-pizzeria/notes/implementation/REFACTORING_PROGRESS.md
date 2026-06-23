# Mario's Pizzeria - AggregateRoot Refactoring Notes

## Refactoring Progress

Migrating all aggregates from custom AggregateRoot to Neuroglia's `AggregateRoot[TState, TKey]` with multipledispatch event handlers.

## Pattern Summary

- **State and Aggregate**: In same file for maintainability
- **Event Handlers**: Using `@dispatch` from `multipledispatch` library
- **Event Registration**: `self.state.on(self.register_event(Event(...)))`
- **ID Access**: `self.id()` method (not property)

## Aggregate Status

### ✅ Pizza Aggregate - COMPLETED

**File**: `domain/entities/pizza.py`

**Changes Made**:

- Moved `PizzaState` into same file as `Pizza`
- Added `@dispatch` event handlers to `PizzaState`
- Changed to `AggregateRoot[PizzaState, str]`
- Using `register_event()` instead of `raise_event()`
- All state mutations through event handlers

**Events**:

- `PizzaCreatedEvent(aggregate_id, name, size, base_price, description, toppings)`
- `ToppingsUpdatedEvent(aggregate_id, toppings)`

**Tests**: All passing ✅

### ✅ Customer Aggregate - COMPLETED

**File**: `domain/entities/customer.py`

**Changes Made**:

- Moved `CustomerState` into same file as `Customer`
- Added `@dispatch` event handlers to `CustomerState`
- Changed to `AggregateRoot[CustomerState, str]`
- Using `register_event()` instead of `raise_event()`
- Updated events to include all necessary fields

**Events Updated**:

- `CustomerRegisteredEvent(aggregate_id, name, email, phone, address)` - Added `address` field
- `CustomerContactUpdatedEvent(aggregate_id, phone, address)` - Simplified from field_name/old_value/new_value

**Tests**: All passing ✅ (`test_customer_state_separation.py` - 10 test scenarios)

### ✅ Order Aggregate - COMPLETED

**File**: `domain/entities/order.py`

**Changes Made**:

- Created `OrderState` in same file as `Order`
- Added `@dispatch` event handlers for all 8 order lifecycle events
- Changed to `AggregateRoot[OrderState, str]`
- Using `register_event()` instead of `raise_event()`
- Removed legacy `__getattr__` method
- Removed temporary duck typing code

**Events Handled**:

- `OrderCreatedEvent(aggregate_id, customer_id, order_time)` - Initialize order
- `PizzaAddedToOrderEvent(aggregate_id, pizza_id, pizza_name, pizza_size, price)` - Track pizza additions
- `PizzaRemovedFromOrderEvent(aggregate_id, pizza_id)` - Track pizza removals
- `OrderConfirmedEvent(aggregate_id, confirmed_time, total_amount, pizza_count)` - PENDING → CONFIRMED
- `CookingStartedEvent(aggregate_id, cooking_started_time)` - CONFIRMED → COOKING
- `OrderReadyEvent(aggregate_id, ready_time, estimated_ready_time)` - COOKING → READY
- `OrderDeliveredEvent(aggregate_id, delivered_time)` - READY → DELIVERED
- `OrderCancelledEvent(aggregate_id, cancelled_time, reason)` - Any status → CANCELLED

**Complexity**: High - manages pizzas collection, 6 status transitions, business rules

**Tests**: All passing ✅ (`test_order_state_separation.py` - 15 test scenarios including full lifecycle)

### ⏳ Kitchen Entity - PENDING REVIEW

**File**: `domain/entities/kitchen.py`

## Event Updates Made

### Pizza Events (`domain/events.py`)

**PizzaCreatedEvent**:

- Added `description: str` field
- Now has all fields needed for state initialization

**ToppingsUpdatedEvent**:

- Changed from `old_toppings, new_toppings` to just `toppings`
- Simpler event - state handler just replaces list

## Testing Strategy

### Unit Tests (State Handlers)

Test each event handler independently:

```python
def test_customer_state_handles_created_event():
    state = CustomerState()
    event = CustomerCreatedEvent(
        aggregate_id="test-id",
        name="John Doe",
        email="john@example.com"
    )

    state.on(event)

    assert state.id == "test-id"
    assert state.name == "John Doe"
    assert state.email == "john@example.com"
```

### Integration Tests (Aggregates)

Test full aggregate behavior:

```python
def test_customer_aggregate_creation():
    customer = Customer(name="John Doe", email="john@example.com")

    assert customer.state.name == "John Doe"
    assert customer.state.email == "john@example.com"

    events = customer.domain_events
    assert len(events) == 1
    assert isinstance(events[0], CustomerCreatedEvent)
```

### Event Replay Tests

Verify state can be reconstructed:

```python
def test_customer_state_replay():
    state = CustomerState()

    events = [
        CustomerCreatedEvent(...),
        CustomerDetailsUpdatedEvent(...),
    ]

    for event in events:
        state.on(event)

    # Verify final state
    assert state.name == "Updated Name"
```

## Files Modified

### Core Changes

1. `pyproject.toml` - Added `multipledispatch` dependency
2. `domain/events.py` - Updated Pizza events
3. `domain/entities/pizza.py` - Refactored (state + aggregate)
4. `domain/entities/pizza_state.py` - DELETED (merged into pizza.py)

### Test Changes

1. `tests/test_pizza_state_separation.py` - Updated for `id()` method
2. `tests/test_pizza_serialization.py` - Verified still works

## Command Handler Updates Needed

Once all aggregates are refactored:

### PlaceOrderCommandHandler

**Before**:

```python
order = Order(...)
# Workaround for type compatibility
cast(NeuroAggregateRoot, order)
unit_of_work.register_aggregate(order)
```

**After**:

```python
order = Order(...)
unit_of_work.register_aggregate(order)  # Direct registration
```

### Other Handlers

Check all handlers for:

- Type casting workarounds
- Direct field manipulation (should use methods that emit events)
- Proper event collection

## Known Issues / Type Checker Warnings

### Multipledispatch and Type Checkers

Pylance/Pyright will show warnings:

- "Method declaration 'on' is obscured"
- "Argument type mismatch"

These are **safe to ignore** - runtime dispatch works correctly.

### Optional Workarounds

Add type ignore comments:

```python
self.state.on(  # type: ignore[arg-type]
    self.register_event(Event(...))
)
```

Or configure `.pylance/pyrightconfig.json` to be more lenient with multipledispatch.

## Migration Checklist Template

For each aggregate:

- [ ] Read current aggregate implementation
- [ ] Identify all domain events
- [ ] Update events if needed (ensure complete data)
- [ ] Create/update State class with @dispatch handlers
- [ ] Move State into same file as Aggregate
- [ ] Update Aggregate to use `AggregateRoot[TState, str]`
- [ ] Replace direct state mutations with event-based mutations
- [ ] Change `raise_event()` to `register_event()`
- [ ] Wrap with `self.state.on()`
- [ ] Update all `self.id` to `self.id()`
- [ ] Update tests for new pattern
- [ ] Add state handler unit tests
- [ ] Verify integration tests still pass
- [ ] Check serialization works

## Next Actions

1. **Customer Aggregate** (Current)

   - Examine current implementation
   - Design CustomerCreatedEvent
   - Implement state handlers
   - Refactor aggregate
   - Update tests

2. **Order Aggregate**

   - More complex - has collection of pizzas
   - Multiple events (add/remove pizzas)
   - Status transitions

3. **Kitchen Aggregate**

   - Workflow states
   - Time tracking

4. **Integration Testing**
   - Full app smoke test
   - Verify UnitOfWork collects events
   - Test event dispatching
   - MongoDB persistence

---

**Last Updated**: 2025-10-07
**Current Task**: Customer aggregate refactoring
**Next**: Order aggregate
