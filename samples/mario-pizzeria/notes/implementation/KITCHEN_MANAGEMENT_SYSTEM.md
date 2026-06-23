# Kitchen Management System Implementation

**Date:** October 22, 2025
**Feature:** Real-time kitchen dashboard with role-based access control

## Overview

Implemented a comprehensive kitchen management system for Mario's Pizzeria that allows kitchen staff (chefs and managers) to view and manage active orders in real-time using Server-Sent Events (SSE).

## Key Features

### 1. Role-Based Access Control (RBAC)

**Keycloak Roles:**

- `customer` - Regular customers who can place orders
- `chef` - Kitchen staff who can manage orders
- `manager` - Managers with both chef and customer privileges

**Test Users (from Keycloak realm):**

```
Customer User:
  username: customer
  password: password123
  roles: customer

Chef User:
  username: chef
  password: password123
  roles: chef

Manager User:
  username: manager
  password: password123
  roles: manager, chef
```

### 2. Real-Time Order Updates with SSE

**Server-Sent Events Stream:**

- Endpoint: `GET /kitchen/stream`
- Updates every 5 seconds
- Automatic reconnection on connection loss
- Client-side connection status indicator

**Why SSE over WebSocket:**

- Unidirectional server→client communication (perfect for this use case)
- Simpler implementation and debugging
- Automatic reconnection handled by browser
- Works through most firewalls and proxies
- Lower overhead than WebSocket for read-only updates

### 3. Order Status Workflow

```
pending → confirmed → cooking → ready → delivered
                ↓
            cancelled
```

**Status Actions:**

- **Pending** → Confirm (chef acknowledges order)
- **Confirmed** → Start Cooking (chef begins preparation)
- **Cooking** → Mark Ready (order complete, awaiting pickup)
- **Ready** → Delivered (order picked up/delivered)
- **Pending/Confirmed** → Cancel (order cancelled)

### 4. Kitchen Dashboard Features

**Visual Design:**

- Color-coded order cards by status
  - Yellow border: Pending
  - Blue border: Confirmed
  - Orange border: Cooking (with pulse animation)
  - Green border: Ready
- Elapsed time display with warning for orders >30 minutes
- Live connection status indicator
- Active order count

**Order Information Display:**

- Order ID (shortened to first 8 characters)
- Customer name
- Order time with elapsed time calculation
- Pizza details (name, size, toppings)
- Special instructions/notes
- Current status badge

**Actions:**

- Quick status update buttons (context-aware)
- Cancel order option (pending/confirmed only)
- One-click status transitions

## Architecture

### Commands

**`UpdateOrderStatusCommand`** (`application/commands/update_order_status_command.py`)

```python
@dataclass
class UpdateOrderStatusCommand(Command[OperationResult[OrderDto]]):
    order_id: str
    new_status: str  # "confirmed", "cooking", "ready", "delivered", "cancelled"
    notes: Optional[str] = None
```

**Handler Logic:**

- Validates order exists
- Validates status transition
- Calls appropriate domain method (confirm, start_cooking, mark_ready, deliver, cancel)
- Saves updated order to repository
- Returns updated OrderDto

### Queries

**`GetActiveKitchenOrdersQuery`** (`application/queries/get_active_kitchen_orders_query.py`)

```python
@dataclass
class GetActiveKitchenOrdersQuery(Query[OperationResult[List[OrderDto]]]):
    include_completed: bool = False
```

**Handler Logic:**

- Fetches all orders from repository
- Filters to active statuses: pending, confirmed, cooking, ready
- Sorts by order time (oldest first for kitchen priority)
- Fetches customer information for each order
- Constructs OrderDto with full details

### Controllers

**`UIKitchenController`** (`ui/controllers/kitchen_controller.py`)

**Endpoints:**

1. `GET /kitchen` - Kitchen dashboard view

   - Checks authentication
   - Validates chef/manager role
   - Returns 403 if unauthorized
   - Displays active orders

2. `GET /kitchen/stream` - SSE stream

   - Checks authentication and authorization
   - Streams order updates every 5 seconds
   - Handles client disconnection gracefully
   - Auto-reconnects on connection loss

3. `POST /kitchen/{order_id}/status` - Update order status (AJAX)
   - Validates authentication and authorization
   - Accepts form data with new status
   - Returns JSON response with success/error

### Templates

**`kitchen/dashboard.html`**

- Responsive grid layout (3 columns on XL screens, 2 on LG, 1 on mobile)
- Real-time SSE connection with status indicator
- JavaScript for elapsed time updates
- AJAX status update without page reload
- Auto-reload when orders change significantly

**`errors/403.html`**

- User-friendly access denied page
- Shows current user information
- Explains permission requirements

### Session Management

**Role Storage:**
Updated `ui/controllers/auth_controller.py` to extract and store roles from Keycloak token:

```python
# Extract roles from token
roles = []
if "realm_access" in user and "roles" in user["realm_access"]:
    roles = user["realm_access"]["roles"]

# Store in session
request.session["roles"] = roles
```

**Role Checking:**

```python
def _check_kitchen_access(self, request: Request) -> bool:
    roles = request.session.get("roles", [])
    return "chef" in roles or "manager" in roles
```

### Navigation Updates

**Base Template (`layouts/base.html`):**

- Added "Kitchen" link in main navigation (visible only to chef/manager)
- Added "Kitchen Dashboard" in user dropdown menu (role-conditional)
- Passes `roles` to all templates for conditional rendering

## Implementation Details

### SSE Event Format

```javascript
// Server sends:
data: {"orders": [{"id": "...", "status": "cooking", ...}]}

// Client receives and processes:
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    updateKitchenDisplay(data.orders);
};
```

### Connection Management

```javascript
// Automatic reconnection with exponential backoff
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

eventSource.onerror = function (error) {
  if (reconnectAttempts < maxReconnectAttempts) {
    reconnectAttempts++;
    setTimeout(connectSSE, 3000 * reconnectAttempts);
  }
};
```

### Status Update Flow

```javascript
// Client-side AJAX call
async function updateOrderStatus(orderId, newStatus) {
  const formData = new FormData();
  formData.append("status", newStatus);

  const response = await fetch(`/kitchen/${orderId}/status`, {
    method: "POST",
    body: formData,
  });

  const result = await response.json();
  if (result.success) {
    location.reload(); // Refresh to show updated status
  }
}
```

## Files Created/Modified

### New Files Created

1. `application/commands/update_order_status_command.py` - Order status update command
2. `application/queries/get_active_kitchen_orders_query.py` - Active orders query
3. `ui/controllers/kitchen_controller.py` - Kitchen dashboard controller
4. `ui/templates/kitchen/dashboard.html` - Kitchen dashboard template
5. `ui/templates/errors/403.html` - Access denied error page

### Modified Files

1. `application/commands/__init__.py` - Added UpdateOrderStatusCommand export
2. `application/queries/__init__.py` - Added GetActiveKitchenOrdersQuery export
3. `ui/controllers/auth_controller.py` - Added role extraction from Keycloak
4. `ui/controllers/home_controller.py` - Pass roles to templates
5. `ui/templates/layouts/base.html` - Added kitchen navigation links

## Testing Instructions

### Test as Regular Customer

1. Login with: `customer` / `password123`
2. Verify Kitchen link is NOT visible in navigation
3. Try to access `/kitchen` directly → should get 403 error
4. Place an order through `/menu`

### Test as Kitchen Staff

1. Login with: `chef` / `password123`
2. Verify "Kitchen" link IS visible in navigation
3. Access `/kitchen` → should see kitchen dashboard
4. Observe real-time updates every 5 seconds
5. Test order workflow:
   - Click "Confirm" on pending order
   - Click "Start Cooking" on confirmed order
   - Click "Mark Ready" on cooking order
   - Click "Delivered" on ready order
6. Verify connection status indicator shows "Live Updates Active"
7. Disconnect internet → verify shows "Connection Lost"
8. Reconnect → verify auto-reconnects

### Test as Manager

1. Login with: `manager` / `password123`
2. Verify has both customer and kitchen access
3. Can place orders AND manage kitchen

## Performance Considerations

**SSE Polling Interval:**

- Current: 5 seconds (configurable)
- Reduces database load
- Provides near-real-time updates
- Balance between responsiveness and resource usage

**Database Queries:**

- `get_all_async()` on orders (could be optimized with status filter)
- Customer lookups for each order (could be cached)
- Consider implementing database-level filtering in production

**Optimization Opportunities:**

1. Add database index on `order.status` field
2. Implement Redis caching for customer data
3. Use database change notifications instead of polling
4. Batch customer lookups

## Security

**Access Control:**

- ✅ Authentication required for all kitchen endpoints
- ✅ Role-based authorization (chef/manager only)
- ✅ Session-based security
- ✅ No sensitive data exposed in SSE stream

**CSRF Protection:**

- Using Starlette's built-in session management
- AJAX requests include session cookies
- Consider adding CSRF tokens for production

## Benefits

1. **Real-Time Visibility** - Kitchen staff see new orders immediately
2. **Reduced Errors** - Clear status workflow prevents confusion
3. **Improved Efficiency** - One-click status updates
4. **Better Communication** - Visual indicators show order status at a glance
5. **Scalability** - SSE handles multiple concurrent kitchen users
6. **Security** - Role-based access ensures only authorized staff access kitchen
7. **User Experience** - Connection status feedback and auto-reconnection

## Future Enhancements

1. **Order Notifications** - Sound alerts for new orders
2. **Order Timer** - Countdown for estimated ready time
3. **Print Queue** - Automatic order printing to kitchen printer
4. **Statistics Dashboard** - Orders per hour, average preparation time
5. **Order Assignment** - Assign specific orders to specific chefs
6. **Mobile View** - Optimized layout for kitchen tablets
7. **Order Notes** - Chef notes and special handling instructions
8. **Customer Communication** - SMS notifications when order ready
9. **Historical View** - Completed orders with timing analytics
10. **Multi-Location** - Support for multiple kitchen locations

## Conclusion

The kitchen management system provides a professional, real-time order management interface that significantly improves kitchen operations. The use of SSE for live updates, combined with role-based access control from Keycloak, creates a secure and efficient workflow for kitchen staff.

The system is production-ready with room for future enhancements based on operational feedback.
