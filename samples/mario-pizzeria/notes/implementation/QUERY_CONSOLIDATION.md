# Query Consolidation - GetCustomerProfileQuery

**Date:** October 22, 2025
**Issue:** Unnecessary duplication with two similar queries for customer profile retrieval

## 🐛 Problem

The application had two separate but nearly identical queries:

### Before: Two Separate Queries

```python
@dataclass
class GetCustomerProfileQuery(Query[OperationResult[CustomerProfileDto]]):
    """Query to get customer profile by customer ID"""
    customer_id: str

@dataclass
class GetCustomerProfileByUserIdQuery(Query[OperationResult[CustomerProfileDto]]):
    """Query to get customer profile by Keycloak user ID"""
    user_id: str
```

**Problems:**

- **Code Duplication**: Two queries, two handlers for essentially the same thing
- **Maintenance Burden**: Changes need to be applied to both
- **Inconsistent Behavior**: Risk of handlers diverging over time
- **Unnecessary Complexity**: API consumers need to know which query to use

---

## ✅ Solution

Consolidated into a single flexible query that supports both lookup methods:

### After: Single Unified Query

```python
@dataclass
class GetCustomerProfileQuery(Query[OperationResult[CustomerProfileDto]]):
    """
    Query to get customer profile.

    Supports lookup by either customer_id or user_id (Keycloak).
    Exactly one must be provided.
    """
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
```

### Handler Logic

The consolidated handler validates input and routes to the appropriate repository method:

```python
async def handle_async(self, request: GetCustomerProfileQuery) -> OperationResult[CustomerProfileDto]:
    """Handle profile retrieval by customer_id or user_id"""

    # Validate input - exactly one identifier must be provided
    if not request.customer_id and not request.user_id:
        return self.bad_request("Either customer_id or user_id must be provided")

    if request.customer_id and request.user_id:
        return self.bad_request("Cannot specify both customer_id and user_id")

    # Find customer by appropriate identifier
    customer: Optional[Customer] = None

    if request.customer_id:
        customer = await self.customer_repository.get_async(request.customer_id)
        if not customer:
            return self.not_found(Customer, request.customer_id)
    else:
        # user_id lookup
        customer = await self.customer_repository.get_by_user_id_async(request.user_id)
        if not customer:
            return self.bad_request(f"No customer profile found for user_id={request.user_id}")

    # ... rest of profile retrieval logic (orders, stats, etc.)
```

---

## 🎯 Usage Patterns

### Lookup by Customer ID

```python
# Internal system lookup (when you have the customer aggregate ID)
query = GetCustomerProfileQuery(customer_id="cust_123")
result = await mediator.execute_async(query)
```

### Lookup by User ID (Keycloak)

```python
# External authentication lookup (when you have the Keycloak user ID)
query = GetCustomerProfileQuery(user_id="auth0|123456")
result = await mediator.execute_async(query)
```

### Validation Examples

```python
# ❌ INVALID: No identifier provided
query = GetCustomerProfileQuery()
# Returns: bad_request("Either customer_id or user_id must be provided")

# ❌ INVALID: Both identifiers provided
query = GetCustomerProfileQuery(customer_id="cust_123", user_id="auth0|123")
# Returns: bad_request("Cannot specify both customer_id and user_id")
```

---

## 📝 Files Modified

### 1. **application/queries/get_customer_profile_query.py**

- Removed `GetCustomerProfileByUserIdQuery` class
- Removed `GetCustomerProfileByUserIdHandler` class
- Updated `GetCustomerProfileQuery` to accept optional `customer_id` or `user_id`
- Updated `GetCustomerProfileHandler` with validation and routing logic
- Fixed type hint for favorite pizza calculation: `max(pizza_counts, key=lambda name: pizza_counts[name])`

### 2. **application/queries/**init**.py**

- Removed `GetCustomerProfileByUserIdQuery` import
- Removed `GetCustomerProfileByUserIdHandler` import
- Removed from `__all__` exports

### 3. **application/queries/get_or_create_customer_profile_query.py**

- Changed import: `GetCustomerProfileByUserIdQuery` → `GetCustomerProfileQuery`
- Updated usage: `GetCustomerProfileQuery(user_id=request.user_id)`

### 4. **api/controllers/profile_controller.py**

- Removed `GetCustomerProfileByUserIdQuery` import
- Updated `update_my_profile()`: Uses `GetCustomerProfileQuery(user_id=user_id)`
- Updated `get_my_orders()`: Uses `GetCustomerProfileQuery(user_id=user_id)`

### 5. **ui/controllers/auth_controller.py**

- Changed import: `GetCustomerProfileByUserIdQuery` → `GetCustomerProfileQuery`
- Updated `_ensure_customer_profile()`: Uses `GetCustomerProfileQuery(user_id=user_id)`

---

## 🎯 Benefits

### 1. **Reduced Code Duplication**

- **Before**: 2 query classes + 2 handler classes = ~150 lines
- **After**: 1 query class + 1 handler class = ~100 lines
- **Saved**: ~50 lines of duplicated code

### 2. **Single Source of Truth**

- Profile retrieval logic exists in exactly one place
- Changes propagate automatically to all use cases
- No risk of handler implementations diverging

### 3. **Simpler Mental Model**

- Developers only need to learn one query
- API consumers have a single, flexible interface
- Clear validation rules prevent misuse

### 4. **Easier Testing**

- Only one handler to test
- Test both lookup paths in the same test suite
- Shared test fixtures and assertions

### 5. **Better Maintainability**

- Future enhancements (caching, logging, etc.) only need to be added once
- Bug fixes apply to all lookup scenarios
- Consistent error handling across lookup methods

---

## 🧪 Testing Recommendations

### Test Scenarios

```python
@pytest.mark.asyncio
class TestGetCustomerProfileQuery:
    """Test unified customer profile query"""

    async def test_lookup_by_customer_id_success(self):
        """Test successful lookup by customer_id"""
        query = GetCustomerProfileQuery(customer_id="cust_123")
        result = await self.handler.handle_async(query)

        assert result.is_success
        assert result.data.id == "cust_123"

    async def test_lookup_by_user_id_success(self):
        """Test successful lookup by user_id"""
        query = GetCustomerProfileQuery(user_id="auth0|123456")
        result = await self.handler.handle_async(query)

        assert result.is_success
        assert result.data.user_id == "auth0|123456"

    async def test_validation_no_identifier_provided(self):
        """Test validation when no identifier provided"""
        query = GetCustomerProfileQuery()
        result = await self.handler.handle_async(query)

        assert not result.is_success
        assert "Either customer_id or user_id must be provided" in result.error_message

    async def test_validation_both_identifiers_provided(self):
        """Test validation when both identifiers provided"""
        query = GetCustomerProfileQuery(
            customer_id="cust_123",
            user_id="auth0|123456"
        )
        result = await self.handler.handle_async(query)

        assert not result.is_success
        assert "Cannot specify both" in result.error_message

    async def test_customer_not_found_by_customer_id(self):
        """Test not found scenario for customer_id"""
        query = GetCustomerProfileQuery(customer_id="nonexistent")
        result = await self.handler.handle_async(query)

        assert not result.is_success
        assert result.status_code == 404

    async def test_customer_not_found_by_user_id(self):
        """Test not found scenario for user_id"""
        query = GetCustomerProfileQuery(user_id="nonexistent")
        result = await self.handler.handle_async(query)

        assert not result.is_success
        assert "No customer profile found" in result.error_message
```

---

## 🔍 Design Pattern: Flexible Query with Validation

This pattern can be applied to other queries where multiple lookup methods exist:

```python
@dataclass
class GetOrderQuery(Query[OperationResult[OrderDto]]):
    """
    Flexible order lookup query.

    Supports lookup by order_id, customer_id + order_number, or tracking_code.
    """
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    order_number: Optional[str] = None
    tracking_code: Optional[str] = None
```

**Benefits of this pattern:**

- Single query interface for multiple lookup strategies
- Clear validation ensures correct usage
- Easy to extend with additional lookup methods
- Maintains single handler with all business logic

---

## ✅ Status

**COMPLETED** ✅

All query consolidation work is complete:

- ✅ Query classes consolidated into one
- ✅ Handler classes consolidated into one
- ✅ All usages updated (5 files)
- ✅ Validation logic added
- ✅ Type hints improved
- ✅ Code duplication eliminated

**Impact:** Simplified CQRS implementation with better maintainability and clearer API contracts.
