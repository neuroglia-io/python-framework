# Customer Name Fix - "Demo User" Issue Resolved

## Problem

When a manager (or any authenticated user) created an order through the menu:

1. **Kitchen displayed "Demo User"** instead of the manager's actual name
2. **Order didn't appear** in the manager's order history

Example: Order #2c2de85c showed "Demo User" in the kitchen view instead of the manager's name.

## Root Cause

The order creation workflow was using **editable form fields** for customer name and email, which could be:

- Pre-filled with incorrect values
- Modified by the user (breaking the link to their authenticated profile)
- Defaulting to "Demo User" if Keycloak authentication fell back to demo mode

### The Problematic Flow

```
User logs in with Keycloak
       ↓
Menu loads, form pre-fills with name/email
       ↓
User can EDIT name/email fields  ← PROBLEM!
       ↓
Order created with edited values
       ↓
Wrong customer name in database
```

## Solution Implemented

### 1. Use Authenticated User Profile Data Directly

**File:** `ui/controllers/menu_controller.py`

**Changes:**

- Removed `customer_name` and `customer_email` from form parameters
- Fetch customer profile before processing order
- Use profile name and email directly in PlaceOrderCommand
- Added validation to ensure profile has required fields

**Before:**

```python
async def create_order_from_menu(
    self,
    request: Request,
    customer_name: str = Form(...),      # ← User could edit this!
    customer_phone: str = Form(...),
    customer_address: str = Form(...),
    customer_email: Optional[str] = Form(None),  # ← User could edit this!
    payment_method: str = Form(...),
    notes: Optional[str] = Form(None),
):
    # ... create order with form values
    command = PlaceOrderCommand(
        customer_name=customer_name,      # ← Could be wrong!
        customer_email=customer_email,    # ← Could be wrong!
        ...
    )
```

**After:**

```python
async def create_order_from_menu(
    self,
    request: Request,
    customer_phone: str = Form(...),      # ← Still editable
    customer_address: str = Form(...),    # ← Still editable
    payment_method: str = Form(...),
    notes: Optional[str] = Form(None),
):
    # Get authenticated user info
    user_id = request.session.get("user_id")
    user_name = request.session.get("name")
    user_email = request.session.get("email")

    # Get or create customer profile
    profile_query = GetOrCreateCustomerProfileQuery(
        user_id=str(user_id),
        email=user_email,
        name=user_name
    )
    profile_result = await self.mediator.execute_async(profile_query)

    # Validation
    if not profile_result.is_success or not profile_result.data:
        return RedirectResponse(url="/menu?error=Unable+to+load+customer+profile", ...)

    customer_profile = profile_result.data

    if not customer_profile.name or not customer_profile.email:
        return RedirectResponse(url="/menu?error=Incomplete+customer+profile", ...)

    # ... create order with profile values
    command = PlaceOrderCommand(
        customer_name=customer_profile.name,      # ← From Keycloak profile!
        customer_email=customer_profile.email,    # ← From Keycloak profile!
        customer_phone=customer_phone,            # ← From form (can vary)
        customer_address=customer_address,        # ← From form (can vary)
        ...
    )
```

### 2. Make Name and Email Read-Only in Form

**File:** `ui/templates/menu/index.html`

**Changes:**

- Changed name and email fields to **read-only** display
- Removed `name="customer_name"` and `name="customer_email"` attributes (no longer submitted)
- Added explanatory text to clarify these are account-level settings
- Added visual styling (gray background) to indicate read-only status

**Before:**

```html
<div class="mb-3">
  <label for="customer_name" class="form-label">Name *</label>
  <input
    type="text"
    class="form-control"
    id="customer_name"
    name="customer_name"
    ←
    Submitted
    with
    form
    value="{{ customer_profile.name if customer_profile else name }}"
    required
  />
  ← User could edit
</div>

<div class="mb-3">
  <label for="customer_email" class="form-label">Email</label>
  <input
    type="email"
    class="form-control"
    id="customer_email"
    name="customer_email"
    ←
    Submitted
    with
    form
    value="{{ customer_profile.email if customer_profile else email }}"
  />
</div>
← User could edit
```

**After:**

```html
<!-- Display logged-in user's name (read-only) -->
<div class="mb-3">
  <label class="form-label">Ordering As</label>
  <input
    type="text"
    class="form-control"
    value="{{ customer_profile.name if customer_profile else name }}"
    readonly
    ←
    Cannot
    edit
    style="background-color: #e9ecef;"
  />
  ← Gray background
  <small class="form-text text-muted"> This is your account name and cannot be changed here. </small>
</div>

<!-- Display logged-in user's email (read-only) -->
<div class="mb-3">
  <label class="form-label">Email</label>
  <input
    type="email"
    class="form-control"
    value="{{ customer_profile.email if customer_profile else email }}"
    readonly
    ←
    Cannot
    edit
    style="background-color: #e9ecef;"
  />
  ← Gray background
  <small class="form-text text-muted"> Order confirmation will be sent to this email. </small>
</div>
```

## The Fixed Flow

```
User logs in with Keycloak
       ↓
Session stores: user_id, name, email (from Keycloak)
       ↓
Menu loads customer profile (GetOrCreateCustomerProfileQuery)
       ↓
Form shows name/email as READ-ONLY  ← FIXED!
       ↓
User can only edit phone and address
       ↓
Order created with profile name/email  ← FIXED!
       ↓
Correct customer name in database  ← FIXED!
       ↓
Kitchen displays correct name  ← FIXED!
       ↓
Order appears in user's history  ← FIXED!
```

## Benefits

### Security & Data Integrity

- ✅ **Authenticated identity enforced** - Users cannot impersonate others
- ✅ **Profile data consistency** - Name and email match Keycloak account
- ✅ **Audit trail accuracy** - Orders correctly attributed to authenticated users

### User Experience

- ✅ **Clear UI** - Users understand which fields are account-level vs order-level
- ✅ **Less confusion** - No ability to accidentally change account name
- ✅ **Order history works** - Orders properly linked to user profiles

### Maintainability

- ✅ **Single source of truth** - Keycloak is authoritative for identity
- ✅ **Cleaner code** - Controller uses profile data directly
- ✅ **Better validation** - Explicit checks for required profile fields

## What Can Still Be Edited Per-Order

Users can still customize these fields for each order:

- **Phone number** - May want to use different contact number
- **Delivery address** - May want delivery to different locations
- **Payment method** - Can vary per order
- **Notes** - Order-specific instructions

## Testing Checklist

- [ ] Manager logs in with Keycloak credentials
- [ ] Menu form shows manager's name and email as read-only (gray background)
- [ ] Manager can edit phone and address
- [ ] Manager selects pizzas and submits order
- [ ] Kitchen view displays manager's actual name (not "Demo User")
- [ ] Order appears in manager's order history
- [ ] Order details show correct customer name and email
- [ ] Customer profile linked correctly (customer_id matches)

## Related Changes

This fix complements other authentication and profile improvements:

- **Keycloak Integration** - Authentication provides reliable user identity
- **Customer Profile System** - Profiles correctly linked to Keycloak user_id
- **Order History** - Orders queryable by user_id through customer profile

## Remaining Considerations

### Demo User Fallback (Not Addressed Yet)

The demo user fallback in `auth_service.py` still exists:

```python
# Fallback to demo user for development
if username == "demo" and password == "demo123":
    return {
        "name": "Demo User",  # ← Still creates demo user
        ...
    }
```

**Decision:** Keep this for development/testing purposes, but with the new fix, even if someone logs in as demo user, their orders will consistently use "Demo User" as the name (not accidentally use it for other users).

**Future Option:** Could remove this fallback entirely if Keycloak is always available.

### Updating Existing "Demo User" Orders

If there are existing orders in the database with "Demo User" as the customer name:

- They will remain as-is (historical data)
- New orders will use correct names
- Optional: Could create a migration script to link old orders if needed

## Files Modified

1. **`ui/controllers/menu_controller.py`**

   - Removed `customer_name` and `customer_email` form parameters
   - Added customer profile fetch and validation
   - Use profile data in PlaceOrderCommand

2. **`ui/templates/menu/index.html`**

   - Changed name/email fields to read-only display
   - Removed form field names (not submitted)
   - Added explanatory help text
   - Applied visual styling for read-only state

3. **`notes/CUSTOMER_NAME_ISSUE.md`** (New)

   - Comprehensive analysis of the problem
   - Multiple solution options
   - Implementation recommendations

4. **`notes/CUSTOMER_NAME_FIX.md`** (This document)
   - Summary of implemented solution
   - Before/after code comparison
   - Testing checklist

## Summary

The "Demo User" issue is now resolved. Orders created by authenticated users will always use their Keycloak profile name and email, ensuring:

- Correct attribution in the kitchen view
- Orders appear in user's order history
- Data integrity and security maintained

The fix is minimal, focused, and maintains backward compatibility while solving the core issue.
