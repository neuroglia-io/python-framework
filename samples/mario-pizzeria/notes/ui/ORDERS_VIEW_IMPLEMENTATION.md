# Orders View Implementation

**Date:** October 22, 2025
**Status:** ✅ Complete
**Type:** Feature Implementation & Fix

---

## Overview

Fixed and enhanced the `/orders` view to properly display user order history after placing an order. The controller existed but needed proper routing configuration and the template needed field name updates to match the DTOs.

---

## Issues Fixed

### 1. Missing Routable Initialization

**Problem:** The UIOrdersController didn't initialize `Routable`, so routes weren't being registered.

**Solution:** Added proper Routable initialization with `/orders` prefix:

```python
class UIOrdersController(ControllerBase):
    def __init__(self, service_provider, mapper, mediator):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Orders"

        # Initialize Routable with /orders prefix
        Routable.__init__(
            self,
            prefix="/orders",
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )
```

### 2. Template Field Mismatch

**Problem:** Template referenced fields that didn't exist in OrderDto:

- `order.items` → should be `order.pizzas`
- `order.created_at` → should be `order.order_time`
- `order.delivery_address` → should be `order.customer_address`
- `order.special_instructions` → should be `order.notes`
- `order.order_number` → doesn't exist, use `order.id[:8]`
- `item.pizza_name` → should be `pizza.name`
- `item.unit_price` → should be `pizza.price`
- `item.quantity` → not applicable (each pizza is separate)

**Solution:** Updated template to match OrderDto and PizzaDto field names.

### 3. No Root Route

**Problem:** User gets redirected to `/orders` but no route handled the root path.

**Solution:** Added root route that displays orders directly:

```python
@get("/", response_class=HTMLResponse)
async def orders_root(self, request: Request):
    """Redirect /orders to /orders with query params preserved"""
    query_string = str(request.query_params)
    redirect_url = f"/orders?{query_string}" if query_string else "/orders"

    # If no query params, just show the history directly
    if not query_string:
        return await self.order_history(request)

    return RedirectResponse(url=redirect_url, status_code=302)
```

### 4. Success/Error Messages Not Displayed

**Problem:** Success messages from order creation weren't shown to user.

**Solution:** Extract success/error from query parameters and pass to template:

```python
# Get success/error messages from query params
success_message = request.query_params.get("success")
error_message = request.query_params.get("error")

# Pass to template
return request.app.state.templates.TemplateResponse(
    "orders/history.html",
    {
        "success": success_message,
        "error": error_message or query_error,
        # ... other context
    },
)
```

---

## Implementation

### Controller Updates

**File:** `ui/controllers/orders_controller.py`

**Key Changes:**

1. **Import Routable:**

   ```python
   from classy_fastapi import get, Routable
   from neuroglia.mvc.controller_base import generate_unique_id_function
   ```

2. **Initialize Routable in `__init__`:**

   ```python
   Routable.__init__(
       self,
       prefix="/orders",
       tags=["UI"],
       generate_unique_id_function=generate_unique_id_function,
   )
   ```

3. **Add root route:**

   ```python
   @get("/", response_class=HTMLResponse)
   async def orders_root(self, request: Request):
       # Handle /orders directly
   ```

4. **Update main route to handle query params:**

   ```python
   @get("", response_class=HTMLResponse)
   async def order_history(self, request: Request):
       success_message = request.query_params.get("success")
       error_message = request.query_params.get("error")
       # ... rest of logic
   ```

### Template Updates

**File:** `ui/templates/orders/history.html`

**Field Mappings:**

| Template (Old)               | Template (New)           | OrderDto Field     |
| ---------------------------- | ------------------------ | ------------------ |
| `order.order_number`         | `order.id[:8]`           | `id`               |
| `order.created_at`           | `order.order_time`       | `order_time`       |
| `order.delivery_address`     | `order.customer_address` | `customer_address` |
| `order.special_instructions` | `order.notes`            | `notes`            |
| `order.items`                | `order.pizzas`           | `pizzas`           |
| `item.pizza_name`            | `pizza.name`             | `name`             |
| `item.unit_price`            | `pizza.price`            | `price`            |
| `item.quantity`              | `1` (removed)            | -                  |

**Order Summary Updates:**

Removed fields that don't exist in OrderDto:

- ❌ `order.tax_amount`
- ❌ `order.delivery_fee`

Added fields from OrderDto:

- ✅ `order.pizza_count` - Number of pizzas in order
- ✅ `order.payment_method` - Payment method used

---

## User Flow

### After Order Placement

1. User submits order from `/menu`
2. Menu controller processes order via `PlaceOrderCommand`
3. On success, redirects to: `/orders?success=Order+created`
4. Orders controller extracts success message from query params
5. Template displays success alert at top of page
6. User sees their order history with the new order at the top

### Order Display

**Order Card Shows:**

- Order number (first 8 chars of order ID)
- Order time (formatted: "October 22, 2025 at 2:30 PM")
- Status badge (pending, preparing, ready, completed, cancelled)
- List of pizzas with names, sizes, toppings, and prices
- Delivery address
- Special instructions (if any)
- Total amount
- Number of pizzas
- Payment method

**Actions Available:**

- View Details button (for future detail page)
- Cancel button (if order is pending or preparing)
- Reorder button (if order is completed)

---

## Routes

| Route                 | Method | Handler                         | Description                                                 |
| --------------------- | ------ | ------------------------------- | ----------------------------------------------------------- |
| `/orders`             | GET    | `orders_root`                   | Shows order history directly or redirects with query params |
| `/orders/`            | GET    | `orders_root`                   | Same as above                                               |
| `/orders?success=...` | GET    | `orders_root` → `order_history` | Shows order history with success message                    |

---

## Template Features

### Success/Error Alerts

```html
{% if success %}
<div class="alert alert-success alert-dismissible fade show">
  <i class="bi bi-check-circle-fill"></i> Order details retrieved successfully.
  <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
{% endif %}
```

### Empty State

```html
{% if not orders or orders|length == 0 %}
<div class="card text-center">
  <i class="bi bi-cart-x" style="font-size: 4rem;"></i>
  <h3>No Orders Yet</h3>
  <p>You haven't placed any orders yet.</p>
  <a href="/menu" class="btn btn-primary">Browse Menu</a>
</div>
{% endif %}
```

### Order Cards

- Responsive layout with Bootstrap grid
- Status badges with appropriate colors
- Pizza list in table format
- Collapsible address and notes sections
- Action buttons in footer

---

## Testing

### Manual Test Steps

1. **Start application:**

   ```bash
   make sample-mario-bg
   ```

2. **Login:**

   - Visit http://localhost:8080/auth/login
   - Login as: customer / password123

3. **Place an order:**

   - Visit http://localhost:8080/menu
   - Add pizzas to cart
   - Fill out order form
   - Click "Place Order"

4. **Verify redirect:**

   - Should redirect to: `/orders?success=Order+created`
   - Success message should appear at top
   - Order should be visible in list

5. **Verify order display:**

   - ✅ Order number shown (e.g., "Order #abc123de")
   - ✅ Order time formatted correctly
   - ✅ Status badge shows "Pending"
   - ✅ All pizzas listed with correct details
   - ✅ Delivery address shown
   - ✅ Special instructions shown (if provided)
   - ✅ Total amount displayed
   - ✅ Payment method shown

6. **Direct navigation:**
   - Visit http://localhost:8080/orders
   - Should display order history (no redirect)

---

## Files Modified

### Updated

- ✅ `ui/controllers/orders_controller.py`

  - Added Routable initialization
  - Added root route handler
  - Added success/error query param handling
  - Updated template context

- ✅ `ui/templates/orders/history.html`
  - Updated field names to match OrderDto
  - Simplified order summary (removed tax/delivery fee)
  - Added payment method display
  - Fixed pizza iteration loop

---

## Related Queries & DTOs

### GetOrdersByCustomerQuery

**Purpose:** Retrieve all orders for a specific customer

**Input:** `customer_id` (string)

**Output:** `OperationResult[list[OrderDto]]`

### OrderDto Structure

```python
class OrderDto(BaseModel):
    id: str
    customer: Optional[CustomerDto] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    pizzas: list[PizzaDto] = []
    status: str
    order_time: datetime
    confirmed_time: Optional[datetime] = None
    cooking_started_time: Optional[datetime] = None
    actual_ready_time: Optional[datetime] = None
    estimated_ready_time: Optional[datetime] = None
    notes: Optional[str] = None
    total_amount: Decimal
    pizza_count: int
    payment_method: Optional[str] = None
```

### PizzaDto Structure

```python
class PizzaDto(BaseModel):
    id: str
    name: str
    size: str
    toppings: list[str] = []
    price: Decimal
```

---

## Future Enhancements

### Order Detail Page

- [ ] Implement `/orders/{order_id}` route
- [ ] Show detailed order information
- [ ] Order status timeline
- [ ] Estimated completion time

### Order Actions

- [ ] Implement `/orders/{order_id}/cancel` endpoint
- [ ] Implement `/orders/reorder/{order_id}` functionality
- [ ] Add order tracking (real-time updates)

### Pagination

- [ ] Add pagination for large order histories
- [ ] Implement filtering (by status, date range)
- [ ] Add sorting options

### JavaScript Enhancements

- [ ] Extract cancel confirmation to separate JS file
- [ ] Add real-time order status updates (WebSocket)
- [ ] Add order animations

---

## Summary

✅ **Routable initialization added** - Routes properly registered
✅ **Template field names fixed** - Matches OrderDto structure
✅ **Root route implemented** - `/orders` displays history directly
✅ **Success messages working** - Query params extracted and displayed
✅ **Order display complete** - All order details shown correctly
✅ **User flow fixed** - Order placement → Success message → Order list

**Result:** Users can now successfully view their order history after placing orders. The page displays all order details with proper field mapping and success notifications.
