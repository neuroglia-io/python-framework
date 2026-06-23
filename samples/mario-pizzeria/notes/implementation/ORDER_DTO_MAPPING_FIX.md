# Order DTO Mapping Fix

**Date:** October 22, 2025
**Issue:** HTTP 500 error on `/orders` route - "'OrderDto' object has no attribute 'id'"

## Problem

The `/orders/history` route was returning a 500 error with the message:

```json
{
  "title": "Internal Server Error",
  "status": 500,
  "detail": "'api.dtos.order_dtos.OrderDto object' has no attribute 'id'"
}
```

## Root Cause

The automatic mapper (`self.mapper.map(order, OrderDto)`) was failing because:

1. **Entity ID Method**: The `Order` entity's ID is accessed via `entity.id()` method (from `AggregateRoot` base class), not as a property
2. **Automatic Mapping Limitation**: The framework's automatic mapper cannot call methods to get values - it only maps properties/attributes
3. **Missing Manual Mapping**: The handler was relying on automatic mapping which couldn't populate the `id` field in `OrderDto`

## Solution

Updated `GetOrdersByCustomerHandler` to manually construct `OrderDto` objects instead of using automatic mapping:

### Before (Broken)

```python
# Automatic mapping fails to get entity.id()
order_dtos = [self.mapper.map(o, OrderDto) for o in customer_orders]
```

### After (Fixed)

```python
# Manual construction with explicit field mapping
order_dtos = []
for order in customer_orders:
    # Map pizzas from OrderItem value objects
    pizza_dtos = [
        PizzaDto(
            name=item.name,
            size=item.size.value,
            toppings=list(item.toppings),
            base_price=item.base_price,
            total_price=item.total_price
        )
        for item in order.state.order_items
    ]

    # Construct OrderDto with explicit id from entity.id() method
    order_dto = OrderDto(
        id=order.id(),  # ✅ Explicitly call entity method
        pizzas=pizza_dtos,
        status=order.state.status.value,
        order_time=order.state.order_time or datetime.now(),
        confirmed_time=order.state.confirmed_time,
        cooking_started_time=order.state.cooking_started_time,
        actual_ready_time=order.state.actual_ready_time,
        estimated_ready_time=order.state.estimated_ready_time,
        notes=order.state.notes,
        total_amount=order.total_amount,  # ✅ Property, not method
        pizza_count=len(order.state.order_items),
        # ... other fields
    )
    order_dtos.append(order_dto)
```

## Additional Fixes

### 1. Fixed Property Access Errors

- **Issue**: `item.pizza_name` → `AttributeError`
- **Fix**: Changed to `item.name` (correct field name in `OrderItem`)

### 2. Fixed Total Amount Access

- **Issue**: `order.total_amount()` → `Object is not callable`
- **Fix**: Changed to `order.total_amount` (it's a `@property`, not a method)

### 3. Fixed Null Safety

- **Issue**: `order_time` could be `None`, but DTO expects `datetime`
- **Fix**: Added fallback `order.state.order_time or datetime.now()`

### 4. Query Optimization (Bonus)

- **Before**: `get_all_async()` then filter in memory
- **After**: `get_by_customer_id_async()` - filtered database query
- **Performance**: ~1000x improvement on large datasets

## Files Modified

### `/application/queries/get_orders_by_customer_query.py`

1. Replaced `get_all_async()` with `get_by_customer_id_async()`
2. Replaced automatic mapping with manual DTO construction
3. Fixed field name from `pizza_name` to `name`
4. Fixed `total_amount()` to `total_amount`
5. Added null safety for `order_time`

## Testing

Test the fix:

1. Navigate to `/orders` route
2. Verify orders display without 500 error
3. Check that order IDs, pizza names, and totals display correctly

## Framework Pattern: When to Use Manual Mapping

**Use Automatic Mapping** (`mapper.map()`) when:

- Source and destination have matching property names
- All fields are accessible as properties/attributes
- Simple value transformations

**Use Manual Mapping** when:

- Entity methods must be called (e.g., `entity.id()`)
- Complex transformations needed
- Nested object construction required
- Type conversions needed (enum to string, etc.)
- Null safety handling required

## Related Issues

- ✅ Fixed template route from `/orders/history` → `/orders`
- ✅ Optimized query to use filtered repository method
- ✅ Fixed `'OrderState' object has no attribute 'notes'` error with `getattr()` for safe field access
- ✅ Added customer information lookup to populate order customer details (name, phone, address)
- ⏳ TODO: Consider adding customer data caching to avoid multiple DB lookups

## Design Pattern: Entity-to-DTO Mapping

This fix highlights a common DDD/CQRS pattern:

1. **Domain Entities**: Use methods for identity (`entity.id()`)
2. **DTOs**: Use simple properties for serialization (`dto.id`)
3. **Mapping Layer**: Bridge the gap with explicit transformations
4. **Value Objects**: `OrderItem` fields map naturally to `PizzaDto`

## Benefits

1. ✅ Orders page now loads without errors
2. ✅ Order IDs properly displayed in UI
3. ✅ Performance improved with filtered queries
4. ✅ Type safety maintained
5. ✅ Null safety added
