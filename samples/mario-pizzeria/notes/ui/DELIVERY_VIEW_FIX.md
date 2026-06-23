# Delivery View Fix - Show READY and DELIVERING Orders

## Issue Description

After fixing the kitchen view to only show kitchen-relevant orders (PENDING, CONFIRMED, COOKING), the delivery view stopped showing READY orders. This was because the delivery view was using `GetReadyOrdersQuery` which only fetches orders with status READY, but delivery drivers need to see both:

1. **READY orders** - Pizzas finished cooking, waiting for driver pickup
2. **DELIVERING orders** - Orders currently out for delivery with a driver

## Root Cause

The `GetReadyOrdersQuery` was designed to fetch only orders with status READY:

```python
async def handle_async(self, request: GetReadyOrdersQuery):
    ready_orders = await self.order_repository.get_ready_orders_async()
    # Only gets READY status orders
```

This worked for the management operations monitor (which shows available orders for assignment), but wasn't appropriate for the delivery driver view which needs to see both available orders and their current deliveries.

## Order Status Lifecycle and Responsibilities

### Complete Order Flow

1. **PENDING** → New order, awaiting kitchen confirmation
2. **CONFIRMED** → Acknowledged by kitchen, preparing to cook
3. **COOKING** → Actively being prepared by kitchen
4. **READY** → Finished cooking, waiting for driver pickup
5. **DELIVERING** → Out for delivery with assigned driver
6. **DELIVERED** → Successfully completed (terminal state)
7. **CANCELLED** → Order cancelled (terminal state)

### View Responsibilities

**Kitchen View** (`/kitchen`):

- Shows: PENDING, CONFIRMED, COOKING
- Purpose: Orders that require kitchen attention
- Fixed in: KITCHEN_VIEW_FILTER_FIX.md

**Delivery View** (`/delivery`):

- Shows: READY, DELIVERING
- Purpose: Orders available for pickup + orders currently being delivered
- Fixed in: This document

**Management View** (`/management`):

- Shows: All active orders (all except DELIVERED, CANCELLED)
- Purpose: Complete overview for managers

## Solution Implementation

### 1. Created New Query: GetDeliveryOrdersQuery

Created a new specialized query that fetches both READY and DELIVERING orders:

**File**: `application/queries/get_delivery_orders_query.py`

```python
@dataclass
class GetDeliveryOrdersQuery(Query[OperationResult[List[OrderDto]]]):
    """Query to fetch all orders relevant to delivery drivers (READY + DELIVERING)"""
    pass

class GetDeliveryOrdersHandler:
    async def handle_async(self, request: GetDeliveryOrdersQuery):
        # Get all active orders
        active_orders = await self.order_repository.get_active_orders_async()

        # Filter for delivery-relevant orders only
        delivery_orders = [
            order for order in active_orders
            if order.state.status.value in ["ready", "delivering"]
        ]

        # Sort by priority:
        # 1. DELIVERING orders first (by out_for_delivery_time)
        # 2. READY orders second (by actual_ready_time - FIFO)
        delivering_orders = [o for o in delivery_orders if o.state.status.value == "delivering"]
        ready_orders = [o for o in delivery_orders if o.state.status.value == "ready"]

        delivering_orders.sort(
            key=lambda o: getattr(o.state, "out_for_delivery_time", None) or datetime.min
        )
        ready_orders.sort(
            key=lambda o: o.state.actual_ready_time or o.state.order_time or datetime.min
        )

        # Combine: delivering first, then ready
        sorted_orders = delivering_orders + ready_orders

        # Build DTOs...
```

**Key Design Decisions:**

1. **Filtering at Query Level**: Business logic about "delivery-relevant" belongs in the query handler, not the repository
2. **Smart Sorting**: DELIVERING orders appear first (current deliveries take priority), then READY orders (FIFO for fairness)
3. **Reuses Repository**: Uses existing `get_active_orders_async()` method and applies filtering

### 2. Updated Delivery Controller

**File**: `ui/controllers/delivery_controller.py`

Changed from:

```python
from application.queries.get_ready_orders_query import GetReadyOrdersQuery

@get("/", response_class=HTMLResponse)
async def ready_orders(self, request: Request):
    query = GetReadyOrdersQuery()
    result = await self.mediator.execute_async(query)
```

To:

```python
from application.queries.get_delivery_orders_query import GetDeliveryOrdersQuery

@get("/", response_class=HTMLResponse)
async def ready_orders(self, request: Request):
    query = GetDeliveryOrdersQuery()
    result = await self.mediator.execute_async(query)
```

**SSE Stream Update**:

```python
async def event_generator():
    # Changed from GetReadyOrdersQuery to GetDeliveryOrdersQuery
    delivery_query = GetDeliveryOrdersQuery()
    delivery_result = await self.mediator.execute_async(delivery_query)

    delivery_orders = delivery_result.data if delivery_result.is_success else []

    delivery_data = [
        {
            "id": o.id,
            "status": o.status,  # Now includes both "ready" and "delivering"
            "customer_name": o.customer_name,
            "customer_address": o.customer_address,
            "pizza_count": o.pizza_count,
            "total_amount": float(o.total_amount) if o.total_amount else 0,
            "actual_ready_time": o.actual_ready_time.isoformat() if o.actual_ready_time else None,
        }
        for o in delivery_orders
    ]

    yield f"data: {json.dumps({'delivery_orders': delivery_data, 'tour_orders': tour_data})}\n\n"
```

### 3. Updated Delivery Template

**File**: `ui/templates/delivery/ready_orders.html`

Changed SSE data key from `ready_orders` to `delivery_orders`:

```javascript
eventSource.onmessage = function (event) {
  const data = JSON.parse(event.data);
  updateReadyOrders(data.delivery_orders); // Changed from ready_orders
};
```

### 4. Registered New Query

**File**: `application/queries/__init__.py`

Added import and export:

```python
from .get_delivery_orders_query import GetDeliveryOrdersQuery, GetDeliveryOrdersHandler

__all__ = [
    # ... existing exports ...
    "GetDeliveryOrdersQuery",
    "GetDeliveryOrdersHandler",
]
```

## Why Keep GetReadyOrdersQuery?

The original `GetReadyOrdersQuery` is still used by the management controller for the operations monitor. It serves a different purpose:

- **GetReadyOrdersQuery**: Shows READY orders available for assignment (management view)
- **GetDeliveryOrdersQuery**: Shows READY + DELIVERING orders for driver view

This separation of concerns allows each view to have exactly the data it needs.

## Testing Verification

### Test Scenario 1: READY Orders Visible

1. Log in as kitchen staff
2. Confirm and cook an order until READY
3. Switch to delivery driver view (`/delivery`)
4. **Verify**: Order appears in delivery view with READY status

### Test Scenario 2: DELIVERING Orders Visible

1. As delivery driver, pick up a READY order (assign to delivery)
2. Mark order as DELIVERING
3. Check delivery view
4. **Verify**: Order still appears but now shows DELIVERING status

### Test Scenario 3: Priority Sorting

1. Create multiple orders:
   - Order A: READY for 5 minutes
   - Order B: READY for 2 minutes
   - Order C: DELIVERING for 10 minutes
2. View delivery page
3. **Verify**:
   - Order C (DELIVERING) appears first
   - Order A (READY, oldest) appears second
   - Order B (READY, newer) appears third

### Test Scenario 4: Kitchen Orders Not in Delivery

1. Create new order (PENDING)
2. Confirm order (CONFIRMED)
3. Start cooking (COOKING)
4. Check delivery view
5. **Verify**: None of these orders appear in delivery view

### Test Scenario 5: SSE Updates Work

1. Open delivery view
2. In another session, mark an order as READY
3. **Verify**: Order appears in delivery view within 5 seconds
4. Assign order for delivery (DELIVERING)
5. **Verify**: Order updates to DELIVERING status in real-time

### Test Scenario 6: Management Still Works

1. Log in as manager
2. View operations monitor (`/management`)
3. **Verify**: GetReadyOrdersQuery still works correctly
4. **Verify**: Only READY orders appear (not DELIVERING)

## Design Rationale

### Why Create a New Query Instead of Modifying GetReadyOrdersQuery?

1. **Separation of Concerns**: Different views have different needs

   - Management needs: READY orders only (available for assignment)
   - Delivery needs: READY + DELIVERING (available + in-progress)

2. **Single Responsibility**: Each query serves one specific view's purpose

   - GetReadyOrdersQuery: "What orders are ready for assignment?"
   - GetDeliveryOrdersQuery: "What orders should delivery drivers see?"

3. **Backward Compatibility**: Existing management features continue to work

   - Operations monitor unchanged
   - No risk of breaking existing functionality

4. **Clear Intent**: Query names explicitly state their purpose
   - `GetReadyOrdersQuery` → Obviously fetches READY orders
   - `GetDeliveryOrdersQuery` → Obviously fetches delivery-relevant orders

### Why Filter at Query Level?

1. **Business Logic**: "Delivery-relevant" is a business concept, not a data concept
2. **Repository Reusability**: `get_active_orders_async()` remains generic
3. **Query Flexibility**: Each query can define its own filtering rules
4. **Testability**: Easy to unit test query-specific filtering logic

## Files Modified

1. **Created**: `application/queries/get_delivery_orders_query.py` (130 lines)

   - New query and handler for delivery-relevant orders

2. **Modified**: `ui/controllers/delivery_controller.py`

   - Changed import from GetReadyOrdersQuery to GetDeliveryOrdersQuery
   - Updated SSE stream to use GetDeliveryOrdersQuery
   - Changed data key from `ready_orders` to `delivery_orders`

3. **Modified**: `ui/templates/delivery/ready_orders.html`

   - Updated SSE message handler to use `delivery_orders` key

4. **Modified**: `application/queries/__init__.py`
   - Added GetDeliveryOrdersQuery and GetDeliveryOrdersHandler exports

## Related Documentation

- **KITCHEN_VIEW_FILTER_FIX.md**: Kitchen view filtering implementation
- **Order Lifecycle**: See domain/entities/enums.py for OrderStatus enum
- **Repository Pattern**: See integration/repositories/mongo_order_repository.py

## Future Considerations

### Potential Enhancements

1. **Driver-Specific Filtering**: Show only orders assigned to logged-in driver

   ```python
   @dataclass
   class GetDeliveryOrdersQuery(Query[OperationResult[List[OrderDto]]]):
       driver_id: Optional[str] = None  # Filter by driver if provided
   ```

2. **Distance-Based Sorting**: Sort READY orders by proximity to driver location

   ```python
   # Sort by distance from driver's current location
   ready_orders.sort(key=lambda o: calculate_distance(driver_location, o.customer_address))
   ```

3. **Time-Based Alerts**: Highlight orders ready for extended periods

   ```python
   # Add urgency flag for orders waiting > 10 minutes
   if (datetime.now() - order.actual_ready_time).total_seconds() > 600:
       order_dto.is_urgent = True
   ```

4. **Repository Method**: If this pattern is reused, consider adding:

   ```python
   async def get_delivery_orders_async(self) -> List[Order]:
       return await self.get_by_statuses_async([OrderStatus.READY, OrderStatus.DELIVERING])
   ```

## Summary

This fix ensures delivery drivers see both orders available for pickup (READY) and orders they're currently delivering (DELIVERING). By creating a specialized `GetDeliveryOrdersQuery`, we maintain clean separation of concerns while providing each view with exactly the data it needs.

The solution follows the framework's CQRS principles by:

- Creating a specific query for a specific view's needs
- Keeping business logic in the application layer (query handler)
- Maintaining repository genericity and reusability
- Using dependency injection and the mediator pattern

The delivery view now correctly displays all delivery-relevant orders with intelligent sorting (active deliveries first, then waiting orders in FIFO order).
