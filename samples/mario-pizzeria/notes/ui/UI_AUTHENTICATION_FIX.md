# UI Authentication State Display Fix

**Date:** October 22, 2025
**Status:** ✅ Fixed
**Type:** Bug Fix

---

## Problem

After logging in through `/auth/login`, the UI was not showing the authenticated state:

- ❌ User dropdown menu not appearing
- ❌ "Guest" label still showing
- ❌ "Login" button still visible
- ❌ Protected links (My Orders, Profile) not appearing

**User reported:**

> "I can authenticate and login but the UI doesn't change at all."

---

## Root Cause

**Session Mismatch:**

The `UIAuthController` (login handler) was setting session variables:

```python
request.session["user_id"] = user_id
request.session["username"] = username_value
request.session["email"] = email
request.session["name"] = name or username_value
request.session["authenticated"] = True  # ✅ Setting authenticated flag
```

But the `HomeController` (home page renderer) was checking for a **different** variable:

```python
# ❌ WRONG: Checking for access_token (OAuth2 JWT)
access_token = request.session.get("access_token", None)
token_payload = None
if access_token:
    try:
        token_payload = jwt.decode(access_token, options={"verify_signature": False})
    except Exception as e:
        log.warning(f"Failed to decode access token: {e}")

# ❌ Passing token_payload existence instead of authenticated flag
return request.app.state.templates.TemplateResponse(
    "home/index.html",
    {
        "authenticated": token_payload is not None,  # ❌ Always False!
        "username": username,
    },
)
```

**The Issue:**

- Auth controller uses **session-based authentication** (for UI)
- Home controller was checking for **OAuth2 access_token** (for API)
- These are two different authentication mechanisms!

---

## Solution

Updated `HomeController.home_view()` to read from session variables set by auth controller:

```python
@get("/", response_class=HTMLResponse)
async def home_view(self, request: Request) -> Any:
    """
    Render the home page.

    Shows authenticated UI if user is logged in with session.
    """
    # Get session data ✅ Reading from session
    authenticated = request.session.get("authenticated", False)
    username = request.session.get("username", "Guest")
    name = request.session.get("name")
    email = request.session.get("email")

    try:
        return request.app.state.templates.TemplateResponse(
            "home/index.html",
            {
                "request": request,
                "title": "Home",
                "active_page": "home",
                "app_version": app_settings.app_version,
                "authenticated": authenticated,  # ✅ Correct variable
                "username": username,
                "name": name,  # ✅ Added
                "email": email,  # ✅ Added
            },
        )
```

---

## Authentication Architecture

The application uses **two separate authentication mechanisms**:

### 1. Session-Based Authentication (UI)

**Used by:** Browser-based UI (HTML templates)

**Flow:**

```
POST /auth/login (username + password)
    ↓
UIAuthController.login()
    ↓
AuthService.authenticate_user() → Keycloak token exchange
    ↓
Store in session:
  - user_id
  - username
  - email
  - name
  - authenticated = True ✅
    ↓
Redirect to homepage
    ↓
HomeController reads session.authenticated
    ↓
Template shows user dropdown menu
```

**Session Variables:**

- `authenticated`: `bool` - True if logged in
- `user_id`: `str` - Keycloak user ID (sub claim)
- `username`: `str` - Username or preferred_username
- `email`: `str` - User email
- `name`: `str` - Full name

### 2. OAuth2 Bearer Token Authentication (API)

**Used by:** REST API endpoints (Swagger UI, external clients)

**Flow:**

```
GET /api/profile/me
    ↓
Header: Authorization: Bearer <jwt_token>
    ↓
validate_token() dependency
    ↓
Verify JWT signature with Keycloak public key
    ↓
Extract claims from token
    ↓
Pass token dict to endpoint
```

**Token Claims:**

- `sub`: User ID
- `preferred_username`: Username
- `email`: Email
- `name`: Full name
- `realm_access.roles`: User roles

---

## Template Context Variables

All templates using `layouts/base.html` need these variables:

```python
{
    "request": request,               # FastAPI request object (required)
    "title": "Page Title",           # Browser title
    "active_page": "home",           # For nav highlighting
    "app_version": app_settings.app_version,  # Footer version

    # Authentication (for navbar)
    "authenticated": bool,            # True if logged in
    "username": str,                  # Username (fallback)
    "name": str | None,              # Full name (preferred)
    "email": str | None,             # Email address
}
```

### Template Usage (base.html)

```html
{% if authenticated %}
<!-- User Dropdown Menu -->
<div class="dropdown">
  <button class="btn btn-outline-light dropdown-toggle" ...>
    <i class="bi bi-person-circle me-2 fs-5"></i>
    <span>{{ name if name else username }}</span>
  </button>
  <ul class="dropdown-menu">
    <li>
      <div class="dropdown-header">
        <strong>{{ name if name else username }}</strong>
        {% if email %}
        <br /><small class="text-muted">{{ email }}</small>
        {% endif %}
      </div>
    </li>
    <li><a href="/profile">My Profile</a></li>
    <li><a href="/orders/history">Order History</a></li>
    <li><a href="/auth/logout">Logout</a></li>
  </ul>
</div>
{% else %}
<!-- Guest State -->
<span class="navbar-text">Guest</span>
<a href="/auth/login" class="btn btn-outline-light">Login</a>
{% endif %}
```

---

## Controllers Review

### ✅ UIAuthController (auth_controller.py)

**Status:** Correct - Sets session variables

```python
# Login handler
request.session["authenticated"] = True
request.session["user_id"] = user_id
request.session["username"] = username_value
request.session["email"] = email
request.session["name"] = name

# Logout handler
request.session.clear()
```

### ✅ HomeController (home_controller.py) - FIXED

**Before:**

```python
access_token = request.session.get("access_token", None)  # ❌ Wrong variable
authenticated = token_payload is not None  # ❌ Always False
```

**After:**

```python
authenticated = request.session.get("authenticated", False)  # ✅ Correct
username = request.session.get("username", "Guest")
name = request.session.get("name")
email = request.session.get("email")
```

### ✅ UIProfileController (profile_controller.py)

**Status:** Correct - Checks session.authenticated for access control

```python
if not request.session.get("authenticated"):
    return RedirectResponse(url="/auth/login?next=/profile", status_code=302)

# Passes to template
return templates.TemplateResponse({
    "authenticated": True,  # Always True (already checked)
    "username": request.session.get("username"),
    "name": request.session.get("name"),
    "email": request.session.get("email"),
})
```

### ✅ UIOrdersController (orders_controller.py)

**Status:** Correct - Checks session.authenticated for access control

```python
if not request.session.get("authenticated"):
    return RedirectResponse(url="/auth/login", status_code=302)

# Passes to template
return templates.TemplateResponse({
    "authenticated": True,
    "username": request.session.get("username"),
    ...
})
```

---

## Testing

### Manual Test Steps

1. **Start application:**

   ```bash
   make sample-mario-bg
   ```

2. **Visit homepage (unauthenticated):**

   ```
   Open: http://localhost:8080/
   Expected:
     - ✅ "Guest" label in navbar
     - ✅ "Login" button visible
     - ✅ No "My Orders" link
     - ✅ No user dropdown
   ```

3. **Login:**

   ```
   Click: Login button
   URL: http://localhost:8080/auth/login
   Enter: customer / password123
   Expected: Redirect to homepage
   ```

4. **Verify authenticated UI:**

   ```
   Expected:
     - ✅ User dropdown menu visible
     - ✅ Shows "Customer User" or username
     - ✅ Shows email in dropdown
     - ✅ "My Orders" link visible
     - ✅ Dropdown contains:
       - My Profile
       - Order History
       - Logout
   ```

5. **Logout:**

   ```
   Click: Logout in dropdown
   Expected: Redirect to homepage (guest state)
   ```

---

## Files Changed

### Modified

- ✅ `ui/controllers/home_controller.py`
  - Removed JWT token decoding logic
  - Changed to read `session.authenticated` flag
  - Pass `username`, `name`, `email` to template

### No Changes Needed

- ✅ `ui/controllers/auth_controller.py` - Already correct
- ✅ `ui/controllers/profile_controller.py` - Already correct
- ✅ `ui/controllers/orders_controller.py` - Already correct
- ✅ `ui/templates/layouts/base.html` - Already correct

---

## Related Issues

This fix resolves the UI authentication display but maintains the dual authentication system:

1. **Session-based auth for UI** - Uses cookies, server-side session
2. **OAuth2 Bearer tokens for API** - Uses JWT, stateless

Both are valid and serve different purposes:

- UI needs persistent sessions across page loads
- API needs stateless tokens for REST clients

---

## Summary

✅ **Fixed `HomeController` to read correct session variables**
✅ **UI now properly shows authenticated vs guest state**
✅ **Session variables now consistent across all UI controllers**
✅ **Documented dual authentication architecture**
✅ **All controllers reviewed for consistency**

**Status:** ✅ Fixed - Ready for Testing
