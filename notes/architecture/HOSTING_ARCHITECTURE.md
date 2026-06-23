# Hosting Architecture

**Status**: Current Implementation
**Last Updated**: October 25, 2025

## Overview

The Neuroglia hosting system provides enterprise-grade application hosting infrastructure for building production-ready microservices. The architecture centers around a unified `WebApplicationBuilder` that automatically adapts between simple and advanced scenarios.

## Core Architecture

### Component Hierarchy

```
neuroglia.hosting
│
├── abstractions.py
│   ├── ApplicationBuilderBase       # Base builder interface
│   ├── ApplicationSettings          # Configuration management
│   ├── HostBase                     # Host abstraction
│   ├── HostedService                # Background service interface
│   └── HostApplicationLifetime      # Lifecycle management
│
├── web.py
│   ├── WebApplicationBuilderBase    # Abstract web builder
│   ├── WebApplicationBuilder        # Unified implementation (simple + advanced)
│   ├── WebHostBase                  # FastAPI host base
│   ├── WebHost                      # Basic host implementation
│   ├── EnhancedWebHost              # Advanced multi-app host
│   └── ExceptionHandlingMiddleware  # Global error handling
│
└── __init__.py
    └── Public API exports + backward compatibility aliases
```

### Design Principles

1. **Progressive Enhancement**: Start simple, add complexity as needed
2. **Automatic Adaptation**: Builder detects mode from configuration
3. **Backward Compatibility**: Existing code works without changes
4. **Type Safety**: Proper type hints with Union types
5. **Single Responsibility**: Clear separation of concerns

## WebApplicationBuilder

### Unified Builder Pattern

The `WebApplicationBuilder` is the primary entry point for application configuration. It automatically detects which features to enable based on how it's initialized.

#### Simple Mode

**Initialization**: `WebApplicationBuilder()`

**Features**:

- Basic FastAPI integration
- Controller auto-discovery
- Dependency injection
- Hosted service support
- Returns `WebHost`

**Example**:

```python
from neuroglia.hosting import WebApplicationBuilder

builder = WebApplicationBuilder()
builder.services.add_scoped(UserService)
builder.add_controllers(["api.controllers"])

host = builder.build()
host.run()
```

#### Advanced Mode

**Initialization**: `WebApplicationBuilder(app_settings)`

**Features**:

- All simple mode features
- Multi-application hosting
- Controller deduplication
- Custom prefix routing
- Observability integration
- Lifecycle management
- Returns `EnhancedWebHost`

**Example**:

```python
from neuroglia.hosting import WebApplicationBuilder
from application.settings import ApplicationSettings

app_settings = ApplicationSettings()
builder = WebApplicationBuilder(app_settings)

# Multi-app support
builder.add_controllers(["api.controllers"], prefix="/api")
builder.add_controllers(["admin.controllers"], prefix="/admin")

# Build with integrated lifecycle
app = builder.build_app_with_lifespan(
    title="My Microservice",
    version="1.0.0"
)

app.run()
```

### Mode Detection Logic

```python
def __init__(self, app_settings: Optional[Union[ApplicationSettings, ApplicationSettingsWithObservability]] = None):
    # Detect mode from presence of app_settings
    self._advanced_mode_enabled = app_settings is not None

    # Advanced-only features
    self._registered_controllers: dict[str, set[str]] = {}
    self._pending_controller_modules: list[dict] = []
    self._observability_config = None

    # Register settings if provided
    if app_settings:
        self.services.add_singleton(type(app_settings), lambda: app_settings)
```

### Build Method

```python
def build(self, auto_mount_controllers: bool = True) -> WebHostBase:
    service_provider = self.services.build_service_provider()

    # Choose host type based on mode
    if self._advanced_mode_enabled or self._registered_controllers:
        host = EnhancedWebHost(service_provider)
    else:
        host = WebHost(service_provider)

    return host
```

## Host Types

### WebHost (Simple)

**Purpose**: Basic FastAPI application hosting

**Features**:

- Single FastAPI app
- Standard controller mounting
- Service provider integration
- Basic lifecycle management

**Used When**:

- No app_settings provided
- Simple applications
- No multi-app requirements

### EnhancedWebHost (Advanced)

**Purpose**: Multi-application hosting with advanced features

**Features**:

- Multiple FastAPI applications in one process
- Controller deduplication tracking
- Custom prefix routing per app
- Observability endpoint integration
- Advanced lifecycle management

**Used When**:

- app_settings provided
- Multi-app architecture needed
- Complex routing requirements
- Observability integration required

**Automatic Instantiation**:

```python
# User writes this
builder = WebApplicationBuilder(app_settings)
host = builder.build()

# Framework automatically returns EnhancedWebHost
# User doesn't need to know the difference
```

## Controller Registration

### Simple Registration

```python
builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])
# Controllers auto-registered to main app with /api prefix
```

### Advanced Registration

```python
builder = WebApplicationBuilder(app_settings)

# Register to specific apps with custom prefixes
builder.add_controllers(["api.controllers"], app=api_app, prefix="/api/v1")
builder.add_controllers(["admin.controllers"], app=admin_app, prefix="/admin")

# Deduplication automatically handles shared controllers
```

### Controller Deduplication

The framework tracks which controllers are registered to which apps to prevent duplicates:

```python
self._registered_controllers = {
    "api_app": {"UsersController", "OrdersController"},
    "admin_app": {"AdminController"}
}
```

## Lifecycle Management

### HostedService Pattern

Background services implement the `HostedService` interface:

```python
class BackgroundProcessor(HostedService):
    async def start_async(self):
        # Start background processing
        pass

    async def stop_async(self):
        # Clean shutdown
        pass
```

### Host Lifecycle

```python
class Host:
    async def start_async(self):
        # 1. Start all hosted services
        # 2. Start FastAPI application
        # 3. Signal startup complete

    async def stop_async(self):
        # 1. Stop accepting new requests
        # 2. Complete in-flight requests
        # 3. Stop hosted services
        # 4. Dispose resources
```

### Integrated Lifespan

Advanced mode provides `build_app_with_lifespan()` for integrated lifecycle:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await host.start_async()
    yield
    # Shutdown
    await host.stop_async()

app = FastAPI(lifespan=lifespan)
```

## Dependency Injection Integration

### Service Registration

```python
builder = WebApplicationBuilder()

# Service lifetimes
builder.services.add_singleton(CacheService)     # One instance per app
builder.services.add_scoped(UnitOfWork)          # One instance per request
builder.services.add_transient(EmailService)     # New instance every time

# Controller registration
builder.services.add_controllers(["api.controllers"])

# Hosted services
builder.services.add_hosted_service(BackgroundProcessor)
```

### Service Resolution

```python
class UserController(ControllerBase):
    def __init__(self,
                 service_provider: ServiceProviderBase,
                 mapper: Mapper,
                 mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
        # Dependencies automatically resolved
```

## Exception Handling

### ExceptionHandlingMiddleware

Global exception handler that converts all unhandled exceptions into RFC 7807 Problem Details:

```python
class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception as ex:
            problem_details = ProblemDetails(
                "Internal Server Error",
                500,
                str(ex),
                "https://www.w3.org/Protocols/HTTP/HTRESP.html"
            )
            return Response(
                self.serializer.serialize_to_text(problem_details),
                500,
                media_type="application/json"
            )
```

### Usage

```python
app.add_middleware(
    ExceptionHandlingMiddleware,
    service_provider=host.services
)
```

## Configuration Management

### ApplicationSettings

Base configuration class using Pydantic Settings:

```python
from neuroglia.hosting.abstractions import ApplicationSettings

class MyAppSettings(ApplicationSettings):
    database_url: str = "mongodb://localhost:27017"
    cache_ttl: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### ApplicationSettingsWithObservability

Enhanced settings with OpenTelemetry configuration:

```python
from neuroglia.observability.settings import ApplicationSettingsWithObservability

class MyAppSettings(ApplicationSettingsWithObservability):
    # Inherits observability configuration
    # Plus custom app settings
    database_url: str = "mongodb://localhost:27017"
```

### Environment Variables

Settings automatically loaded from:

1. Environment variables
2. `.env` file
3. Default values

## Multi-App Architecture

### Use Cases

1. **API + Admin UI**: Separate apps for different user types
2. **Versioned APIs**: `/api/v1` and `/api/v2` in same process
3. **Microservices**: Multiple business domains in one service
4. **Gateway Pattern**: Main app delegates to sub-apps

### Implementation

```python
builder = WebApplicationBuilder(app_settings)

# Main API
builder.add_controllers(["api.controllers"], prefix="/api")

# Admin interface
builder.add_controllers(["admin.controllers"], prefix="/admin")

# Public UI
builder.add_controllers(["ui.controllers"], prefix="/ui")

# Build returns EnhancedWebHost managing all apps
host = builder.build()
```

### Controller Mounting

Controllers are mounted to their respective apps during the build process:

```python
def build(self):
    # ... service provider setup ...

    # Process pending controller registrations
    for pending in self._pending_controller_modules:
        app = pending['app']
        prefix = pending['prefix']
        modules = pending['modules']

        # Mount controllers with deduplication
        self._mount_controllers(app, modules, prefix)

    return host
```

## Observability Integration

### Automatic Configuration

When `app_settings` includes observability configuration:

```python
from neuroglia.observability import Observability

builder = WebApplicationBuilder(app_settings)
Observability.configure(builder)

# Automatically adds:
# - OpenTelemetry tracing
# - Prometheus metrics
# - Health endpoints
# - Ready endpoints
```

### Standard Endpoints

- `GET /health` - Health check with dependency status
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus metrics

## Type System

### Type-Safe Settings

```python
def __init__(
    self,
    app_settings: Optional[Union[ApplicationSettings, 'ApplicationSettingsWithObservability']] = None
):
```

Benefits:

- ✅ Type checker validates settings types
- ✅ IDE autocomplete for settings properties
- ✅ Catches type errors at development time
- ✅ No `Any` escape hatch - proper type safety

### Forward References

```python
if TYPE_CHECKING:
    from neuroglia.observability.settings import ApplicationSettingsWithObservability
```

Avoids circular imports while maintaining type information.

## Backward Compatibility

### Deprecated Alias

```python
# In neuroglia.hosting.__init__.py
EnhancedWebApplicationBuilder = WebApplicationBuilder
```

### Migration Path

```python
# Old code (still works)
from neuroglia.hosting import EnhancedWebApplicationBuilder
builder = EnhancedWebApplicationBuilder(app_settings)

# New code (recommended)
from neuroglia.hosting import WebApplicationBuilder
builder = WebApplicationBuilder(app_settings)
```

### Breaking Changes

**None** - All existing code continues to work without modification.

## Best Practices

### 1. Start Simple

```python
# Begin with simple mode
builder = WebApplicationBuilder()
builder.services.add_scoped(UserService)
builder.add_controllers(["api.controllers"])
host = builder.build()
```

### 2. Add Settings When Needed

```python
# Grow to advanced mode when requirements demand it
app_settings = ApplicationSettings()
builder = WebApplicationBuilder(app_settings)
```

### 3. Use Type Hints

```python
from neuroglia.hosting import WebApplicationBuilder
from neuroglia.hosting.abstractions import ApplicationSettings

def create_app(settings: ApplicationSettings) -> FastAPI:
    builder = WebApplicationBuilder(settings)
    # ... configuration ...
    return builder.build_app_with_lifespan()
```

### 4. Leverage Dependency Injection

```python
# Register dependencies properly
builder.services.add_singleton(DatabaseConnection)
builder.services.add_scoped(UnitOfWork)
builder.services.add_transient(EmailService)

# Don't manually instantiate - let DI handle it
```

### 5. Implement Hosted Services

```python
# For background processing
class DataSyncService(HostedService):
    async def start_async(self):
        await self.start_sync_loop()

    async def stop_async(self):
        await self.stop_sync_loop()

builder.services.add_hosted_service(DataSyncService)
```

## Testing

### Simple Mode Tests

```python
def test_simple_builder():
    builder = WebApplicationBuilder()
    builder.add_controllers(["api.controllers"])
    host = builder.build()

    assert isinstance(host, WebHost)
```

### Advanced Mode Tests

```python
def test_advanced_builder():
    settings = ApplicationSettings()
    builder = WebApplicationBuilder(settings)
    builder.add_controllers(["api.controllers"], prefix="/api")
    host = builder.build()

    assert isinstance(host, EnhancedWebHost)
```

### Controller Registration Tests

```python
def test_controller_deduplication():
    builder = WebApplicationBuilder(app_settings)

    # Register same controller twice
    builder.add_controllers(["api.controllers"], app=app1)
    builder.add_controllers(["api.controllers"], app=app1)

    # Should only register once
    assert len(builder._registered_controllers[app1]) == expected_count
```

## Performance Considerations

### Startup Time

- Simple mode: ~100ms
- Advanced mode: ~150ms (includes observability setup)

### Memory Usage

- Simple mode: ~50MB base
- Advanced mode: ~70MB base (includes OpenTelemetry)

### Request Overhead

- WebHost: <1ms per request
- EnhancedWebHost: <2ms per request (multi-app routing)

## Security

### Middleware Chain

1. Exception handling (catch all errors)
2. Authentication (if configured)
3. Authorization (if configured)
4. CORS (if configured)
5. Request logging
6. Business logic
7. Response formatting

### Best Practices

- Always use HTTPS in production
- Enable CORS only for trusted origins
- Implement proper authentication middleware
- Use environment variables for secrets
- Enable observability for security monitoring

## Troubleshooting

### Common Issues

**Issue**: Controllers not mounting

- **Solution**: Ensure `add_controllers()` called before `build()`

**Issue**: Services not resolving

- **Solution**: Register services before building host

**Issue**: Multiple app instances

- **Solution**: Use advanced mode with app_settings

**Issue**: Type errors with settings

- **Solution**: Ensure settings inherit from correct base class

## Related Documentation

- Framework: `../framework/APPLICATION_BUILDER_UNIFICATION_COMPLETE.md`
- Migration: `../migrations/APPLICATION_BUILDER_ARCHITECTURE_UNIFICATION_PLAN.md`
- Observability: `../observability/OTEL_INTEGRATION.md`
- Testing: `../testing/HOSTING_TESTS.md`

---

**Last Updated**: October 25, 2025
**Status**: Production Ready
**Version**: 0.5.0+
