# Customer Name Issue: "Demo User" Appearing in Orders

## Problem Description

When a manager (or any authenticated user) creates an order:

1. **Kitchen displays "Demo User"** instead of the actual manager's name
2. **Order doesn't appear in the manager's order history**

Example: Order #2c2de85c shows "Demo User" as the customer in the kitchen view.

## Root Cause Analysis

### Issue 1: Demo User Fallback in Authentication

**File:** `application/services/auth_service.py` (lines 76-87)

```python
# Fallback to demo user for development
if username == "demo" and password == "demo123":
    return {
        "id": "demo-user-id",
        "sub": "demo-user-id",
        "username": "demo",
        "preferred_username": "demo",
        "email": "demo@mariospizzeria.com",
        "name": "Demo User",  # ← THIS IS THE PROBLEM
        "role": "customer",
    }
```

**Problem:** If Keycloak authentication fails or the user uses the demo login, the session gets "Demo User" as the name. This then propagates through the entire order creation workflow.

### Issue 2: Customer Profile Creation Chain

When an authenticated user accesses the menu:

1. **Menu Controller** (`ui/controllers/menu_controller.py` lines 52-56):

   ```python
   profile_query = GetOrCreateCustomerProfileQuery(
       user_id=str(user_id),
       email=email,  # From session
       name=name     # From session - might be "Demo User"!
   )
   ```

2. **Profile Query** creates/updates customer with session name:

   ```python
   # Scenario 3: Create new profile
   name = request.name or "User"  # Uses "Demo User" from session!
   ```

3. **Order Creation** uses customer profile data:

   ```python
   # PlaceOrderCommand gets customer info from form
   command = PlaceOrderCommand(
       customer_name=customer_name,  # From form, pre-filled with "Demo User"
       customer_phone=customer_phone,
       ...
   )
   ```

4. **Customer lookup/creation** (`place_order_command.py` lines 140-162):

   ```python
   # Try to find existing customer by phone
   existing_customer = await self.customer_repository.get_by_phone_async(request.customer_phone)

   if existing_customer:
       return existing_customer  # Returns customer with "Demo User" name
   else:
       # Create new customer with "Demo User" name
       customer = Customer(
           name=request.customer_name,  # "Demo User" from form
           ...
       )
   ```

5. **OrderDto creation** copies customer name:

   ```python
   order_dto = OrderDto(
       id=order.id(),
       customer_name=customer.state.name,  # "Demo User"!
       ...
   )
   ```

6. **Kitchen displays** the OrderDto customer_name:
   ```html
   <i class="bi bi-person"></i> {{ order.customer_name }}
   ```

### Issue 3: Order History Not Showing Orders

**Problem:** Orders are linked to customers by `customer_id`, but the order history query might be looking for orders by a different customer ID.

**Scenario:**

- Manager logs in with Keycloak user_id: "keycloak-manager-123"
- But orders might be created with customer_id from a different customer record
- Order history queries by user_id → customer_id mapping, but if this mapping is wrong, orders don't show up

## The Complete Flow (Current - BROKEN)

```
┌─────────────────────┐
│ User Logs In        │
│ Keycloak fails      │
│ Falls back to demo  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Session:            │
│ name = "Demo User"  │ ← WRONG!
│ user_id = "demo-..."│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Access Menu         │
│ GetOrCreateProfile  │
│ name="Demo User"    │ ← WRONG!
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Form Pre-filled:    │
│ customer_name=      │
│  "Demo User"        │ ← WRONG!
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Submit Order        │
│ PlaceOrderCommand   │
│ customer_name=      │
│  "Demo User"        │ ← WRONG!
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Create/Get Customer │
│ by phone            │
│ name="Demo User"    │ ← WRONG!
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Order Created       │
│ customer_name=      │
│  "Demo User"        │ ← WRONG!
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Kitchen Displays:   │
│ "Demo User"         │ ← DISPLAYED WRONG!
└─────────────────────┘
```

## Solutions

### Solution 1: Remove Demo User Fallback (Recommended)

**Rationale:** If Keycloak is properly configured, there's no need for a demo fallback. If it's not configured, the application should fail loudly rather than silently falling back to incorrect data.

**Change:** `application/services/auth_service.py`

```python
async def authenticate_async(self, username: str, password: str) -> Optional[dict[str, Any]]:
    """Authenticate user with Keycloak only (no fallback)"""
    # Try Keycloak authentication
    keycloak_user = await self._authenticate_with_keycloak(username, password)
    if keycloak_user:
        return keycloak_user

    # NO FALLBACK - authentication failed
    return None
```

### Solution 2: Use Keycloak User Info Directly (Recommended)

**Rationale:** Don't allow form fields to override authenticated user information. The logged-in user IS the customer.

**Change:** `ui/controllers/menu_controller.py`

```python
@post("/order", response_class=HTMLResponse)
async def create_order_from_menu(self, request: Request, ...):
    """Create order from menu selection"""

    # Get authenticated user info from session
    user_id = request.session.get("user_id")
    user_name = request.session.get("name")  # Keycloak name
    user_email = request.session.get("email")  # Keycloak email

    # Get or create customer profile for this user
    profile_query = GetOrCreateCustomerProfileQuery(
        user_id=str(user_id),
        email=user_email,
        name=user_name
    )
    profile_result = await self.mediator.execute_async(profile_query)

    if not profile_result.is_success:
        return RedirectResponse(url="/menu?error=Profile+error", status_code=303)

    customer_profile = profile_result.data

    # Use profile data for order (NOT form fields for name/email)
    command = PlaceOrderCommand(
        customer_name=customer_profile.name,      # From profile, not form
        customer_phone=customer_phone,            # Still from form (can change per order)
        customer_address=customer_address,        # Still from form (can change per order)
        customer_email=customer_profile.email,    # From profile, not form
        pizzas=pizzas,
        payment_method=payment_method,
        notes=notes,
    )
```

### Solution 3: Link Orders to user_id Not Just customer_id

**Rationale:** Orders should be queryable by the authenticated user's ID, not just by phone number lookups.

**Changes Needed:**

1. **Add user_id to Order entity** (optional field for backward compatibility)
2. **Update PlaceOrderCommand** to accept user_id
3. **Update order history query** to find orders by user_id OR customer_id

**Example:**

```python
# In PlaceOrderCommandHandler
async def handle_async(self, request: PlaceOrderCommand) -> OperationResult[OrderDto]:
    # Get customer
    customer = await self._create_or_get_customer(request)

    # Create order WITH user_id link
    order = Order(customer_id=customer.id())
    if hasattr(request, 'user_id') and request.user_id:
        order.state.user_id = request.user_id  # Link to authenticated user

    # ... rest of order creation
```

### Solution 4: Pre-fill Form from Keycloak, Not Customer Profile (Safeguard)

**Rationale:** Even if customer profile has wrong data, the form should show correct Keycloak data.

**Change:** `ui/templates/menu/index.html`

```html
<!-- Use Keycloak name as primary source -->
<input
  type="text"
  class="form-control"
  id="customer_name"
  name="customer_name"
  value="{{ name or (customer_profile.name if customer_profile else 'Guest') }}"
  required
/>
```

## Recommended Fix Priority

1. **HIGH:** Remove demo user fallback (Solution 1)
2. **HIGH:** Use Keycloak user info directly for orders (Solution 2)
3. **MEDIUM:** Link orders to user_id (Solution 3)
4. **LOW:** Update form pre-fill logic (Solution 4) - becomes unnecessary if Solution 2 is implemented

## Implementation Plan

### Step 1: Remove Demo User Fallback

```python
# application/services/auth_service.py
async def authenticate_async(self, username: str, password: str) -> Optional[dict[str, Any]]:
    """Authenticate user with Keycloak"""
    return await self._authenticate_with_keycloak(username, password)
    # Removed demo fallback
```

### Step 2: Update Menu Order Creation

Make authenticated user's info non-editable for name/email:

1. Remove name and email from order form
2. Use session data directly in controller
3. Only allow phone and address to be edited per-order

### Step 3: Test

1. Log in as manager with Keycloak
2. Create order from menu
3. Verify kitchen shows manager's actual name
4. Verify order appears in manager's order history

## Testing Checklist

- [ ] Manager logs in with Keycloak
- [ ] Manager's name appears correctly in session
- [ ] Menu form pre-fills with manager's name
- [ ] Order is created with manager's name
- [ ] Kitchen displays manager's name (not "Demo User")
- [ ] Order appears in manager's order history
- [ ] Customer profile is correctly linked to user_id
- [ ] No "Demo User" fallback occurs

## Migration Considerations

If there are existing orders with "Demo User":

1. **Find affected orders:**

   ```python
   orders = await order_repository.find_by_customer_name_async("Demo User")
   ```

2. **Options:**
   - Leave historical orders as-is (they're already completed)
   - Manual data cleanup if needed
   - Add migration script to link orders to actual users if possible

## Related Files

- `application/services/auth_service.py` - Authentication logic
- `ui/controllers/menu_controller.py` - Order creation from menu
- `application/commands/place_order_command.py` - Order placement logic
- `application/queries/get_or_create_customer_profile_query.py` - Profile creation
- `ui/templates/menu/index.html` - Order form template
- `ui/templates/kitchen/dashboard.html` - Kitchen order display
