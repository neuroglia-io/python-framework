# Fixing Manager User in Keycloak

## Issue

- Manager user showed "unknown error" for created date in Keycloak
- User was deleted
- Need to recreate with correct configuration

## Correct Manager User Configuration

### Option 1: Recreate via Keycloak UI

1. **Access Keycloak Admin Console:**

   ```
   http://localhost:8090
   Username: admin
   Password: admin
   ```

2. **Navigate to Users:**

   - Realm: mario-pizzeria
   - Left menu: Users
   - Click "Add user"

3. **User Details:**
   ```
   Username: manager
   Email: manager@mario-pizzeria.com
   First Name: Mario
   Last Name: Manager
   Email Verified: ON
   Enabled: ON
   ```
4. **Click "Create"**

5. **Set Password:**

   - Go to "Credentials" tab
   - Click "Set password"
   - Password: `password123`
   - Temporary: OFF
   - Click "Set password"

6. **Assign Role:**
   - Go to "Role mapping" tab
   - Click "Assign role"
   - Select "manager" role
   - Click "Assign"
   - **Do NOT assign "chef" role** (unnecessary!)

### Option 2: Update Realm Export File

Update the realm export file with ONLY manager role:

```json
{
  "username": "manager",
  "email": "manager@mario-pizzeria.com",
  "firstName": "Mario",
  "lastName": "Manager",
  "enabled": true,
  "emailVerified": true,
  "credentials": [
    {
      "type": "password",
      "value": "password123",
      "temporary": false
    }
  ],
  "realmRoles": ["manager"]
}
```

Then reimport the realm or restart Keycloak with the updated configuration.

## What Access Manager Role Provides

With ONLY the `"manager"` role, the user can access:

### ✅ Kitchen View

```python
# ui/controllers/kitchen_controller.py
has_access = "chef" in roles or "manager" in roles
# Result: True (because "manager" in roles)
```

### ✅ Management Dashboard

```python
# ui/controllers/management_controller.py
has_access = "manager" in roles
# Result: True
```

### ✅ Delivery View

```python
# ui/controllers/delivery_controller.py
has_access = "delivery_driver" in roles or "manager" in roles
# Result: True (because "manager" in roles)
```

### ✅ Menu & Orders

All authenticated users can access these, so manager can too.

## Testing the Fix

1. **Recreate the manager user** with only `"manager"` role
2. **Log out** completely from the application
3. **Clear browser cookies** or use incognito mode
4. **Log in:**
   - Username: `manager`
   - Password: `password123`
5. **Test access:**
   - Navigate to `/kitchen` - should work ✅
   - Navigate to `/management` - should work ✅
   - Create an order from `/menu` - should work ✅
   - Check order shows "Mario Manager" not "Demo User" ✅

## About the "Unknown Error" for Created Date

This is a known Keycloak issue when:

- User was imported from realm export
- `createdTimestamp` field is missing or invalid
- It's cosmetic and doesn't affect functionality

**Solutions:**

1. **Ignore it** - doesn't affect authentication
2. **Recreate user via UI** - UI-created users have proper timestamps
3. **Add timestamp to export:**
   ```json
   {
     "username": "manager",
     "createdTimestamp": 1729000000000,  // Unix timestamp in milliseconds
     ...
   }
   ```

## Summary

**You were correct!** The manager user only needs the `"manager"` role. The `"chef"` role was redundant because the code explicitly checks for `"manager"` as an OR condition.

**Next steps:**

1. Recreate manager user in Keycloak with ONLY `"manager"` role
2. Log out and log back in
3. Create a test order
4. Verify it shows "Mario Manager" not "Demo User"
