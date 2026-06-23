# Kitchen View Filter Fix

## Issue Reported

**Date**: October 23, 2025
**Reporter**: User
**Problem**: ALL orders were showing up on the kitchen view, including orders that should not be in the kitchen's responsibility.

## Root Cause

The `GetActiveKitchenOrdersQuery` was using `get_active_orders_async()` which returns **all non-delivered and non-cancelled orders**. This includes:

- ✅ PENDING - Should show in kitchen
- ✅ CONFIRMED - Should show in kitchen
- ✅ COOKING - Should show in kitchen
- ❌ READY - Should NOT show (waiting for driver pickup)
- ❌ DELIVERING - Should NOT show (already with driver)

The kitchen view was displaying orders in READY and DELIVERING status, which are outside the kitchen's responsibility once the food is cooked.

## Solution

Added explicit filtering in `GetActiveKitchenOrdersHandler` to only show kitchen-relevant statuses:

```python
# Filter for kitchen-relevant orders only
kitchen_orders = [
    order for order in active_orders
    if order.state.status.value in ["pending", "confirmed", "cooking"]
]
```

## Order Lifecycle and Responsibility

### Kitchen Responsibility (Should show in kitchen view)

1. **PENDING** → New order placed, waiting for kitchen confirmation
2. **CONFIRMED** → Kitchen has acknowledged, preparing to cook
3. **COOKING** → Actively being prepared by kitchen staff

### Driver/Delivery Responsibility (Should NOT show in kitchen view)

4. **READY** → Food is cooked and ready for driver pickup
5. **DELIVERING** → Driver has picked up and is delivering to customer

### Terminal States (Never show in kitchen view)

6. **DELIVERED** → Order successfully completed
7. **CANCELLED** → Order was cancelled

## Files Modified

**File**: `application/queries/get_active_kitchen_orders_query.py`

**Changes**:

- Added detailed comments explaining kitchen responsibility stages
- Added filter to only include ["pending", "confirmed", "cooking"] statuses
- Changed loop variable from `active_orders` to `kitchen_orders` for clarity

## Testing

After restart, verify:

1. Kitchen view (`/kitchen`) only shows orders in PENDING, CONFIRMED, or COOKING status
2. Orders in READY status do not appear in kitchen view
3. Orders in DELIVERING status do not appear in kitchen view
4. Delivered and cancelled orders do not appear

## Related Components

- **Query**: `application/queries/get_active_kitchen_orders_query.py`
- **Repository Method**: `IOrderRepository.get_active_orders_async()` - Still returns all active orders (by design)
- **Kitchen View**: `ui/templates/kitchen/dashboard.html`
- **Kitchen Controller**: `ui/controllers/kitchen_controller.py`

## Design Rationale

### Why not change `get_active_orders_async()`?

The repository method `get_active_orders_async()` is intentionally broad and returns all non-terminal orders. This is correct because:

1. **Reusability**: Other queries might need different definitions of "active"
2. **Management View**: Management dashboard needs to see ALL active orders including READY and DELIVERING
3. **Separation of Concerns**: Business logic about what's "relevant" to a specific view belongs in the query handler, not the repository

### Kitchen-Specific Filtering

The filter is applied in `GetActiveKitchenOrdersHandler` because:

- It's a **kitchen-specific business rule**
- Different views have different relevance criteria
- Keeps repository methods generic and reusable

## Impact

✅ **Kitchen View**: Now correctly shows only orders kitchen staff need to work on
✅ **Management View**: Unaffected - still shows all active orders
✅ **API Endpoints**: Kitchen stream now sends correct filtered list
✅ **Real-time Updates**: SSE updates reflect proper filtering

## Future Considerations

If we add more views (e.g., driver view), create view-specific queries:

- `GetKitchenOrdersQuery` - ["pending", "confirmed", "cooking"]
- `GetDriverOrdersQuery` - ["ready", "delivering"]
- `GetAllActiveOrdersQuery` - ["pending", "confirmed", "cooking", "ready", "delivering"]

Each query would apply appropriate filtering based on the user role and view context.

---

**Status**: ✅ Fixed
**Deployed**: Pending application restart
**Verification**: Test kitchen view after restarting Mario's Pizzeria
