# Controller Routing Fix - Validation and Usage Guide

This document describes the fix for the controller routing issue and provides
usage examples and validation.

## Problem Summary

Controllers registered via `WebApplicationBuilder.add_controllers()` were not
being mounted to the FastAPI application, resulting in:

- Empty Swagger UI ("No operations defined in spec!")
- 404 errors for all API endpoints
- Empty OpenAPI spec

## Root Causes

1. **`add_controllers()`**: Only registered controller types to DI container,
   didn't mount routes to FastAPI app
2. **`use_controllers()`**: Had bugs trying to instantiate controllers without DI
   and calling non-existent methods
3. **`build()`**: Didn't automatically mount registered controllers

## Fix Implementation

### 1. Fixed `use_controllers()` Method

**File**: `neuroglia/hosting/web.py` - `WebHostBase.use_controllers()`

```python
def use_controllers(self, module_names: Optional[list[str]] = None):
    """
    Mount controller routes to the FastAPI application.

    This method retrieves all registered controller instances from the DI container
    and includes their routers in the FastAPI application.
    """
    from neuroglia.mvc.controller_base import ControllerBase

    # Get all registered controller instances from DI container
    # Controllers are already instantiated by DI with proper dependencies
    controllers = self.services.get_services(ControllerBase)

    # Include each controller's router in the FastAPI application
    for controller in controllers:
        # ControllerBase extends Routable, which has a 'router' attribute
        self.include_router(
            controller.router,
            prefix="/api",  # All controllers mounted under /api prefix
        )

    return self
```

**Key Changes**:

- ✅ Retrieves controller instances from DI container (properly initialized)
- ✅ Uses `include_router()` instead of `mount()` (correct FastAPI API)
- ✅ Accesses `controller.router` attribute (exists via Routable base class)
- ✅ No more attempts to call non-existent methods

### 2. Enhanced `build()` Method with Auto-Mounting

**File**: `neuroglia/hosting/web.py` - `WebApplicationBuilder.build()`

```python
def build(self, auto_mount_controllers: bool = True) -> WebHostBase:
    """
    Build the web host application with configured services and settings.

    Args:
        auto_mount_controllers: If True (default), automatically mounts all
                               registered controllers. Set to False for manual control.
    """
    host = WebHost(self.services.build())

    # Automatically mount registered controllers if requested
    if auto_mount_controllers:
        host.use_controllers()

    return host
```

**Key Changes**:

- ✅ Automatically calls `use_controllers()` by default
- ✅ Optional `auto_mount_controllers` parameter for manual control
- ✅ Convenient for 99% of use cases (auto-mounting)
- ✅ Flexible for advanced scenarios (manual control)

## Usage Examples

### Example 1: Standard Usage (Auto-Mount)

```python
from neuroglia.hosting.web import WebApplicationBuilder

# Build application
builder = WebApplicationBuilder()

# Register controllers
builder.add_controllers(["api.controllers"])

# Build - controllers automatically mounted
app = builder.build()

# Run application
app.run()
```

**Result**: ✅ All controller routes automatically available at `/api/{controller}/{endpoint}`

### Example 2: Manual Control

```python
from neuroglia.hosting.web import WebApplicationBuilder

builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])

# Build WITHOUT auto-mounting
app = builder.build(auto_mount_controllers=False)

# ... additional configuration ...

# Manually mount when ready
app.use_controllers()

app.run()
```

### Example 3: Verify Routes are Mounted

```python
from neuroglia.hosting.web import WebApplicationBuilder

builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])
app = builder.build()

# Check mounted routes
for route in app.routes:
    print(f"Route: {route.path} - Methods: {route.methods if hasattr(route, 'methods') else 'N/A'}")

# Access Swagger UI
# Navigate to: http://localhost:8000/api/docs
```

### Example 4: Multiple Controller Modules

```python
builder = WebApplicationBuilder()
builder.add_controllers([
    "api.controllers",
    "admin.controllers",
    "internal.controllers"
])
app = builder.build()
app.run()
```

## Controller Structure Example

```python
from neuroglia.mvc import ControllerBase
from classy_fastapi.decorators import get, post, put, delete

class UsersController(ControllerBase):
    # Automatic route prefix: /api/users
    # Automatic tags: ["Users"]

    @get("/{user_id}")
    async def get_user(self, user_id: str):
        query = GetUserByIdQuery(user_id=user_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/")
    async def create_user(self, create_user_dto: CreateUserDto):
        command = self.mapper.map(create_user_dto, CreateUserCommand)
        result = await self.mediator.execute_async(command)
        return self.process(result)
```

**Generated Routes**:

- `GET /api/users/{user_id}` - Get user by ID
- `POST /api/users/` - Create new user

## Verification Checklist

✅ **Controllers registered to DI container**

- Use `builder.add_controllers(["api.controllers"])`
- Controllers are singleton instances with proper dependency injection

✅ **Routes mounted to FastAPI application**

- Happens automatically in `build()` by default
- Or manually via `app.use_controllers()`

✅ **Swagger UI shows endpoints**

- Navigate to `http://localhost:8000/api/docs`
- Should see all controller endpoints listed

✅ **OpenAPI spec is populated**

- GET `http://localhost:8000/openapi.json`
- Should contain `paths` with controller routes

✅ **API endpoints respond correctly**

- Test actual HTTP requests to controller endpoints
- Should return expected responses (not 404)

## Migration from Workaround

If you were using the manual workaround:

### Before (Workaround)

```python
builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])
app = builder.build()

# ⚠️ WORKAROUND: Manually mount controller routes
from neuroglia.mvc import ControllerBase
controllers = app.services.get_services(ControllerBase)
for controller in controllers:
    app.include_router(controller.router)

app.run()
```

### After (Fixed)

```python
builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])
app = builder.build()  # ✅ Controllers automatically mounted!
app.run()
```

## Technical Details

### How It Works

1. **Controller Discovery**: `add_controllers()` discovers all controller classes
   in specified modules using `TypeFinder.get_types()`

2. **DI Registration**: Each controller type is registered as a singleton in the
   DI container with interface `ControllerBase`

3. **Controller Instantiation**: When building the service provider, DI container
   instantiates controllers with required dependencies:

   - `ServiceProviderBase` (for accessing other services)
   - `Mapper` (for DTO ↔ Entity mapping)
   - `Mediator` (for CQRS command/query dispatch)

4. **Router Creation**: Controllers extend `Routable` (from classy-fastapi),
   which automatically creates an `APIRouter` with all decorated endpoints

5. **Route Mounting**: `use_controllers()` retrieves controller instances from
   DI and calls `app.include_router(controller.router, prefix="/api")`

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ WebApplicationBuilder                                            │
├─────────────────────────────────────────────────────────────────┤
│ add_controllers(["api.controllers"])                            │
│   ↓                                                              │
│ Discovers controller types via TypeFinder                       │
│   ↓                                                              │
│ Registers each type to DI: services.add_singleton(ControllerBase│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ builder.build()                                                  │
├─────────────────────────────────────────────────────────────────┤
│ 1. Creates WebHost with service provider                        │
│ 2. DI instantiates all controllers with dependencies            │
│ 3. Auto-calls use_controllers() (if auto_mount_controllers=True│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ use_controllers()                                                │
├─────────────────────────────────────────────────────────────────┤
│ 1. Gets controllers: services.get_services(ControllerBase)     │
│ 2. For each controller:                                         │
│    - Accesses controller.router (FastAPI APIRouter)            │
│    - Calls app.include_router(router, prefix="/api")           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ FastAPI Application                                              │
├─────────────────────────────────────────────────────────────────┤
│ ✅ Routes mounted at /api/{controller}/{endpoint}               │
│ ✅ Swagger UI at /api/docs shows all endpoints                  │
│ ✅ OpenAPI spec includes controller routes                      │
│ ✅ HTTP requests work correctly                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Issue: Swagger UI still shows "No operations defined"

**Causes**:

- Controllers not registered via `add_controllers()`
- `auto_mount_controllers=False` without manual `use_controllers()` call
- Controllers don't extend `ControllerBase`
- No endpoint decorators on controller methods

**Solution**:

```python
# Ensure controllers are registered
builder.add_controllers(["api.controllers"])

# Ensure auto-mounting is enabled (default)
app = builder.build()  # or builder.build(auto_mount_controllers=True)

# Or manually mount
app = builder.build(auto_mount_controllers=False)
app.use_controllers()
```

### Issue: 404 errors for controller endpoints

**Cause**: Routes not mounted to FastAPI app

**Solution**: Verify `use_controllers()` was called (automatically or manually)

### Issue: "Controller requires ServiceProviderBase, Mapper, Mediator"

**Cause**: Controllers not instantiated via DI container

**Solution**: Don't manually instantiate controllers - let the framework handle it:

```python
# ❌ Don't do this
controller = MyController(provider, mapper, mediator)

# ✅ Do this
builder.add_controllers(["api.controllers"])
app = builder.build()
```

## Summary

The fix ensures that:

1. ✅ Controllers are properly registered to DI container
2. ✅ Controllers are instantiated with proper dependencies
3. ✅ Controller routes are automatically mounted to FastAPI app
4. ✅ Swagger UI displays all controller endpoints
5. ✅ OpenAPI spec includes controller operations
6. ✅ API endpoints respond correctly to HTTP requests

The default behavior (auto-mounting) works for 99% of use cases, with an option
for manual control when needed.
