# Keycloak Role Configuration for Mario's Pizzeria

## Current Role Structure

### Defined Roles

1. **`customer`** - Customer role for ordering pizzas
2. **`chef`** - Kitchen staff role for managing orders
3. **`manager`** - Restaurant manager role with full access

### Current User Assignments

| Username   | Roles      | Purpose                                            |
| ---------- | ---------- | -------------------------------------------------- |
| `customer` | `customer` | Regular customer - can only place orders           |
| `chef`     | `chef`     | Kitchen staff - can view and manage kitchen orders |
| `manager`  | `manager`  | Manager - has access to all areas                  |

## Role-Based Access Control (RBAC)

### Access Permissions by Area

#### Kitchen View (`/kitchen`)

**Required Roles:** `chef` OR `manager`

```python
# ui/controllers/kitchen_controller.py
has_access = "chef" in roles or "manager" in roles
```

**Why manager has access:** The code explicitly checks for `"manager"` in the OR condition, so manager role alone grants access.

#### Management Dashboard (`/management`)

**Required Roles:** `manager` ONLY

```python
# ui/controllers/management_controller.py
has_access = "manager" in roles
```

**Why only manager:** Contains sensitive business data, analytics, and menu management.

#### Delivery View (`/delivery`)

**Required Roles:** `delivery_driver` OR `manager`

```python
# ui/controllers/delivery_controller.py
has_access = "delivery_driver" in roles or "manager" in roles
```

**Why manager has access:** Managers may need to help with deliveries or monitor delivery operations.

#### Menu/Orders (Public areas)

**Required Roles:** Authenticated users (any role)

## Why Manager Has Both `manager` AND `chef` Roles

### Design Pattern: Hierarchical Roles

The current configuration follows a **hierarchical/additive role model**:

```
customer     → Can place orders
    ↓
chef         → Can place orders + manage kitchen
    ↓
manager      → Can place orders + manage kitchen + manage business
```

### Benefits of This Approach

1. **Operational Flexibility**

   - Manager can jump into kitchen operations during busy periods
   - No need to switch accounts to help with cooking
   - Single sign-on works across all areas

2. **Code Simplicity**

   - Controllers check: `"chef" in roles or "manager" in roles`
   - Don't need: `"chef" in roles or "manager" in roles or has_permission("kitchen.access")`

3. **Realistic Business Model**

   - In real pizzerias, managers often help in the kitchen
   - Reflects actual workflow and responsibilities

4. **Fail-Safe Access**
   - If chef is sick, manager can cover kitchen duties
   - Emergency access to all systems

### Alternative Approaches (NOT Recommended)

#### ❌ Option 1: Manager Role Only

```json
"realmRoles": ["manager"]
```

**Problems:**

- Need to change ALL code to check for manager role everywhere
- Code like `"chef" in roles or "manager" in roles` needed everywhere
- More complex permission logic

#### ❌ Option 2: Hierarchical Role Resolution

```python
def has_permission(user, permission):
    role_hierarchy = {
        "manager": ["chef", "customer"],
        "chef": ["customer"]
    }
    # Complex permission resolution logic...
```

**Problems:**

- Overly complex for this application
- Need custom permission resolver
- Harder to understand and maintain

## Recommended Configuration (Current)

### Keep Manager with Multiple Roles ✅

```json
{
  "username": "manager",
  "realmRoles": [
    "manager", // Access to management dashboard
    "chef" // Access to kitchen operations
  ]
}
```

### Why This Is Best

1. **Simple & Clear:** Easy to understand what manager can do
2. **Follows RBAC Best Practices:** Roles are additive capabilities
3. **Minimal Code Changes:** Works with existing permission checks
4. **Realistic:** Matches real-world restaurant operations
5. **Maintainable:** Easy for other developers to understand

## When to Use Manager-Only Role

You would ONLY assign `manager` role alone if:

1. You want managers to ONLY see the management dashboard
2. You don't want managers to access kitchen operations
3. You implement role hierarchy resolution in code

**But this doesn't make sense for a pizzeria!** Managers need operational visibility.

## Customer Role Behavior

### Important Note on Customer Orders

When a **manager** places an order from the menu:

- They are authenticated as `manager` user
- The order is created with their customer profile
- The order displays their name (e.g., "Mario Manager")
- **They are acting as a customer in this context**

This is correct behavior because:

- Managers can also order food
- The system needs to track WHO ordered, not their job role
- Customer profile is linked to user_id, not role

## Delivery Driver Role (Future)

Note: `delivery_driver` role is checked but not currently in the realm export. If you add delivery drivers:

```json
{
  "username": "driver",
  "realmRoles": [
    "delivery_driver",
    "customer" // Can also place orders
  ]
}
```

## Summary & Recommendations

### Current Configuration: ✅ CORRECT

The manager user should have **both** `manager` AND `chef` roles:

```json
"realmRoles": ["manager", "chef"]
```

### Reasoning

- Follows hierarchical/additive role model
- Matches real-world pizzeria operations
- Works cleanly with existing code
- Provides operational flexibility
- Simple to understand and maintain

### Don't Change It Unless

- You want to restrict managers from kitchen operations (unlikely)
- You implement a complex permission system (overkill)
- Business requirements explicitly demand it (not the case)

## Testing Access

To verify the manager has correct access:

1. **Log in as manager** (`manager`/`password123`)
2. **Should be able to access:**

   - ✅ `/management` - Management dashboard
   - ✅ `/kitchen` - Kitchen view
   - ✅ `/menu` - Order food
   - ✅ `/orders` - View their order history
   - ✅ `/delivery` - Delivery operations (if delivery_driver role added)

3. **Should NOT be able to access:**
   - ❌ Nothing - managers have full access

## Related Documentation

- `deployment/keycloak/mario-pizzeria-realm-export.json` - Role definitions
- `ui/controllers/*_controller.py` - Role-based access checks
- `CUSTOMER_NAME_FIX.md` - How customer profiles work for authenticated users
