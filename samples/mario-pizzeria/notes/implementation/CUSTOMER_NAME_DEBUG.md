# Customer Name Issue - Debugging & Root Cause

## Current Status

The fix has been applied but the issue persists. Order 60e91dad still shows "Demo User" instead of the manager's name.

## Root Cause Analysis - Deeper Investigation

After implementing the fix to use `customer_profile.name` instead of form fields, the issue persists. This indicates the problem is **upstream** from where I fixed it.

### The Real Problem Chain

```
1. Login → Session gets name="Demo User"
         ↓
2. GetOrCreateCustomerProfileQuery(name="Demo User")
         ↓
3. Customer profile created with name="Demo User"
         ↓
4. Order uses customer_profile.name = "Demo User"
         ↓
5. Kitchen displays "Demo User"
```

The issue is at **step 1** - the session is getting "Demo User" as the name in the first place!

## Why This Happens

### Scenario 1: Manager Uses Demo Credentials

If the manager logs in with `username="demo"` and `password="demo123"`, the auth fallback kicks in:

```python
# application/services/auth_service.py
if username == "demo" and password == "demo123":
    return {
        "name": "Demo User",  # ← This gets stored in session!
        ...
    }
```

### Scenario 2: Keycloak Token Missing `name` Claim

Even if logging in with proper Keycloak credentials (`manager`/`password123`), the Keycloak token might not include a `name` claim.

Keycloak token structure:

```json
{
  "sub": "user-id-123",
  "preferred_username": "manager",
  "email": "manager@mario-pizzeria.com",
  "given_name": "Mario", // ← firstName
  "family_name": "Manager", // ← lastName
  "name": "Mario Manager" // ← This might be MISSING!
}
```

If `name` is missing, the code falls back:

```python
name = decoded_token.get("name") or decoded_token.get("preferred_username")
# Results in: name = "manager" (username, not full name!)
```

## The Session Problem

Once a user logs in, their session persists until:

1. They log out
2. Session expires
3. Browser is closed (depending on config)

**If order 60e91dad was created with an existing session**, it would use the old session data even after code changes!

## Debug Logging Added

I've added debug logging to help diagnose:

```python
# In menu_controller.py create_order_from_menu()
log.info(f"🔍 Order creation - Session data: user_id={user_id}, name={user_name}, email={user_email}")
log.info(f"🔍 Order creation - Using customer_profile: name={customer_profile.name}, email={customer_profile.email}")
```

## Testing Instructions

### Step 1: Check Login Credentials

**Question for User:** How is the manager logging in?

**Option A: Demo Credentials**

- Username: `demo`
- Password: `demo123`
- Result: Will always show "Demo User"
- **Solution:** Use proper Keycloak credentials instead

**Option B: Keycloak Credentials**

- Username: `manager`
- Password: `password123`
- Result: Should work, but need to verify Keycloak token includes `name` claim

### Step 2: Fresh Login Test

**IMPORTANT:** You must log out and log back in for the fix to work!

1. **Log out completely** from the application
2. Clear browser session/cookies (or use incognito mode)
3. **Log in with Keycloak credentials:**
   - Username: `manager`
   - Password: `password123`
4. Go to menu and create a new order
5. Check the logs for the debug output
6. Check the kitchen view for the customer name

### Step 3: Check Application Logs

After creating a test order, check the logs:

```bash
docker logs mario-pizzeria-mario-pizzeria-app-1 --tail 50 | grep "🔍 Order creation"
```

This will show:

- What name was in the session
- What name the customer profile has
- This tells us where the "Demo User" is coming from

### Step 4: Check Keycloak Token

To verify what Keycloak is returning, check the auth logs:

```bash
docker logs mario-pizzeria-mario-pizzeria-app-1 --tail 100 | grep -A 5 "Keycloak user object"
```

This shows what user info Keycloak is providing.

## Potential Solutions

### Solution 1: Ensure Manager Uses Keycloak Login

If the manager is using `demo`/`demo123`, they need to use `manager`/`password123` instead.

### Solution 2: Fix Keycloak Token to Include `name` Claim

If Keycloak isn't including the `name` claim, we need to construct it:

```python
# In auth_service.py _authenticate_with_keycloak()
user_info = {
    "id": decoded_token.get("sub"),
    "sub": decoded_token.get("sub"),
    "username": decoded_token.get("preferred_username"),
    "preferred_username": decoded_token.get("preferred_username"),
    "email": decoded_token.get("email"),

    # IMPROVED: Build full name from first + last name if 'name' is missing
    "name": (
        decoded_token.get("name") or
        f"{decoded_token.get('given_name', '')} {decoded_token.get('family_name', '')}".strip() or
        decoded_token.get("preferred_username")
    ),

    "given_name": decoded_token.get("given_name"),
    "family_name": decoded_token.get("family_name"),
    "roles": decoded_token.get("realm_access", {}).get("roles", []),
}
```

### Solution 3: Remove Demo Fallback (Optional)

To prevent accidental use of demo credentials:

```python
# Remove this fallback entirely
# if username == "demo" and password == "demo123":
#     return {"name": "Demo User", ...}
```

## Next Steps

1. **User Action Required:** Log out and log back in with proper credentials
2. **Create a new test order** (not order 60e91dad, that one is historical)
3. **Check the logs** to see what session data and customer profile name are being used
4. **Share the log output** so I can determine which scenario is occurring

## Expected Behavior After Fix

Once logged in with proper Keycloak credentials:

1. **Session should have:**

   - `name`: "Mario Manager" (or whatever the Keycloak user's name is)
   - `email`: "manager@mario-pizzeria.com"
   - `user_id`: Keycloak sub claim

2. **Customer profile should have:**

   - `name`: "Mario Manager"
   - `email`: "manager@mario-pizzeria.com"

3. **Orders should display:**
   - Kitchen: "Mario Manager" as customer name
   - Order history: Orders appear under the manager's profile

## Temporary Workaround

If the issue persists, you can manually update the customer profile:

1. Go to the profile page
2. Update the name to the correct value
3. Future orders will use the updated name

But the root cause (session getting wrong name) should still be fixed.
