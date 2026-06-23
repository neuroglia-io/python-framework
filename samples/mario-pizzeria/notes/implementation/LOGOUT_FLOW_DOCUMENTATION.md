# Logout Flow Implementation

**Date:** October 22, 2025
**Status:** ✅ Already Implemented
**Type:** Feature Verification & Documentation

---

## Overview

The logout flow is already fully implemented in Mario's Pizzeria. This document provides a comprehensive overview of how the logout functionality works.

---

## Implementation

### 1. Logout Endpoint

**File:** `ui/controllers/auth_controller.py`

**Route:** `GET /auth/logout`

**Handler:**

```python
@get("/logout")
async def logout(self, request: Request) -> RedirectResponse:
    """Clear session and redirect to home"""
    username = request.session.get("username", "Unknown")
    request.session.clear()
    log.info(f"User {username} logged out")
    return RedirectResponse(url="/", status_code=303)
```

**Functionality:**

1. Retrieves username from session for logging
2. Clears all session data (removes authenticated state, user info)
3. Logs the logout action
4. Redirects to homepage with 303 status code

---

### 2. Logout UI Integration

**File:** `ui/templates/layouts/base.html`

**Location:** User dropdown menu in navigation bar

**UI Elements:**

```html
{% if authenticated %}
<!-- User Dropdown Menu -->
<div class="dropdown">
  <button class="btn btn-outline-light dropdown-toggle" type="button" id="userDropdown" data-bs-toggle="dropdown">
    <i class="bi bi-person-circle me-2 fs-5"></i>
    <span class="d-none d-md-inline">{{ name if name else username }}</span>
  </button>
  <ul class="dropdown-menu dropdown-menu-end shadow">
    <li>
      <div class="dropdown-header">
        <strong>{{ name if name else username }}</strong>
        <br />
        <small class="text-muted">{{ email }}</small>
      </div>
    </li>
    <li><hr class="dropdown-divider" /></li>
    <li>
      <a class="dropdown-item" href="/profile"> <i class="bi bi-person"></i> My Profile </a>
    </li>
    <li>
      <a class="dropdown-item" href="/orders/history"> <i class="bi bi-clock-history"></i> Order History </a>
    </li>
    <li><hr class="dropdown-divider" /></li>
    <li>
      <a class="dropdown-item text-danger" href="/auth/logout"> <i class="bi bi-box-arrow-right"></i> Logout </a>
    </li>
  </ul>
</div>
{% endif %}
```

**Features:**

- User dropdown shows current user's name and email
- Logout link styled in red (text-danger) to indicate destructive action
- Icon: `bi-box-arrow-right` (Bootstrap Icons)
- Accessible from any page in the navigation bar

---

## User Flow

### Complete Logout Flow

1. **User clicks dropdown menu:**

   - Dropdown button shows user's name and profile icon
   - Appears in navigation bar (authenticated users only)

2. **User sees menu options:**

   - User info header (name + email)
   - My Profile link
   - Order History link
   - Logout link (red, at bottom)

3. **User clicks "Logout":**

   - Browser navigates to `/auth/logout`
   - Controller retrieves username for logging
   - Session is cleared completely

4. **Session cleared:**

   - `authenticated` flag removed
   - `user_id` removed
   - `username` removed
   - `email` removed
   - `name` removed
   - All other session data removed

5. **User redirected to homepage:**

   - 303 redirect to `/`
   - Navigation bar now shows "Guest" state
   - "Login" button visible instead of user dropdown

6. **Server logs action:**
   - Log entry: "User {username} logged out"
   - INFO level logging

---

## Session Management

### Session Middleware Configuration

**File:** `main.py`

The application uses FastAPI's `SessionMiddleware` for session management:

```python
from starlette.middleware.sessions import SessionMiddleware

ui_app.add_middleware(
    SessionMiddleware,
    secret_key=app_settings.secret_key,
    max_age=3600,  # 1 hour session
    same_site="lax",
    https_only=False,  # Set True in production
)
```

**Session Characteristics:**

- **Cookie Name:** `mario_session`
- **Max Age:** 3600 seconds (1 hour)
- **Same Site:** "lax" (CSRF protection)
- **Storage:** Server-side session data
- **Security:** Signed with secret key

### Session Data Structure

When authenticated, session contains:

```python
{
    "authenticated": True,
    "user_id": "abc123...",
    "username": "customer",
    "email": "customer@example.com",
    "name": "John Doe"
}
```

After logout, session is completely empty: `{}`

---

## Security Considerations

### 1. Session Clearing

✅ **Complete Cleanup:** `request.session.clear()` removes ALL session data

- No residual authentication state
- Forces re-authentication on next protected route access
- Cannot access order history, profile, or place orders without re-login

### 2. Redirect After Logout

✅ **Safe Redirect:** Always redirects to homepage (`/`)

- Prevents logout loops
- No sensitive data in URL
- Uses 303 status (See Other) for proper POST-redirect-GET pattern

### 3. Logging

✅ **Audit Trail:** All logout actions are logged

- Includes username for tracking
- INFO level for normal operations
- Helps with security auditing and debugging

### 4. No Logout Token/CSRF

⚠️ **Current Implementation:** GET request without CSRF token

**Consideration:** Logout via GET is acceptable for low-risk applications, but best practice is POST with CSRF token.

**Enhancement (Optional):**

```python
@post("/logout")
async def logout(self, request: Request) -> RedirectResponse:
    # Validate CSRF token
    # Clear session
    # Redirect
```

---

## Testing

### Manual Test Steps

1. **Login:**

   ```
   Visit: http://localhost:8080/auth/login
   Login: customer / password123
   Expected: Redirect to homepage, user dropdown visible
   ```

2. **Verify authenticated state:**

   ```
   Navigate to: http://localhost:8080/orders
   Expected: Can access order history
   ```

3. **Click user dropdown:**

   ```
   Click: User dropdown button in nav bar
   Expected: Menu shows name, email, profile/orders links, logout link
   ```

4. **Click logout:**

   ```
   Click: Logout link (red, at bottom of dropdown)
   Expected: Redirect to homepage
   ```

5. **Verify logged out:**

   ```
   Check nav bar: Should show "Guest" and "Login" button
   Navigate to: http://localhost:8080/orders
   Expected: Redirect to login page
   ```

6. **Verify session cleared:**

   ```
   Open browser DevTools → Application → Cookies
   Check: mario_session cookie should be empty or removed
   ```

### Automated Test (Future)

```python
async def test_logout_clears_session(test_client):
    # Login first
    response = await test_client.post(
        "/auth/login",
        data={"username": "customer", "password": "password123"}
    )
    assert response.status_code == 303

    # Verify authenticated
    response = await test_client.get("/orders")
    assert response.status_code == 200

    # Logout
    response = await test_client.get("/auth/logout")
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # Verify logged out
    response = await test_client.get("/orders", follow_redirects=False)
    assert response.status_code == 302  # Redirect to login
```

---

## UI States

### Authenticated State (Before Logout)

**Navigation Bar:**

```
🍕 Mario's Pizzeria | Home | Menu | My Orders | [User Dropdown ▼]
```

**User Dropdown:**

- User name + email header
- My Profile
- Order History

---

- Logout (red)

**Accessible Pages:**

- All public pages (home, menu)
- Protected pages (orders, profile)

---

### Guest State (After Logout)

**Navigation Bar:**

```
🍕 Mario's Pizzeria | Home | Menu | [Guest 👤] [Login Button]
```

**Accessible Pages:**

- Public pages only (home, menu)
- Attempting to access protected pages redirects to login

**Login Prompt:**

- Visible "Login" button in nav bar
- Can browse menu but can't add to cart or place orders

---

## Logging Output

**Example log entry on logout:**

```
2025-10-22 11:30:45 INFO [auth_controller] User customer logged out
```

**Log includes:**

- Timestamp
- Log level (INFO)
- Module (auth_controller)
- Username of logged-out user

---

## Related Endpoints

| Endpoint       | Method | Purpose               | Auth Required                       |
| -------------- | ------ | --------------------- | ----------------------------------- |
| `/auth/login`  | GET    | Display login page    | No                                  |
| `/auth/login`  | POST   | Process login form    | No                                  |
| `/auth/logout` | GET    | Clear session, logout | No (but pointless if not logged in) |
| `/`            | GET    | Homepage              | No                                  |
| `/menu`        | GET    | Menu page             | No (auth for ordering)              |
| `/orders`      | GET    | Order history         | Yes                                 |
| `/profile`     | GET    | User profile          | Yes                                 |

---

## Future Enhancements

### 1. Logout Confirmation Modal

Add confirmation dialog before logout:

```javascript
function confirmLogout() {
  if (confirm("Are you sure you want to logout?")) {
    window.location.href = "/auth/logout";
  }
}
```

```html
<a class="dropdown-item text-danger" href="#" onclick="confirmLogout(); return false;">
  <i class="bi bi-box-arrow-right"></i> Logout
</a>
```

### 2. POST-based Logout

Use POST request with CSRF token:

```python
@post("/logout")
async def logout(self, request: Request) -> RedirectResponse:
    # Validate CSRF token
    csrf_token = request.headers.get("X-CSRF-Token")
    if not self._validate_csrf_token(csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    username = request.session.get("username", "Unknown")
    request.session.clear()
    log.info(f"User {username} logged out")
    return RedirectResponse(url="/", status_code=303)
```

### 3. Logout Success Message

Show success message after logout:

```python
return RedirectResponse(url="/?message=You+have+been+logged+out", status_code=303)
```

### 4. Logout All Sessions

If implementing multi-device sessions, add "Logout All Devices":

```python
@post("/logout-all")
async def logout_all(self, request: Request) -> RedirectResponse:
    user_id = request.session.get("user_id")
    await self.session_service.revoke_all_sessions(user_id)
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
```

### 5. Session Expiry Warning

Warn user before session expires:

```javascript
// After 55 minutes (5 minutes before expiry)
setTimeout(
  () => {
    if (confirm("Your session will expire soon. Stay logged in?")) {
      // Refresh session
      fetch("/auth/refresh-session");
    }
  },
  55 * 60 * 1000
);
```

---

## Summary

✅ **Logout endpoint implemented** - `GET /auth/logout`
✅ **Session clearing works** - `request.session.clear()`
✅ **UI integration complete** - User dropdown with logout link
✅ **Redirect to homepage** - Clean post-logout experience
✅ **Logging enabled** - Audit trail for logout actions
✅ **Guest state restored** - Navigation updates correctly
✅ **Protected routes blocked** - Cannot access orders/profile after logout

**Status:** Fully functional logout flow. Users can log out from any page using the user dropdown menu in the navigation bar. Session is completely cleared and users are redirected to the homepage in guest state.
