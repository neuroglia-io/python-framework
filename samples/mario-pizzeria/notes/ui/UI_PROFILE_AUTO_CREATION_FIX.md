# UI Profile Auto-Creation Fix

**Date:** October 22, 2025
**Issue:** Profile not found error after successful order placement
**Status:** ✅ Fixed

---

## Problem Description

Users could login and place orders successfully, but when redirected to the orders page, they received:

```
Order details retrieved successfully.
Profile not found. Please create a profile first.
```

### Root Cause

The UI controllers were using `GetCustomerProfileByUserIdQuery` which only **retrieves** existing profiles but doesn't **create** them automatically. This caused a race condition:

1. ✅ User logs in via Keycloak (session created)
2. ✅ User visits menu page (no profile needed to view)
3. ✅ User places order (order created successfully)
4. ❌ User redirected to orders page → Profile lookup fails!

### Why Orders Were Created Successfully

The `PlaceOrderCommand` doesn't require a CustomerProfile entity - it accepts customer information directly:

```python
@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    customer_name: str
    customer_phone: str
    customer_address: str
    customer_email: Optional[str]
    pizzas: List[CreatePizzaDto]
    payment_method: str
    notes: Optional[str] = None
```

However, the **orders view** needs the CustomerProfile to:

1. Get the `customer_id` to query orders
2. Display profile information in the UI

---

## Solution

Replace `GetCustomerProfileByUserIdQuery` with `GetOrCreateCustomerProfileQuery` in both UI controllers.

This ensures profiles are **automatically created** when:

- User first visits the menu page (profile ready for order form)
- User visits orders page after login (profile exists for order lookup)

### Key Benefits

1. **No Manual Profile Creation Required** - Profiles auto-create from session data
2. **Consistent with API Behavior** - API already uses GetOrCreateCustomerProfileQuery
3. **Better User Experience** - No "create profile first" errors
4. **Handles SSO Migration** - Auto-links existing email-based profiles to user_id

---

## Code Changes

### 1. Orders Controller

**File:** `ui/controllers/orders_controller.py`

**Before:**

```python
from application.queries import GetOrdersByCustomerQuery, GetCustomerProfileByUserIdQuery

# ...

# Get customer profile to get customer_id
profile_query = GetCustomerProfileByUserIdQuery(user_id=str(user_id))
profile_result = await self.mediator.execute_async(profile_query)
```

**After:**

```python
from application.queries import GetOrdersByCustomerQuery, GetOrCreateCustomerProfileQuery

# ...

# Get or create customer profile (auto-creates if doesn't exist)
profile_query = GetOrCreateCustomerProfileQuery(
    user_id=str(user_id),
    email=request.session.get("email"),
    name=request.session.get("name")
)
profile_result = await self.mediator.execute_async(profile_query)
```

**Key Changes:**

- ✅ Import `GetOrCreateCustomerProfileQuery` instead of `GetCustomerProfileByUserIdQuery`
- ✅ Pass `email` and `name` from session for profile creation
- ✅ Profile auto-created if doesn't exist
- ✅ Profile linked if exists by email without user_id

---

### 2. Menu Controller

**File:** `ui/controllers/menu_controller.py`

**Before:**

```python
from application.queries import GetMenuQuery, GetCustomerProfileByUserIdQuery

# ...

# Get customer profile if authenticated (for pre-filling order form)
customer_profile = None
if authenticated and user_id:
    profile_query = GetCustomerProfileByUserIdQuery(user_id=str(user_id))
    profile_result = await self.mediator.execute_async(profile_query)
    customer_profile = profile_result.data if profile_result.is_success else None
```

**After:**

```python
from application.queries import GetMenuQuery, GetOrCreateCustomerProfileQuery

# ...

# Get customer profile if authenticated (for pre-filling order form)
# Uses GetOrCreateCustomerProfileQuery to auto-create profile if doesn't exist
customer_profile = None
if authenticated and user_id:
    profile_query = GetOrCreateCustomerProfileQuery(
        user_id=str(user_id),
        email=email,
        name=name
    )
    profile_result = await self.mediator.execute_async(profile_query)
    customer_profile = profile_result.data if profile_result.is_success else None
```

**Key Changes:**

- ✅ Import `GetOrCreateCustomerProfileQuery` instead of `GetCustomerProfileByUserIdQuery`
- ✅ Pass `email` and `name` from session for profile creation
- ✅ Profile auto-created when user first visits menu
- ✅ Order form pre-filled from newly created profile

---

## Flow After Fix

### Complete User Journey

1. **User Logs In**

   ```
   POST /auth/login
   → Keycloak authentication
   → Session created with: user_id, email, name, username
   → Redirect to homepage
   ```

2. **User Visits Menu**

   ```
   GET /menu
   → GetOrCreateCustomerProfileQuery(user_id, email, name)
   → Profile created automatically from session data
   → Order form pre-filled with profile info
   ```

3. **User Places Order**

   ```
   POST /menu/order
   → PlaceOrderCommand with customer info + pizzas
   → Order created successfully
   → Redirect to /orders?success=Order+created
   ```

4. **User Views Orders** ✅ **NOW WORKS**

   ```
   GET /orders
   → GetOrCreateCustomerProfileQuery(user_id, email, name)
   → Profile found (created in step 2)
   → GetOrdersByCustomerQuery(customer_id)
   → Orders displayed successfully
   ```

---

## Profile Auto-Creation Logic

The `GetOrCreateCustomerProfileHandler` implements intelligent profile management:

### Scenario 1: Profile Exists by user_id (Fast Path)

```python
# Check if profile exists by user_id
existing = await self.customer_repository.get_by_user_id_async(query.user_id)
if existing:
    return self.ok(self.mapper.map(existing, CustomerProfileDto))
```

**Result:** Returns existing profile immediately

---

### Scenario 2: Profile Exists by Email (Migration Path)

```python
# Check if profile exists by email (pre-SSO customer)
if query.email:
    existing_by_email = await self.customer_repository.get_by_email_async(query.email)
    if existing_by_email:
        # Link existing profile to user_id
        existing_by_email.user_id = query.user_id
        await self.customer_repository.update_async(existing_by_email)
        return self.ok(self.mapper.map(existing_by_email, CustomerProfileDto))
```

**Result:** Links pre-existing email-based profile to Keycloak user_id

---

### Scenario 3: No Profile Exists (Creation Path)

```python
# Create new profile from token claims
command = CreateCustomerProfileCommand(
    user_id=query.user_id,
    email=query.email,
    name=query.name,
    phone="",  # Can be updated later
    address=""  # Can be updated later
)
result = await self.mediator.send_async(command)
return result
```

**Result:** Creates new profile with user info from session/token

---

## Session Data Requirements

For profile auto-creation to work, the session must contain:

```python
{
    "authenticated": True,        # Auth flag
    "user_id": "abc123...",       # Keycloak user ID (required)
    "email": "user@example.com",  # Email from token claims (required)
    "name": "John Doe",           # Full name from token claims (optional)
    "username": "johndoe"         # Username (for display)
}
```

### Where Session Data Comes From

**File:** `ui/controllers/auth_controller.py`

```python
@post("/login", response_class=HTMLResponse)
async def login(self, request: Request, username: str = Form(...), password: str = Form(...)):
    # ... Keycloak authentication ...

    # Extract user info from token claims
    access_token = token_response.get("access_token")
    decoded = self._decode_token(access_token)

    user_id = decoded.get("sub")  # Keycloak user ID
    email = decoded.get("email")
    name = decoded.get("name") or decoded.get("preferred_username")

    # Store in session
    request.session["authenticated"] = True
    request.session["user_id"] = user_id
    request.session["username"] = username
    request.session["email"] = email
    request.session["name"] = name
```

---

## Testing

### Manual Test Steps

1. **Clear existing profiles** (if testing fresh):

   ```bash
   # Connect to MongoDB
   mongo mario_pizzeria

   # Remove all profiles
   db.customer_profiles.deleteMany({})
   ```

2. **Login as new user:**

   ```
   Visit: http://localhost:8080/auth/login
   Username: customer
   Password: password123
   ```

3. **Visit menu page:**

   ```
   Navigate to: http://localhost:8080/menu
   Expected: Menu displays, order form pre-filled
   Check: Profile created in MongoDB
   ```

4. **Place order:**

   ```
   Add pizzas to cart
   Submit order
   Expected: Success message, redirect to orders
   ```

5. **View orders page:** ✅ **NOW WORKS**

   ```
   Should see: Order history with placed order
   Should NOT see: "Profile not found" error
   ```

### Verify Profile Creation

```bash
# Check MongoDB for created profile
mongo mario_pizzeria

db.customer_profiles.find({}).pretty()

# Should see profile with:
# - user_id: Keycloak user ID
# - email: From token claims
# - name: From token claims
```

---

## Error Handling

### If Profile Creation Fails

The handlers gracefully handle failures:

```python
if not profile_result.is_success or not profile_result.data:
    return request.app.state.templates.TemplateResponse(
        "orders/history.html",
        {
            "error": "Profile not found. Please create a profile first.",
            "orders": [],
            # ... other context
        }
    )
```

**Possible Causes:**

- Database connection failure
- Invalid session data (missing user_id)
- Repository errors

**User Experience:**

- Error message displayed
- Empty orders list
- Can still navigate app

---

## Related Documentation

- **CQRS Profile Refactoring:** `notes/CQRS_PROFILE_REFACTORING.md`
- **GetOrCreateCustomerProfileQuery:** `application/queries/get_or_create_customer_profile_query.py`
- **GetOrCreateCustomerProfileHandler:** `application/handlers/get_or_create_customer_profile_handler.py`

---

## Future Enhancements

### 1. Profile Validation

Add validation for required fields:

```python
if not query.email:
    return self.bad_request("Email is required for profile creation")
```

### 2. Profile Update on Login

Update profile info on each login:

```python
if existing:
    # Update profile with latest token info
    if query.email and existing.email != query.email:
        existing.email = query.email
    if query.name and existing.name != query.name:
        existing.name = query.name
    await self.customer_repository.update_async(existing)
```

### 3. Background Profile Sync

Sync profile data from Keycloak periodically:

```python
@scheduled_task(cron="0 0 * * *")  # Daily at midnight
async def sync_profiles_from_keycloak():
    # Fetch user info from Keycloak API
    # Update profiles in database
    pass
```

---

## Summary

✅ **Fixed:** Profile auto-creation now works in UI controllers
✅ **Consistency:** UI and API both use GetOrCreateCustomerProfileQuery
✅ **User Experience:** No manual profile creation required
✅ **Migration Support:** Handles email-based profile linking
✅ **Robustness:** Graceful error handling if creation fails

**Impact:** Users can now seamlessly login → place orders → view order history without encountering "profile not found" errors.
