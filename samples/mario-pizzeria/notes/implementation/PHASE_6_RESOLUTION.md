# Phase 6: Routing Issue Resolution

## Problem Summary

After completing Phase 5 (multi-app architecture with ui_app mounted at `/`), all UI routes were returning 404 errors despite correct code deployment and controller registration.

## Root Cause

The issue was **NOT** with the multi-app architecture or mounting strategy. The problem was that `ControllerBase` automatically sets the router prefix based on the controller class name in its `__init__()` method:

```python
# In ControllerBase.__init__()
self.name = self.__class__.__name__.replace("Controller", "").strip()
super().__init__(
    prefix=f"/{self.name.lower()}",  # Automatic prefix generation
    tags=[self.name],
)
```

This caused:

- `HomeController` → `/home/` prefix (should be `/`)
- `UIAuthController` → `/uiauth/` prefix (should be `/auth/`)

## Failed Approaches

1. **Attempting to override `self.router.prefix` after `super().__init__()`** - Didn't work because classy-fastapi had already set the prefix
2. **Removing ui_app and registering controllers directly to main app** - Wrong approach, broke the clean separation
3. **Multiple container rebuilds and restarts** - Code was correct but routes were wrong

## Solution

Override the `Routable.__init__()` call directly in the controller's `__init__()` method to set the correct prefix **before** the router is initialized:

### HomeController (Root Routes)

```python
class HomeController(ControllerBase):
    """Controller for home UI views."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        # Store DI services first
        from neuroglia.serialization.json import JsonSerializer

        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.json_serializer = service_provider.get_required_service(JsonSerializer)
        self.name = "Home"

        # Call Routable.__init__ directly with empty prefix for root routes
        from classy_fastapi import Routable
        from neuroglia.mvc.controller_base import generate_unique_id_function
        Routable.__init__(
            self,
            prefix="",  # Empty prefix for root routes
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )
```

### UIAuthController (Auth Routes)

```python
class UIAuthController(ControllerBase):
    """UI authentication controller - session cookies"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        # Store DI services first
        from neuroglia.serialization.json import JsonSerializer

        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.json_serializer = service_provider.get_required_service(JsonSerializer)
        self.name = "Auth"

        # Initialize auth service
        self.auth_service = AuthService()

        # Call Routable.__init__ directly with /auth prefix
        from classy_fastapi import Routable
        from neuroglia.mvc.controller_base import generate_unique_id_function
        Routable.__init__(
            self,
            prefix="/auth",  # Auth routes prefix
            tags=["UI Auth"],
            generate_unique_id_function=generate_unique_id_function,
        )
```

## Verification

After the fix, all routes work correctly:

```bash
$ curl http://localhost:8080/
# Returns: Homepage HTML ✅

$ curl http://localhost:8080/auth/login
# Returns: Login page HTML ✅

$ curl http://localhost:8080/api/docs
# Returns: Swagger UI ✅
```

## Route Structure

```
Main App (/)
├── /api (api_app mounted)
│   ├── /docs (Swagger UI)
│   ├── /auth/token (JWT authentication)
│   ├── /menu/* (Menu endpoints)
│   ├── /orders/* (Order endpoints)
│   └── /kitchen/* (Kitchen endpoints)
└── / (ui_app mounted)
    ├── / (Homepage - HomeController)
    ├── /auth/login (Login page - UIAuthController)
    ├── /auth/logout (Logout - UIAuthController)
    └── /static/* (Static assets including Parcel builds)
```

## Key Learnings

1. **Multi-app architecture was correct** - The original Phase 5 design was sound
2. **Controller prefix is set at initialization time** - Must override in `__init__()`, not after
3. **Direct Routable initialization required** - Bypassing `super().__init__()` to control the prefix
4. **Hot reload works perfectly** - Changes were picked up immediately after the fix

## Commits

- `a9bc72e`: Fix UI controller routing - override prefix in **init**

## Status

✅ **RESOLVED** - All UI and API routes working correctly with proper multi-app architecture
