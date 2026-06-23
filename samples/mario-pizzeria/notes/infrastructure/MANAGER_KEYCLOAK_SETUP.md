# Keycloak Setup Guide - Manager Role

## Overview

This guide explains how to set up the `manager` role in Keycloak and create a test manager user with full access to all Mario's Pizzeria features.

## Prerequisites

- Keycloak is running (http://localhost:8080)
- Mario Pizzeria realm exists
- Admin credentials available

---

## Step 1: Create Manager Role

1. **Access Keycloak Admin Console**:

   - Navigate to: http://localhost:8080
   - Login with admin credentials

2. **Select Mario Pizzeria Realm**:

   - Click on the realm dropdown (top-left)
   - Select "mario-pizzeria"

3. **Create Manager Role**:
   - Navigate to: **Realm Roles** (left sidebar)
   - Click **Create Role** button
   - Enter role details:
     - **Role Name**: `manager`
     - **Description**: `Restaurant manager with full access to all features`
   - Click **Save**

---

## Step 2: Create Manager Test User

1. **Navigate to Users**:

   - Click **Users** in the left sidebar
   - Click **Add User** button

2. **Enter User Details**:

   ```
   Username: manager
   Email: manager@mario-pizzeria.com
   First Name: Mario
   Last Name: Manager
   Email Verified: ON
   Enabled: ON
   ```

   - Click **Create**

3. **Set Password**:

   - Navigate to **Credentials** tab
   - Click **Set Password**
   - Enter password details:

     ```
     Password: password123
     Temporary: OFF  (Important!)
     ```

   - Click **Set Password**
   - Confirm when prompted

4. **Assign Manager Role**:
   - Navigate to **Role Mappings** tab
   - In the **Available Roles** section, find and select: `manager`
   - Click **Add selected** to move it to **Assigned Roles**
   - Verify `manager` appears in the **Assigned Roles** list

---

## Step 3: Verify Role Assignment

**Check Assigned Roles for manager user**:

- `default-roles-mario-pizzeria` (automatic)
- `manager` (manually assigned)
- `offline_access` (automatic)
- `uma_authorization` (automatic)

**Note**: The manager role automatically provides access to:

- Customer features (menu, orders, profile)
- Chef features (kitchen dashboard)
- Delivery features (delivery dashboard)
- Management features (analytics, operations, menu management)

---

## Test User Credentials

| Role        | Username    | Password        | Email                          | Access Level          |
| ----------- | ----------- | --------------- | ------------------------------ | --------------------- |
| Customer    | customer    | password123     | customer@mario-pizzeria.com    | Menu, Orders, Profile |
| Chef        | chef        | password123     | chef@mario-pizzeria.com        | Customer + Kitchen    |
| Driver      | driver      | password123     | driver@mario-pizzeria.com      | Customer + Delivery   |
| **Manager** | **manager** | **password123** | **manager@mario-pizzeria.com** | **All Features**      |

---

## Step 4: Test Manager Access

1. **Restart the Application**:

   ```bash
   ./mario-docker.sh restart
   ```

2. **Login as Manager**:

   - Navigate to: http://localhost:3000
   - Click **Login**
   - Enter credentials:
     - Username: `manager`
     - Password: `password123`
   - Click **Sign In**

3. **Verify Manager Features**:

   **✅ Main Navigation Should Show**:

   - Home
   - Menu
   - My Orders
   - Kitchen
   - Delivery
   - **Management** ← New!

   **✅ User Dropdown Should Include**:

   - My Profile
   - Order History
   - Kitchen Dashboard
   - Delivery Dashboard
   - My Delivery Tour
   - **Management** section:
     - Dashboard
     - Operations Monitor
     - Menu Management
     - Analytics

   **✅ Home Page Should Show**:

   - Management Dashboard card (priority over other cards)

4. **Test Management Dashboard**:

   - Click **Management** in navigation
   - Should see: /management dashboard
   - Verify metrics display:
     - Total Orders Today
     - Revenue Today
     - Average Order Value
     - Active Orders
     - Kitchen Status (pending, confirmed, cooking, ready)
     - Delivery Status (delivering, delivered)
   - Connection status should show: "Live Updates Active" (green)

5. **Test Real-Time Updates**:

   - Keep management dashboard open
   - In another browser window, login as customer
   - Place a new order
   - Management dashboard should update within 5 seconds
   - Watch metrics animate when values change

6. **Test Navigation**:
   - Click "Operations Monitor" → Should navigate to /management/operations
   - Click "Kitchen Dashboard" link → Should navigate to /kitchen
   - Click "Delivery Dashboard" link → Should navigate to /delivery
   - Verify all features are accessible

---

## Troubleshooting

### Issue: 403 Access Denied when accessing /management

**Possible Causes**:

1. Manager role not assigned to user
2. Old session cached (logged in before role was added)
3. Role not appearing in JWT token

**Solutions**:

1. **Verify Role Assignment**:

   - In Keycloak, check user's Role Mappings tab
   - Ensure `manager` role is in Assigned Roles

2. **Clear Session and Re-login**:

   - Logout from Mario's Pizzeria
   - Close browser (to clear session)
   - Open new browser window
   - Login again as manager

3. **Check Application Logs**:

   ```bash
   docker logs mario-pizzeria-mario-pizzeria-app-1
   ```

   - Look for role extraction logs:

     ```
     Extracted roles for user manager: ['manager', ...]
     ```

4. **Verify JWT Token** (Advanced):
   - Open browser DevTools (F12)
   - Go to Application > Cookies
   - Check `mario_session` cookie exists
   - In console, check session storage
   - Roles should be stored in session

### Issue: Management link not appearing in navigation

**Solution**:

1. Check that roles are being passed to template:

   - View page source
   - Search for `roles`
   - Should see roles array in template context

2. Verify navigation template has correct conditional:

   ```html
   {% if 'manager' in roles %}
   ```

3. Ensure base.html is using latest version

### Issue: SSE not connecting (Connection Lost)

**Solution**:

1. Check application is running:

   ```bash
   docker ps | grep mario-pizzeria
   ```

2. Check SSE endpoint is accessible:

   ```bash
   curl -N http://localhost:3000/management/stream
   ```

3. Check browser console for errors

4. Verify SSE headers in Network tab (DevTools)

---

## Optional: Create Additional Manager Users

To create more manager users for testing:

1. Follow Step 2 with different usernames:

   - Username: `manager2`, `manager3`, etc.
   - Email: `manager2@mario-pizzeria.com`, etc.

2. Assign `manager` role to each user

3. Set passwords and test access

---

## Role Hierarchy Summary

```
┌─────────────┐
│   Manager   │  ← Full access to everything
├─────────────┤
│   Customer  │  Menu, Orders, Profile
│    Chef     │  Customer + Kitchen
│   Driver    │  Customer + Delivery
└─────────────┘
```

**Manager Role = Customer + Chef + Driver + Management Features**

---

## Next Steps

After successful setup:

1. ✅ Login as manager
2. ✅ Verify all features are accessible
3. ✅ Test real-time dashboard updates
4. ✅ Explore operations monitor
5. ⏳ Wait for Phase 2: Analytics implementation
6. ⏳ Wait for Phase 3: Menu management implementation

---

## Security Notes

**Production Considerations**:

1. **Strong Passwords**: Use complex passwords (not `password123`)
2. **HTTPS Only**: Enable HTTPS for Keycloak
3. **2FA**: Enable two-factor authentication
4. **Role Auditing**: Monitor who has manager role
5. **Session Timeout**: Configure appropriate session timeouts
6. **IP Whitelisting**: Restrict manager access by IP (optional)

**For Development**:

- Test credentials (`password123`) are acceptable
- HTTP is fine for local development
- Focus on functionality testing

---

## Conclusion

The manager role provides comprehensive access to all restaurant operations:

- Monitor real-time metrics and KPIs
- Oversee kitchen and delivery operations
- Access to analytics and reporting (coming in Phase 2)
- Menu management capabilities (coming in Phase 3)

**Ready for Testing!** 🎉

Follow Step 4 above to test the complete management dashboard workflow.
