# Integration Test Issues - Mario's Pizzeria Refactoring

## Date: October 8, 2025

## Summary

After refactoring all aggregates (Pizza, Customer, Order) to use Neuroglia's `AggregateRoot[TState, TKey]` pattern with `multipledispatch` @dispatch event handlers, integration tests are revealing serialization/deserialization issues.

## Completed Work ✅

### 1. Aggregate Refactoring

- **Pizza**: PizzaState + Pizza(AggregateRoot[PizzaState, str]) ✅
- **Customer**: CustomerState + Customer(AggregateRoot[CustomerState, str]) ✅
- **Order**: OrderState + Order(AggregateRoot[OrderState, str]) with 8 event handlers ✅
- **Kitchen**: Remains Entity[str] (correctly, no refactoring needed) ✅

### 2. Handler Updates

- **Command Handlers**: Removed all `cast(NeuroAggregateRoot, ...)` workarounds ✅
- **Query Handlers**: Updated to use `order.state.*` and `order.id()` pattern ✅

### 3. Repository Updates

- **FileSystemRepository**: Added `_get_entity_id()` helper to handle both `entity.id` property (Entity) and `entity.id()` method (AggregateRoot) ✅
- **FileOrderRepository**: Updated queries to use `order.state.status`, `order.state.created_at` ✅
- **FileCustomerRepository**: Updated queries to use `customer.state.phone`, `customer.state.email` ✅

## Current Issues ❌

### Issue 1: AggregateRoot Serialization/Deserialization

**Problem**: The `JsonSerializer` is not properly handling AggregateRoot objects with state separation.

**Root Cause**:

1. When serializing an AggregateRoot, the serializer appears to flatten the state fields directly onto the aggregate object
2. When deserializing, it reconstructs the object but doesn't properly initialize the `state` attribute
3. The `AggregateRoot.__init__()` creates the state using `__orig_bases__` reflection, but JSON deserialization bypasses `__init__`

**Evidence**:

```bash
# Old JSON structure (before refactoring)
{
    "id": "951b9282-b39c-495a-b879-5926166339f5",
    "customer_id": "ed666580-14d3-4ade-a726-a7b2535ee7ab",
    "pizzas": [...],
    "status": "CONFIRMED",
    ...
}

# Expected new structure (with state separation)
{
    "state": {
        "id": "951b9282-b39c-495a-b879-5926166339f5",
        "customer_id": "ed666580-14d3-4ade-a726-a7b2535ee7ab",
        "pizzas": [...],
        "status": "CONFIRMED",
        ...
    },
    "_pending_events": []
}
```

**Error when loading from disk**:

```python
AttributeError: 'Order' object has no attribute 'state'
```

This happens because:

1. The deserialized Order object doesn't have `state` attribute initialized
2. Repository queries try to access `order.state.status` and fail

### Issue 2: ID Method vs Property

**Problem**: Fixed in FileSystemRepository, but the serializer was creating files with names like:

```
<bound method AggregateRoot.id of <domain.entities.order.Order object at 0x...>>.json
```

**Solution Applied**: Added `_get_entity_id()` helper that checks if `id` is callable and calls it if needed.

### Issue 3: Test Data Incompatibility

**Problem**: Old test data was created with the custom AggregateRoot implementation and has a different structure.

**Solution Applied**: Deleted all old JSON files from `data/` directories.

## What Needs to Be Fixed 🔧

### Option 1: Fix JsonSerializer to Handle AggregateRoot

**Approach**: Modify the JsonSerializer to:

1. Detect when serializing an AggregateRoot
2. Extract the `state` object and serialize it properly
3. On deserialization, reconstruct both the aggregate and its state

**Pros**:

- Proper solution that works with the framework design
- Maintains clean separation between aggregate and state

**Cons**:

- Requires changes to core Neuroglia framework
- Complex to implement correctly

### Option 2: Custom Serialization for Mario's Pizzeria Aggregates

**Approach**: Add `__getstate__` and `__setstate__` methods to Order, Customer, Pizza:

```python
class Order(AggregateRoot[OrderState, str]):
    def __getstate__(self):
        """Custom serialization"""
        return {
            'state': self.state.__dict__,
            '_pending_events': self._pending_events
        }

    def __setstate__(self, state_dict):
        """Custom deserialization"""
        self._pending_events = state_dict.get('_pending_events', [])
        self.state = OrderState()
        self.state.__dict__.update(state_dict['state'])
```

**Pros**:

- Localized fix, doesn't touch framework
- Can be applied immediately to unblock testing

**Cons**:

- Workaround, not a proper solution
- Every aggregate needs this boilerplate

### Option 3: Use Event Sourcing Instead of State Persistence

**Approach**: Store domain events instead of aggregate state:

1. Use `EventStore` instead of `FileSystemRepository`
2. Reconstruct aggregates from events on load
3. This is the "proper" DDD/CQRS approach

**Pros**:

- Aligns with Neuroglia's event-sourcing capabilities
- Proper DDD implementation
- Complete audit trail

**Cons**:

- Requires significant changes to repositories
- More complex setup
- Overkill for a sample application?

## Recommended Path Forward 🎯

### Short Term (Unblock Testing)

1. **Add `__setstate__` to aggregates** as a temporary workaround
2. **Test if this resolves the deserialization issue**
3. **Continue with integration testing**

### Medium Term (Proper Fix)

1. **Investigate how OpenBank sample handles this** - check if it has the same issue or uses event sourcing
2. **Consult with framework maintainers** about proper AggregateRoot serialization
3. **Implement proper solution** in JsonSerializer or document the pattern

### Long Term (Best Practice)

1. **Consider event sourcing** for the sample if it's meant to demonstrate best practices
2. **Document the pattern** for users of the framework
3. **Add tests** to Neuroglia framework for AggregateRoot serialization/deserialization

## Test Results Before Fixing 📊

```bash
===================================================================== 8 failed, 6 passed in 1.88s ======================================================================

FAILED tests/test_integration.py::TestPizzaOrderingWorkflow::test_create_order_valid - KeyError: 'name'
FAILED tests/test_integration.py::TestPizzaOrderingWorkflow::test_get_orders - assert 400 == 200
FAILED tests/test_integration.py::TestPizzaOrderingWorkflow::test_get_order_by_id - assert 400 == 201
FAILED tests/test_integration.py::TestPizzaOrderingWorkflow::test_start_cooking_order - assert 400 == 201
FAILED tests/test_integration.py::TestPizzaOrderingWorkflow::test_complete_order - KeyError: 'id'
FAILED tests/test_integration.py::TestPizzaOrderingWorkflow::test_complete_workflow - assert 400 == 201
FAILED tests/test_integration.py::TestPizzaOrderingWorkflow::test_create_order - assert 422 == 201
FAILED tests/test_integration.py::TestPizzaOrderingWorkflow::test_get_orders - assert 400 == 200
```

### Passing Tests

- `test_get_menu` ✅ (no aggregates involved)
- `test_create_order_invalid_phone` ✅ (validation only)
- `test_create_order_invalid_payment` ✅ (validation only)
- `test_get_nonexistent_order` ✅ (returns 404)
- `test_get_orders_by_status` ✅ (empty result)
- `test_kitchen_status` ✅ (Entity, not AggregateRoot)

### Failing Tests

All tests that create or retrieve Orders/Customers fail due to state access issues.

## Next Steps 🚀

1. Add `__setstate__`/`__getstate__` to Order, Customer, Pizza aggregates
2. Test if this resolves deserialization
3. If successful, continue with integration testing
4. Document the issue and solution
5. Consider raising this with Neuroglia framework maintainers

## Files Modified

### Core Framework

- `src/neuroglia/data/infrastructure/filesystem/filesystem_repository.py`
  - Added `_get_entity_id()` helper method
  - Updated `add_async()` to use helper
  - Updated `update_async()` to use helper

### Mario's Pizzeria

- `samples/mario-pizzeria/integration/repositories/generic_file_order_repository.py`
  - Updated all queries to use `order.state.*`
- `samples/mario-pizzeria/integration/repositories/generic_file_customer_repository.py`
  - Updated all queries to use `customer.state.*`

## Questions for Framework Maintainers 🤔

1. Is AggregateRoot meant to be persisted directly, or only through event sourcing?
2. Should JsonSerializer have special handling for AggregateRoot types?
3. How does OpenBank sample handle aggregate persistence?
4. Is there a documented pattern for state-based (vs event-sourced) aggregate persistence?
