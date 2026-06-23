# Dependency Injection Refactoring - ProfileController

**Date:** October 22, 2025
**Status:** ✅ Complete
**Type:** Code Quality Improvement

---

## Problem

The `get_my_profile()` endpoint was using the **Service Locator pattern** to resolve the `ICustomerRepository` dependency:

```python
# ❌ Anti-pattern: Service Locator inside method
@get("/me")
async def get_my_profile(self, token: dict = Depends(validate_token)):
    from domain.repositories import ICustomerRepository
    customer_repository = self.service_provider.get_service(ICustomerRepository)
    # ... use repository
```

### Issues with This Approach

1. **Hidden Dependencies**: Not visible in method signature
2. **Testing Difficulty**: Must mock `service_provider.get_service()`
3. **Runtime Resolution**: Dependency resolved at runtime instead of injection time
4. **Import Inside Method**: `from domain.repositories import ...` inside function
5. **Violates DI Principles**: Manually pulling dependencies instead of receiving them

---

## Solution

Refactored to use **FastAPI Method-Level Dependency Injection**:

```python
# ✅ Clean: Method-level dependency injection
@get("/me")
async def get_my_profile(
    self,
    token: dict = Depends(validate_token),
    customer_repository: ICustomerRepository = Depends(),  # Injected!
):
    # ... use repository directly
```

---

## Implementation

### Changes Made

**1. Moved import to module level:**

```python
# At top of file
from domain.repositories import ICustomerRepository
```

**2. Added repository as method parameter:**

```python
async def get_my_profile(
    self,
    token: dict = Depends(validate_token),
    customer_repository: ICustomerRepository = Depends(),  # Added
):
```

**3. Removed service locator code:**

```python
# Removed these lines:
# from domain.repositories import ICustomerRepository
# customer_repository = self.service_provider.get_service(ICustomerRepository)
```

**4. Fixed type safety issues:**

```python
# Handle Optional fields properly
profile_dto = CustomerProfileDto(
    name=existing_customer.state.name or "Unknown",  # Fallback for None
    email=existing_customer.state.email or token_email,  # Fallback for None
    ...
)
```

---

## Benefits

### 1. **Explicit Dependencies** ✅

Dependencies are now visible in the method signature:

```python
async def get_my_profile(
    self,
    token: dict = Depends(validate_token),        # Auth dependency
    customer_repository: ICustomerRepository = Depends(),  # Data dependency
):
```

Anyone reading the code can immediately see what this endpoint needs.

### 2. **Easier Testing** ✅

Testing is now straightforward:

```python
# Before (complex)
def test_get_my_profile():
    mock_service_provider = Mock()
    mock_service_provider.get_service.return_value = mock_repository
    controller = ProfileController(mock_service_provider, ...)

# After (simple)
def test_get_my_profile():
    mock_repository = Mock(spec=ICustomerRepository)
    await controller.get_my_profile(token=mock_token, customer_repository=mock_repository)
```

### 3. **FastAPI Integration** ✅

FastAPI's dependency injection system handles:

- Automatic resolution from DI container
- Proper scoping (scoped per request)
- Type checking and validation
- Automatic OpenAPI documentation

### 4. **Better Type Safety** ✅

Static type checkers (Pylance, mypy) can now:

- Verify the repository interface is correctly used
- Catch type mismatches at development time
- Provide better autocomplete

### 5. **Consistency** ✅

Now matches the pattern used in other endpoints:

```python
@get("/me", ...)
async def get_my_profile(
    self,
    token: dict = Depends(validate_token),           # Consistent
    customer_repository: ICustomerRepository = Depends(),  # Consistent
):

@put("/me", ...)
async def update_my_profile(
    self,
    request: UpdateProfileDto,
    token: dict = Depends(validate_token),  # Same pattern
):
```

---

## Dependency Injection Options Comparison

### Option 1: Constructor Injection

```python
class ProfileController(ControllerBase):
    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
        customer_repository: ICustomerRepository,  # Add here
    ):
        super().__init__(service_provider, mapper, mediator)
        self.customer_repository = customer_repository
```

**Pros:**

- Traditional OOP pattern
- Repository available to all methods

**Cons:**

- All controller instances "pay" for the dependency even if unused
- Clutters constructor with rarely-used dependencies

**Use When:** Multiple methods need the same dependency

---

### Option 2: Method-Level Injection (Chosen) ✅

```python
@get("/me")
async def get_my_profile(
    self,
    token: dict = Depends(validate_token),
    customer_repository: ICustomerRepository = Depends(),
):
```

**Pros:**

- Dependency only injected where needed
- Clear method-level dependencies
- Easier to test individual methods
- Follows FastAPI best practices

**Cons:**

- Slightly more verbose if many methods need it

**Use When:** Only one or two methods need the dependency

---

### Option 3: Service Locator (Previous) ❌

```python
@get("/me")
async def get_my_profile(self, token: dict = Depends(validate_token)):
    customer_repository = self.service_provider.get_service(ICustomerRepository)
```

**Pros:**

- Flexible (can resolve any dependency dynamically)

**Cons:**

- Hidden dependencies (anti-pattern)
- Harder to test
- Runtime resolution
- Violates DI principles

**Use When:** Never! This is an anti-pattern.

---

## Pattern for Other Controllers

This pattern should be applied to other controllers with similar needs:

### Example: OrdersController

```python
from domain.repositories import IOrderRepository

class OrdersController(ControllerBase):

    @get("/{order_id}")
    async def get_order(
        self,
        order_id: str,
        token: dict = Depends(validate_token),
        order_repository: IOrderRepository = Depends(),  # Method-level injection
    ):
        # Validate user has access to order
        user_id = self._get_user_id_from_token(token)
        order = await order_repository.get_by_id_async(order_id)

        if order and order.state.customer_id != user_id:
            raise HTTPException(403, "Access denied")

        return order
```

### Example: KitchenController

```python
from domain.repositories import IOrderRepository

class KitchenController(ControllerBase):

    @get("/queue")
    async def get_order_queue(
        self,
        token: dict = Depends(validate_token),
        order_repository: IOrderRepository = Depends(),  # Method-level injection
    ):
        # Only chefs can view kitchen queue
        self._require_role(token, "chef")

        pending_orders = await order_repository.get_by_status_async("pending")
        return pending_orders
```

---

## Testing Impact

### Before (Complex)

```python
class TestProfileController:
    def test_get_my_profile_links_existing_profile(self):
        # Setup
        mock_service_provider = Mock()
        mock_repository = Mock(spec=ICustomerRepository)
        mock_service_provider.get_service.return_value = mock_repository

        controller = ProfileController(
            service_provider=mock_service_provider,
            mapper=Mock(),
            mediator=Mock()
        )

        # Test
        result = await controller.get_my_profile(token=mock_token)

        # Verify
        mock_service_provider.get_service.assert_called_once_with(ICustomerRepository)
        mock_repository.get_by_email_async.assert_called_once()
```

### After (Simple)

```python
class TestProfileController:
    def test_get_my_profile_links_existing_profile(self):
        # Setup
        mock_repository = Mock(spec=ICustomerRepository)
        mock_repository.get_by_email_async.return_value = mock_customer

        controller = ProfileController(
            service_provider=Mock(),
            mapper=Mock(),
            mediator=Mock()
        )

        # Test - directly pass dependencies
        result = await controller.get_my_profile(
            token=mock_token,
            customer_repository=mock_repository  # Direct injection
        )

        # Verify
        mock_repository.get_by_email_async.assert_called_once()
```

**Benefits:**

- 50% less setup code
- No need to mock `service_provider.get_service()`
- Direct control over injected dependencies
- Clearer test intent

---

## Related Files

**Modified:**

- `api/controllers/profile_controller.py` - Refactored `get_my_profile()` method

**Pattern Applies To:**

- All controllers with method-specific dependencies
- Any FastAPI route that needs repository access
- Event handlers that need specific services

**Documentation:**

- `notes/DEPENDENCY_INJECTION_REFACTORING.md` - This document

---

## Summary

Refactored `ProfileController.get_my_profile()` to use **method-level dependency injection** instead of **service locator pattern**.

**Changes:**

- ✅ Moved `ICustomerRepository` import to module level
- ✅ Added repository as method parameter with `Depends()`
- ✅ Removed manual `service_provider.get_service()` calls
- ✅ Fixed type safety issues with Optional fields

**Benefits:**

- ✅ Explicit, visible dependencies
- ✅ Easier testing (50% less setup code)
- ✅ Better type safety and IDE support
- ✅ Follows FastAPI best practices
- ✅ Consistent with framework patterns

**Status:** ✅ Implementation Complete, Pattern Established
