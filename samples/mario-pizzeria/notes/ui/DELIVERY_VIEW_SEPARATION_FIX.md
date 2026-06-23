# Delivery View Separation Fix

## Issue Identified

The `/delivery/` view was incorrectly showing orders in **both** READY and DELIVERING statuses, which created confusion:

1. **Conceptual Issue**: Orders "Out for Delivery" shouldn't appear in the pickup view
2. **Data Corruption**: Orders had status="delivering" but `delivery_person_id=null`
3. **Wrong Query**: Used `GetDeliveryOrdersQuery` which returns both READY and DELIVERING

## Root Cause

### Data Corruption Discovered

```bash
curl http://localhost:8080/api/orders/3d0e65f5-5b6b-4b22-a988-dfb21632a539
```

**Result:**

```json
{
  "status": "delivering",
  "delivery_person_id": null,      ← WRONG! No driver assigned
  "out_for_delivery_time": null    ← WRONG! No delivery time
}
```

These orders were marked as "delivering" without going through proper assignment workflow:

- Missing `delivery_person_id`
- Missing `out_for_delivery_time`
- Invalid state transition

### Wrong Query Usage

**Before:**

```python
# ui/controllers/delivery_controller.py - ready_orders() method
query = GetDeliveryOrdersQuery()  # Returns READY + DELIVERING
```

This query was designed to return orders in multiple states, but the `/delivery/` view should only show unassigned READY orders.

## Correct View Separation

### `/delivery/` - Ready Orders View

**Purpose:** Show orders ready for pickup (not yet assigned to any driver)

**Should Display:**

- ✅ Orders with status = "READY"
- ✅ Orders cooked and waiting for pickup
- ✅ Action: "Add to My Tour" button

**Should NOT Display:**

- ❌ Orders already assigned to drivers
- ❌ Orders out for delivery
- ❌ Orders being delivered by other drivers

### `/delivery/tour` - My Delivery Tour View

**Purpose:** Show orders assigned to the current driver

**Should Display:**

- ✅ Orders with status = "DELIVERING"
- ✅ Orders with `delivery_person_id` = current user
- ✅ Only THIS driver's assigned orders
- ✅ Action: "Mark as Delivered" button

**Should NOT Display:**

- ❌ Unassigned READY orders
- ❌ Orders assigned to other drivers

## Solution Implemented

### 1. Fixed Controller to Use Correct Query

**File:** `ui/controllers/delivery_controller.py`

**Before (WRONG):**

```python
@get("/", response_class=HTMLResponse)
async def ready_orders(self, request: Request):
    """Display orders ready for delivery"""
    # Get delivery orders (READY + DELIVERING)
    query = GetDeliveryOrdersQuery()  # ← Returns both statuses
    result = await self.mediator.execute_async(query)
```

**After (CORRECT):**

```python
@get("/", response_class=HTMLResponse)
async def ready_orders(self, request: Request):
    """Display orders ready for delivery pickup (READY status only)"""
    # Get ONLY ready orders (not yet assigned to any driver)
    query = GetOrdersByStatusQuery(status="ready")  # ← Only READY
    result = await self.mediator.execute_async(query)
```

### 2. Updated Import

**Changed:**

```python
# OLD
from application.queries.get_delivery_orders_query import GetDeliveryOrdersQuery

# NEW
from application.queries.get_orders_by_status_query import GetOrdersByStatusQuery
```

### 3. Simplified Template

**File:** `ui/templates/delivery/ready_orders.html`

Removed conditional status checks since we now ONLY show READY orders:

**Before:**

```html
{% if order.status == 'ready' %}
<span class="ready-badge">Ready</span>
<button>Add to My Tour</button>
{% elif order.status == 'delivering' %}
<span class="badge bg-primary">Out for Delivery</span>
<button disabled>Already in Delivery</button>
{% endif %}
```

**After:**

```html
<span class="ready-badge">Ready</span> <button>Add to My Tour</button>
```

All orders shown are READY, so no conditionals needed.

## Query Usage Summary

### GetOrdersByStatusQuery(status="ready")

**Used by:** `/delivery/` (ready orders view)
**Returns:** Orders with status = "READY" only
**Purpose:** Show unassigned orders waiting for pickup

### GetDeliveryTourQuery(delivery_person_id=user_id)

**Used by:** `/delivery/tour` (my tour view)
**Returns:** Orders with status = "DELIVERING" AND assigned to specific driver
**Purpose:** Show THIS driver's active deliveries

### GetDeliveryOrdersQuery()

**Used by:** (Should be deprecated or renamed)
**Returns:** Orders with status in ["READY", "DELIVERING"]
**Purpose:** Original design was flawed - mixed two different views

## Data Integrity Issue

The corrupted orders (status="delivering" without driver assignment) indicate one of these problems:

1. **Direct Status Update**: Someone used `UpdateOrderStatusCommand` to change status without proper workflow
2. **Failed Assignment**: Assignment started but didn't complete
3. **Event Replay Issue**: Events applied out of order during development

### How Assignment SHOULD Work:

```python
# Correct flow
order = await repository.get_async(order_id)
order.assign_to_delivery(driver_id)      # Sets delivery_person_id
order.mark_out_for_delivery()            # Sets status to DELIVERING + timestamp
await repository.update_async(order)      # Persists both fields
```

### How It Probably Went Wrong:

```python
# Wrong - direct status change
command = UpdateOrderStatusCommand(
    order_id=order_id,
    new_status="delivering"  # ← Changes status but not driver assignment!
)
```

## Testing the Fix

### Test 1: Verify /delivery/ Shows Only READY Orders

```bash
# Navigate to delivery view
open http://localhost:8000/delivery/

# Should see ONLY orders with green "Ready" badge
# Should NOT see any "Out for Delivery" badges
# All orders should have "Add to My Tour" button
```

### Test 2: Verify Order Assignment Works

```bash
# 1. Click "Add to My Tour" on a READY order
# 2. Order should disappear from /delivery/ view
# 3. Order should appear in /delivery/tour view
# 4. Order should show driver name/ID
```

### Test 3: Check API Consistency

```bash
# Get ready orders via API
curl "http://localhost:8080/api/delivery/ready" | jq '.[].status'
# All should return: "ready"

# Check tour orders
curl "http://localhost:8000/delivery/tour"
# Should show orders with delivery_person_id set
```

## Workflow Diagram

```
┌─────────────┐
│ Kitchen     │
│ marks order │
│ as READY    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ /delivery/          │ ← Driver sees order here
│ "Ready Orders"      │
│                     │
│ [Add to My Tour]    │
└──────┬──────────────┘
       │ Click button
       ▼
┌─────────────────────┐
│ Assignment happens: │
│ - delivery_person_id│
│ - status→DELIVERING │
│ - out_for_deliv time│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ /delivery/tour      │ ← Order now appears here
│ "My Delivery Tour"  │
│                     │
│ [Mark as Delivered] │
└─────────────────────┘
```

## Updated Files

1. **`ui/controllers/delivery_controller.py`**

   - Changed query from `GetDeliveryOrdersQuery` to `GetOrdersByStatusQuery(status="ready")`
   - Updated docstring to clarify "READY status only"
   - Updated import statement

2. **`ui/templates/delivery/ready_orders.html`**
   - Removed conditional status checks
   - Simplified to assume all orders are READY
   - Removed "Out for Delivery" badge rendering

## Migration Note

The corrupted orders (status="delivering" without driver) should be fixed:

**Option 1: Reset to READY**

```bash
# For each corrupted order
curl -X PUT "http://localhost:8080/api/orders/{order_id}/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "ready"}'
```

**Option 2: Properly Assign Them**

```bash
# Assign to a driver (if you know who should deliver)
curl -X POST "http://localhost:8080/api/delivery/{order_id}/assign" \
  -H "Content-Type: application/json" \
  -d '{"delivery_person_id": "driver-123"}'
```

## Summary

✅ **Fixed view separation**: `/delivery/` now shows ONLY READY orders
✅ **Correct query usage**: Using `GetOrdersByStatusQuery` instead of mixed query
✅ **Simplified template**: Removed unnecessary conditionals
✅ **Clear responsibility**: Each view has distinct purpose
✅ **Better UX**: Drivers see clear separation between available and assigned orders

The `/delivery/` view is now consistent with its purpose: showing orders ready for pickup assignment, not orders already out for delivery.
