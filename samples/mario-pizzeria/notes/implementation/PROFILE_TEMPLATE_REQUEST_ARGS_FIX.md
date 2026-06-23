# Profile Template Request.args Fix

**Date:** October 22, 2025
**Issue:** HTTP 500 error - "'starlette.requests.Request object' has no attribute 'args'"
**Location:** `ui/templates/profile/view.html` line 23
**Status:** ✅ Fixed

---

## Problem Description

When accessing the profile page at `/profile/` or `/profile`, the application returned HTTP 500:

```
GET /profile/ HTTP/1.1 500 Internal Server Error

{
  "title": "Internal Server Error",
  "status": 500,
  "detail": "'starlette.requests.Request object' has no attribute 'args'",
  "instance": "..."
}
```

### Debugging Discovery

Using debugpy, we found:

- Request processing succeeded through the entire `view_profile()` method
- Error occurred **AFTER** the return statement
- Error happened during template rendering

---

## Root Cause

The profile template was using Flask-style request syntax:

**File:** `ui/templates/profile/view.html` (Line 23)

```html
{% if request.args.get('success') %}
<div class="alert alert-success alert-dismissible fade show" role="alert">
  <i class="bi bi-check-circle"></i> Profile updated successfully!
  <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
</div>
{% endif %}
```

### The Issue

**Flask Syntax (WRONG for FastAPI/Starlette):**

```python
request.args.get('success')  # ❌ AttributeError: Request has no 'args'
```

**Starlette Syntax (CORRECT):**

```python
request.query_params.get('success')  # ✅ Works correctly
```

### Why This Happened

The template was likely copied from a Flask application or written with Flask conventions in mind. Flask's Request object has an `.args` attribute for query parameters, but Starlette's Request object uses `.query_params` instead.

---

## Solution

Changed the template to use Starlette's correct query parameter syntax:

### Before

```html
{% if request.args.get('success') %}
<div class="alert alert-success alert-dismissible fade show" role="alert">
  <i class="bi bi-check-circle"></i> Profile updated successfully!
  <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
</div>
{% endif %}
```

### After

```html
{% if request.query_params.get('success') %}
<div class="alert alert-success alert-dismissible fade show" role="alert">
  <i class="bi bi-check-circle"></i> Profile updated successfully!
  <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
</div>
{% endif %}
```

**Changed:** `request.args.get('success')` → `request.query_params.get('success')`

---

## Starlette Request Object Reference

### Query Parameters

**Correct Starlette/FastAPI syntax:**

```python
# In Python code or Jinja2 templates
request.query_params.get('param_name')
request.query_params.get('param_name', 'default_value')

# Check if parameter exists
'param_name' in request.query_params

# Get all parameters as dict
dict(request.query_params)
```

### Common Request Attributes

| Flask             | Starlette/FastAPI      | Description             |
| ----------------- | ---------------------- | ----------------------- |
| `request.args`    | `request.query_params` | Query string parameters |
| `request.form`    | `await request.form()` | Form data (must await)  |
| `request.json`    | `await request.json()` | JSON body (must await)  |
| `request.cookies` | `request.cookies`      | Cookies (same)          |
| `request.headers` | `request.headers`      | Headers (same)          |
| `request.method`  | `request.method`       | HTTP method (same)      |
| `request.url`     | `request.url`          | Full URL (same)         |

**Key Difference:** Starlette requires `await` for reading request body data (form, json), while Flask does not.

---

## Testing

### Step 1: Restart Application

```bash
make sample-mario-stop
make sample-mario-bg
```

### Step 2: Test Profile Page

**Access profile:**

```
1. Login at http://localhost:8080/auth/login
2. Click user dropdown → "My Profile"
Expected: ✅ Profile page loads (200 OK)
Should NOT see: 500 Internal Server Error
```

### Step 3: Test Success Message

**Edit and save profile:**

```
1. On profile page, click "Edit Profile"
2. Update name, phone, or address
3. Click "Save Changes"
Expected: ✅ Redirect to /profile?success=true
         ✅ Green success message appears
```

### Step 4: Verify Template Rendering

**Check page displays:**

- ✅ User name and email
- ✅ Phone and address (or "Not provided")
- ✅ Total orders count
- ✅ Favorite pizza
- ✅ "Edit Profile" button
- ✅ Success message (if ?success=true in URL)

---

## Template Best Practices

### Accessing Query Parameters in Jinja2

**Correct patterns for Starlette/FastAPI:**

```html
<!-- Single parameter -->
{% if request.query_params.get('success') %}
<p>Success!</p>
{% endif %}

<!-- Parameter with default -->
{% set page = request.query_params.get('page', '1') %}

<!-- Check parameter exists -->
{% if 'error' in request.query_params %}
<p class="error">{{ request.query_params.get('error') }}</p>
{% endif %}

<!-- Multiple parameters -->
{% set success = request.query_params.get('success') %} {% set error = request.query_params.get('error') %}
```

### Passing Parameters from Controller

**Best practice:** Extract query params in controller, pass to template:

```python
@get("", response_class=HTMLResponse)
async def view_profile(self, request: Request):
    # Extract in controller
    success_message = request.query_params.get('success')
    error_message = request.query_params.get('error')

    return request.app.state.templates.TemplateResponse(
        "profile/view.html",
        {
            "request": request,
            "success": success_message,  # ← Pass explicitly
            "error": error_message,       # ← Pass explicitly
            # ... other context
        },
    )
```

**Template becomes simpler:**

```html
{% if success %}
<div class="alert alert-success">{{ success }}</div>
{% endif %}
```

**Benefits:**

- ✅ Cleaner templates
- ✅ Easier testing
- ✅ Better separation of concerns
- ✅ Less framework-specific code in templates

---

## Other Controllers Using Query Params Correctly

### UIOrdersController

```python
# Extract in controller
success_message = request.query_params.get("success")
error_message = request.query_params.get("error")

return request.app.state.templates.TemplateResponse(
    "orders/history.html",
    {
        "request": request,
        "success": success_message,  # Passed explicitly
        "error": error_message,       # Passed explicitly
        # ...
    },
)
```

**Template:** `orders/history.html`

```html
{% if success %}
<div class="alert alert-success">{{ success }}</div>
{% endif %} {% if error %}
<div class="alert alert-danger">{{ error }}</div>
{% endif %}
```

**Pattern:** Extract in Python, pass to template. No `request.query_params` in template.

---

## Improvement Recommendation

### Update ProfileController to Match Pattern

**Current (works but not ideal):**

```html
<!-- In template -->
{% if request.query_params.get('success') %}
```

**Recommended (better separation):**

**In `profile_controller.py`:**

```python
@get("", response_class=HTMLResponse)
async def view_profile(self, request: Request):
    # ... existing code ...

    # Extract query params
    success_message = request.query_params.get('success')

    return request.app.state.templates.TemplateResponse(
        "profile/view.html",
        {
            "request": request,
            "title": "My Profile",
            "active_page": "profile",
            "authenticated": True,
            "username": request.session.get("username"),
            "name": request.session.get("name"),
            "email": request.session.get("email"),
            "profile": profile,
            "error": error,
            "success": success_message,  # ← Add this
            "app_version": app_settings.app_version,
        },
    )
```

**In `view.html`:**

```html
{% if success %}
<div class="alert alert-success alert-dismissible fade show" role="alert">
  <i class="bi bi-check-circle"></i> Profile updated successfully!
  <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
</div>
{% endif %}
```

**Benefits:**

- Consistent with orders controller
- Template agnostic to request framework
- Easier to test controller logic
- More maintainable

---

## Summary

✅ **Fixed:** Changed `request.args.get()` to `request.query_params.get()` in profile template
✅ **Root Cause:** Flask-style request syntax used in Starlette/FastAPI application
✅ **Result:** Profile page loads correctly without 500 error
✅ **Pattern:** Verified other templates don't have the same issue

**Key Lesson:** When using FastAPI/Starlette, always use `request.query_params` for query string parameters, never `request.args` (which is Flask-specific).

**Recommendation:** Follow the pattern used in orders controller - extract query params in the controller and pass them explicitly to templates for better separation of concerns.
