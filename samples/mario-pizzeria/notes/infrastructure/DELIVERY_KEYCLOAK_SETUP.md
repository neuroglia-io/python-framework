# Delivery System - Keycloak Configuration Guide

## Overview

This guide explains how to add the `delivery_driver` role to the Mario's Pizzeria Keycloak realm and create a test delivery driver user.

## Steps to Configure Keycloak

### 1. Access Keycloak Admin Console

- URL: `http://localhost:8080` (or your Keycloak URL)
- Login with admin credentials
- Select the **mario-pizzeria** realm

### 2. Create the delivery_driver Role

1. Navigate to **Realm Roles** in the left sidebar
2. Click **Create Role**
3. Enter the following details:
   - **Role Name**: `delivery_driver`
   - **Description**: `Delivery driver role for managing order deliveries`
4. Click **Save**

### 3. Create Test Delivery Driver User

1. Navigate to **Users** in the left sidebar
2. Click **Add User**
3. Enter the following details:
   - **Username**: `driver`
   - **Email**: `driver@mario-pizzeria.com`
   - **First Name**: `Mario`
   - **Last Name**: `Driver`
   - **Email Verified**: Toggle **ON**
   - **Enabled**: Toggle **ON**
4. Click **Create**

### 4. Set Password for Driver User

1. After creating the user, go to the **Credentials** tab
2. Click **Set Password**
3. Enter:
   - **Password**: `password123`
   - **Password Confirmation**: `password123`
   - **Temporary**: Toggle **OFF** (so password doesn't need to be changed on first login)
4. Click **Save**
5. Confirm the password reset in the dialog

### 5. Assign delivery_driver Role to Driver User

1. While still in the driver user page, go to the **Role Mappings** tab
2. Under **Realm Roles**, find `delivery_driver` in the **Available Roles** list
3. Select `delivery_driver` and click **Add selected** (or use the arrow button)
4. Verify that `delivery_driver` now appears in the **Assigned Roles** list

### 6. Optional: Create Manager User (if not exists)

If you want a user with both kitchen and delivery access:

1. Follow steps 3-5 to create a user named `manager`
2. Assign both roles:
   - `chef`
   - `delivery_driver`
   - `manager` (if it exists)

## Test Users Summary

After configuration, you should have these test users:

| Username   | Password      | Roles                                | Access                                     |
| ---------- | ------------- | ------------------------------------ | ------------------------------------------ |
| `customer` | `password123` | `customer`                           | Menu, Orders, Profile                      |
| `chef`     | `password123` | `chef`                               | All customer features + Kitchen Dashboard  |
| `driver`   | `password123` | `delivery_driver`                    | All customer features + Delivery Dashboard |
| `manager`  | `password123` | `chef`, `delivery_driver`, `manager` | Full access to all features                |

## Verify Configuration

### Test Delivery Driver Access

1. **Logout** if currently logged in
2. **Login** as driver (driver / password123)
3. Verify you see:
   - ✅ **Delivery** link in main navigation
   - ✅ **Delivery Dashboard** card on home page
   - ✅ Can access `/delivery` (Ready Orders view)
   - ✅ Can access `/delivery/tour` (My Delivery Tour view)
4. Verify you do NOT see:
   - ❌ Kitchen link (chef-only)

### Test Access Control

1. **As Customer**: Should NOT see Kitchen or Delivery links
2. **As Chef**: Should see Kitchen but NOT Delivery links
3. **As Driver**: Should see Delivery but NOT Kitchen links
4. **As Manager**: Should see both Kitchen AND Delivery links

## Troubleshooting

### Issue: Driver Can't See Delivery Links

**Solution:**

1. Verify role assignment in Keycloak (User → Role Mappings)
2. Logout and login again to refresh session
3. Check browser console for JavaScript errors
4. Check application logs for role extraction

### Issue: 403 Access Denied When Accessing /delivery

**Possible Causes:**

1. Role not properly assigned in Keycloak
2. Old session (logged in before role was added)
3. Role extraction not working in auth controller

**Solution:**

1. Verify role in Keycloak
2. Logout and login to get fresh session with roles
3. Check logs for: `Extracted roles for user driver: ['delivery_driver']`

### Issue: Roles Not Being Extracted

**Check:**

1. Application logs during login for role extraction
2. Auth controller properly extracting from `user.get("roles", [])`
3. Session middleware is configured correctly

## Export Realm Configuration (Optional)

To save your configuration:

1. In Keycloak Admin Console, select **mario-pizzeria** realm
2. Click **Realm Settings**
3. Go to **Action** dropdown → **Partial Export**
4. Select:
   - ✅ Export groups and roles
   - ✅ Export clients
5. Click **Export**
6. Save the JSON file to `deployment/keycloak/mario-realm-export.json`

## Delivery Workflow After Configuration

With Keycloak properly configured, the delivery workflow works as follows:

1. **Customer** places order → Status: `pending`
2. **Chef** confirms order → Status: `confirmed`
3. **Chef** starts cooking → Status: `cooking`
4. **Chef** marks ready → Status: `ready` (appears in Delivery Ready Orders)
5. **Driver** picks up order → Status: `delivering` (appears in Driver's Tour)
6. **Driver** marks delivered → Status: `delivered`

## Security Notes

- In production, use stronger passwords
- Enable 2FA for privileged roles (chef, driver, manager)
- Use HTTPS for Keycloak
- Regularly audit role assignments
- Consider time-limited sessions for drivers
