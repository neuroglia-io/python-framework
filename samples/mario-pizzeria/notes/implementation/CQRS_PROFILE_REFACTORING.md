# CQRS Refactoring - Profile Auto-Creation

**Date:** October 22, 2025
**Status:** ✅ Complete
**Type:** Architecture Refactoring

---

## Problem

The `ProfileController.get_my_profile()` endpoint was violating CQRS principles by:

1. **Direct Repository Access**: Controller had repository injected as dependency
2. **Business Logic in API Layer**: Profile lookup/linking/creation logic in controller
3. **Violation of Framework Conventions**: API layer should only orchestrate, not implement business logic

```python
# ❌ Before: Business logic in API layer
@get("/me")
async def get_my_profile(
    self,
    token: dict = Depends(validate_token),
    customer_repository: ICustomerRepository = Depends(),  # Repository in API layer!
):
    # ... 60+ lines of business logic here
    existing_customer = await customer_repository.get_by_email_async(email)
    if existing_customer:
        existing_customer.state.user_id = user_id
        await customer_repository.update_async(existing_customer)
    # ... more logic
```

### Architecture Violation

The previous implementation broke the layered architecture:

```
API Layer (Controller) ──┐
                         ├──> Repository (Should go through Application layer!)
Integration Layer ───────┘
```

**Correct architecture:**

```
API Layer (Controller)
    ↓
Application Layer (Query/Command Handlers) ← Business Logic Here
    ↓
Integration Layer (Repositories)
```

---

## Solution

Created `GetOrCreateCustomerProfileQuery` and `GetOrCreateCustomerProfileHandler` following CQRS pattern:

```python
# ✅ After: Thin controller, business logic in Application layer
@get("/me")
async def get_my_profile(
    self,
    token: dict = Depends(validate_token),
):
    user_id = self._get_user_id_from_token(token)
    token_email = token.get("email")
    token_name = token.get("name", token.get("preferred_username", "User"))

    # Delegate to Application layer via Mediator
    query = GetOrCreateCustomerProfileQuery(
        user_id=user_id,
        email=token_email,
        name=token_name,
    )

    result = await self.mediator.execute_async(query)
    return self.process(result)
```

**Reduced from 60+ lines to 10 lines!**

---

## Implementation

### 1. Created Query and Handler

**File:** `application/queries/get_or_create_customer_profile_query.py`

Following framework convention of keeping query and handler in same file:

```python
@dataclass
class GetOrCreateCustomerProfileQuery(Query[OperationResult[CustomerProfileDto]]):
    """Query to get or create customer profile for authenticated user."""

    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None


class GetOrCreateCustomerProfileHandler(
    QueryHandler[GetOrCreateCustomerProfileQuery, OperationResult[CustomerProfileDto]]
):
    """Handler implementing three-tier lookup strategy"""

    def __init__(
        self,
        customer_repository: ICustomerRepository,  # Repository in Application layer ✅
        mediator: Mediator,
        mapper: Mapper,
    ):
        self.customer_repository = customer_repository
        self.mediator = mediator
        self.mapper = mapper

    async def handle_async(
        self, request: GetOrCreateCustomerProfileQuery
    ) -> OperationResult[CustomerProfileDto]:
        # Scenario 1: Fast path (existing by user_id)
        existing_query = GetCustomerProfileByUserIdQuery(user_id=request.user_id)
        existing_result = await self.mediator.execute_async(existing_query)

        if existing_result.is_success:
            return existing_result

        # Scenario 2: Migration path (existing by email, link to user_id)
        if request.email:
            existing_customer = await self.customer_repository.get_by_email_async(request.email)

            if existing_customer:
                if not existing_customer.state.user_id:
                    existing_customer.state.user_id = request.user_id
                    await self.customer_repository.update_async(existing_customer)

                profile_dto = CustomerProfileDto(...)
                return self.ok(profile_dto)

        # Scenario 3: Creation path (new profile from token claims)
        command = CreateCustomerProfileCommand(...)
        create_result = await self.mediator.execute_async(command)

        if not create_result.is_success:
            return self.bad_request(f"Failed to create profile: {create_result.error_message}")

        return create_result
```

### 2. Updated ProfileController

**File:** `api/controllers/profile_controller.py`

**Removed:**

- `from domain.repositories import ICustomerRepository`
- Repository dependency injection
- 60+ lines of business logic

**Added:**

- `from application.queries import GetOrCreateCustomerProfileQuery`
- Simple query construction and execution via mediator

### 3. Updated Query Exports

**File:** `application/queries/__init__.py`

Added exports for new query and handler:

```python
from .get_or_create_customer_profile_query import (
    GetOrCreateCustomerProfileHandler,
    GetOrCreateCustomerProfileQuery,
)

__all__ = [
    # ... other exports
    "GetOrCreateCustomerProfileQuery",
    "GetOrCreateCustomerProfileHandler",
]
```

### 4. Removed Separate Handler File

Deleted `application/handlers/get_or_create_customer_profile_handler.py` as it was consolidated into the query file following framework convention.

---

## Architecture Benefits

### ✅ Proper Layer Separation

```
┌─────────────────────────────────────────────┐
│  API Layer (ProfileController)             │
│  - Token extraction                         │
│  - Query construction                       │
│  - Result processing                        │
└─────────────────┬───────────────────────────┘
                  │ Mediator
                  ↓
┌─────────────────────────────────────────────┐
│  Application Layer (Query Handler)         │
│  - Profile lookup by user_id                │
│  - Email-based profile linking              │
│  - Profile creation logic                   │
│  - Business rules enforcement               │
└─────────────────┬───────────────────────────┘
                  │ Repository Interface
                  ↓
┌─────────────────────────────────────────────┐
│  Integration Layer (MotorRepository)        │
│  - Data access                              │
│  - MongoDB operations                       │
└─────────────────────────────────────────────┘
```

### ✅ Single Responsibility Principle

**API Layer:**

- Extracts data from HTTP request/token
- Constructs query objects
- Processes results into HTTP responses

**Application Layer:**

- Implements business logic
- Orchestrates domain operations
- Handles profile lookup/linking/creation strategies

**Integration Layer:**

- Data persistence
- External system integration

### ✅ Testability

**Before:** Hard to test controller without mocking repository, service provider, mediator, etc.

**After:**

```python
# Easy to test query handler in isolation
class TestGetOrCreateCustomerProfileHandler:
    def test_existing_profile_by_user_id(self):
        mock_mediator = Mock()
        mock_mediator.execute_async.return_value = OperationResult.ok(profile_dto)

        handler = GetOrCreateCustomerProfileHandler(
            customer_repository=mock_repo,
            mediator=mock_mediator,
            mapper=mock_mapper
        )

        query = GetOrCreateCustomerProfileQuery(user_id="123")
        result = await handler.handle_async(query)

        assert result.is_success

    def test_profile_linking_by_email(self):
        # Test email-based linking
        ...

    def test_profile_creation(self):
        # Test new profile creation
        ...
```

### ✅ Framework Consistency

Now follows same pattern as all other features:

- **Orders**: `CreateOrderCommand` → `CreateOrderHandler`
- **Menu**: `GetMenuQuery` → `GetMenuQueryHandler`
- **Kitchen**: `GetKitchenStatusQuery` → `GetKitchenStatusQueryHandler`
- **Profile**: `GetOrCreateCustomerProfileQuery` → `GetOrCreateCustomerProfileHandler` ✅

---

## Comparison: Before vs After

### Lines of Code

**Before:**

- `profile_controller.py`: ~200 lines (60+ in get_my_profile)
- Total: 200 lines

**After:**

- `profile_controller.py`: ~140 lines (10 in get_my_profile)
- `get_or_create_customer_profile_query.py`: ~125 lines (new)
- Total: 265 lines

**+65 lines total, but:**

- ✅ Proper layer separation
- ✅ Testable business logic
- ✅ Reusable query (can be used from UI controller, background jobs, etc.)
- ✅ Follows framework conventions

### Complexity

**Before (API Layer):**

```
get_my_profile() method:
  ├─ Token extraction
  ├─ Query by user_id
  ├─ Repository access (email lookup)
  ├─ Profile linking logic
  ├─ Name parsing logic
  ├─ Command construction
  ├─ Error handling
  └─ DTO conversion

Cyclomatic Complexity: ~8
Responsibilities: ~7
```

**After (API Layer):**

```
get_my_profile() method:
  ├─ Token extraction
  ├─ Query construction
  └─ Result processing

Cyclomatic Complexity: ~2
Responsibilities: ~3
```

**After (Application Layer):**

```
GetOrCreateCustomerProfileHandler:
  ├─ Query by user_id
  ├─ Repository access (email lookup)
  ├─ Profile linking logic
  ├─ Name parsing logic
  ├─ Command construction
  ├─ Error handling
  └─ DTO conversion

Cyclomatic Complexity: ~6
Responsibilities: ~5
```

**Result:** Complexity moved from API to Application layer where it belongs! ✅

---

## Testing Strategy

### Unit Tests (To Be Written)

**File:** `tests/cases/test_get_or_create_customer_profile_handler.py`

Test scenarios:

1. **Scenario 1 - Fast Path:**

   - Profile exists by user_id
   - Should return immediately without repository access

2. **Scenario 2 - Migration Path:**

   - Profile exists by email without user_id
   - Should link profile to user_id
   - Should update repository
   - Should return linked profile

3. **Scenario 3 - Creation Path:**

   - No profile exists
   - Should create new profile via command
   - Should return created profile

4. **Edge Cases:**
   - Email exists but belongs to different user_id (should create new)
   - No email provided (should use fallback)
   - Name parsing edge cases

### Integration Tests

Test complete flow:

1. Authenticate via OAuth2
2. Call GET /api/profile/me
3. Verify profile created in MongoDB
4. Call again, verify same profile returned (fast path)

---

## Files Changed

### Modified

- ✅ `api/controllers/profile_controller.py` - Simplified get_my_profile() to use query
- ✅ `application/queries/__init__.py` - Added exports for new query

### Created

- ✅ `application/queries/get_or_create_customer_profile_query.py` - Query and handler

### Deleted

- ✅ `application/handlers/get_or_create_customer_profile_handler.py` - Consolidated into query file

---

## Related Documentation

- **Framework Guide:** `.github/copilot-instructions.md` - CQRS patterns
- **Previous Refactoring:** `notes/DEPENDENCY_INJECTION_REFACTORING.md` - DI pattern fix
- **API Profile Feature:** `notes/API_PROFILE_AUTO_CREATION.md` - Feature documentation
- **Email Conflict Fix:** `notes/API_PROFILE_EMAIL_CONFLICT_FIX.md` - Migration support

---

## Summary

✅ **Moved business logic from API layer to Application layer**
✅ **Follows CQRS and framework conventions**
✅ **Improved testability and maintainability**
✅ **Proper layer separation (API → Application → Integration)**
✅ **Query and handler in single file following framework pattern**
✅ **Reduced controller complexity from ~60 lines to ~10 lines**
✅ **Business logic now reusable across different entry points**

**Status:** ✅ Implementation Complete - Ready for Testing
