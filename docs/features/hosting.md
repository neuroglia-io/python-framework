# Application Hosting

**Time to read: 15 minutes**

Neuroglia's hosting infrastructure provides **enterprise-grade application lifecycle management** for building production-ready microservices. The `WebApplicationBuilder` is the central component that handles configuration, dependency injection, and application startup.

## 🎯 What & Why

### What is Application Hosting?

Application hosting in Neuroglia manages the complete lifecycle of a web application:

- **Configuration**: Loading settings, environment variables
- **Dependency Injection**: Registering and resolving services
- **Controller Discovery**: Finding and mounting API controllers
- **Background Services**: Running tasks alongside the web server
- **Lifecycle Management**: Startup, running, graceful shutdown
- **Observability**: Health checks, metrics, tracing

### Why Use Neuroglia Hosting?

**Without Neuroglia Hosting**:

```python
# ❌ Manual setup - repetitive and error-prone
from fastapi import FastAPI
import uvicorn

app = FastAPI()

# Manually register each controller
from api.controllers.users import router as users_router
from api.controllers.orders import router as orders_router
app.include_router(users_router, prefix="/api/users")
app.include_router(orders_router, prefix="/api/orders")

# No DI - manual instantiation
database = Database(connection_string=os.getenv("DB_CONN"))
user_service = UserService(database)

# No lifecycle management
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**With Neuroglia Hosting**:

```python
# ✅ Clean, declarative, automatic
from neuroglia.hosting import WebApplicationBuilder

builder = WebApplicationBuilder()

# Auto-discover and register controllers
builder.add_controllers(["api.controllers"])

# DI handles instantiation
builder.services.add_scoped(Database)
builder.services.add_scoped(UserService)

# Built-in lifecycle management
app = builder.build()
app.run()
```

## 🚀 Getting Started

### Simple Mode (Basic Applications)

For straightforward applications with single API:

```python
from neuroglia.hosting import WebApplicationBuilder

def create_app():
    builder = WebApplicationBuilder()

    # Register services
    builder.services.add_scoped(OrderRepository)
    builder.services.add_scoped(OrderService)

    # Auto-discover controllers
    builder.add_controllers(["api.controllers"])

    # Build and return
    host = builder.build()
    return host

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000)
```

### Advanced Mode (Production Applications)

For production apps with observability, multi-app support:

```python
from neuroglia.hosting import WebApplicationBuilder
from neuroglia.hosting.abstractions import ApplicationSettings

def create_app():
    # Load configuration
    app_settings = ApplicationSettings()

    # Advanced features enabled automatically
    builder = WebApplicationBuilder(app_settings)

    # Register services
    builder.services.add_scoped(OrderRepository)
    builder.services.add_scoped(EmailService)

    # Multi-app support with prefixes
    builder.add_controllers(["api.controllers"], prefix="/api")
    builder.add_controllers(["admin.controllers"], prefix="/admin")

    # Add background services
    builder.services.add_hosted_service(CleanupService)

    # Build with lifecycle management
    app = builder.build_app_with_lifespan(
        title="Mario's Pizzeria API",
        version="1.0.0"
    )

    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🏗️ Core Components

### WebApplicationBuilder

The main builder for creating applications:

```python
from neuroglia.hosting import WebApplicationBuilder

# Simple mode
builder = WebApplicationBuilder()

# Advanced mode
from neuroglia.hosting.abstractions import ApplicationSettings
app_settings = ApplicationSettings()
builder = WebApplicationBuilder(app_settings)
```

**Key Properties**:

- `services`: ServiceCollection for DI registration
- `app`: The FastAPI application instance (after build)
- `app_settings`: Application configuration

**Key Methods**:

- `add_controllers(modules, prefix)`: Register controllers
- `build()`: Build host (returns WebHost or EnhancedWebHost)
- `build_app_with_lifespan(title, version)`: Build FastAPI app with lifecycle
- `use_controllers()`: Mount controllers on app

### Controller Registration

Automatically discover and register controllers:

```python
# Single module
builder.add_controllers(["api.controllers"])

# Multiple modules
builder.add_controllers([
    "api.controllers.orders",
    "api.controllers.customers",
    "api.controllers.menu"
])

# With custom prefix
builder.add_controllers(["api.controllers"], prefix="/api/v1")

# Multiple apps with different prefixes
builder.add_controllers(["api.controllers"], prefix="/api")
builder.add_controllers(["admin.controllers"], prefix="/admin")
```

### Hosted Services

Background services that run alongside your application:

```python
from neuroglia.hosting.abstractions import HostedService

class CleanupService(HostedService):
    """Background service for cleanup tasks."""

    async def start_async(self):
        """Called on application startup."""
        self.running = True
        while self.running:
            await self.cleanup_old_orders()
            await asyncio.sleep(3600)  # Run every hour

    async def stop_async(self):
        """Called on application shutdown."""
        self.running = False

    async def cleanup_old_orders(self):
        # Cleanup logic
        pass

# Register hosted service
builder.services.add_hosted_service(CleanupService)
```

### Application Settings

Configuration management:

```python
from neuroglia.hosting.abstractions import ApplicationSettings
from pydantic import Field

class MyAppSettings(ApplicationSettings):
    """Custom application settings."""

    database_url: str = Field(default="mongodb://localhost:27017")
    redis_url: str = Field(default="redis://localhost:6379")
    api_key: str = Field(default="", env="API_KEY")
    debug: bool = Field(default=False)

# Load settings (from environment variables)
app_settings = MyAppSettings()

# Use in builder
builder = WebApplicationBuilder(app_settings)

# Access in services via DI
class OrderService:
    def __init__(self, settings: MyAppSettings):
        self.db_url = settings.database_url
```

## 💡 Real-World Example: Mario's Pizzeria

Complete application setup:

```python
from neuroglia.hosting import WebApplicationBuilder
from neuroglia.hosting.abstractions import ApplicationSettings
from neuroglia.dependency_injection import ServiceLifetime
from application.settings import PizzeriaSettings

def create_app():
    # Load configuration
    settings = PizzeriaSettings()

    # Create builder with settings
    builder = WebApplicationBuilder(settings)

    # Register domain repositories
    builder.services.add_scoped(IOrderRepository, MongoOrderRepository)
    builder.services.add_scoped(ICustomerRepository, MongoCustomerRepository)
    builder.services.add_scoped(IMenuRepository, MongoMenuRepository)

    # Register application services
    builder.services.add_scoped(OrderService)
    builder.services.add_scoped(CustomerService)

    # Register infrastructure
    builder.services.add_singleton(EmailService)
    builder.services.add_singleton(PaymentService)

    # Configure core services
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos"])

    # Add SubApp with controllers
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            controllers=[
                "api.controllers.orders",
                "api.controllers.customers",
                "api.controllers.menu"
            ]
        )
    )

    # Add background services
    builder.services.add_hosted_service(OrderCleanupService)
    builder.services.add_hosted_service(MetricsCollectorService)

    # Build application with lifecycle management
    app = builder.build_app_with_lifespan(
        title="Mario's Pizzeria API",
        version="1.0.0",
        description="Pizza ordering and management system"
    )

    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
```

## 🔧 Advanced Features

### Multi-Application Architecture

Host multiple FastAPI applications in one process:

```python
from neuroglia.hosting import WebApplicationBuilder
from fastapi import FastAPI

# Create builder with settings
builder = WebApplicationBuilder(app_settings)

# Create custom sub-applications
api_app = FastAPI(title="Public API")
admin_app = FastAPI(title="Admin Panel")

# Register controllers to specific apps
builder.add_controllers(
    ["api.controllers"],
    app=api_app,
    prefix="/api"
)

builder.add_controllers(
    ["admin.controllers"],
    app=admin_app,
    prefix="/admin"
)

# Build host that manages both apps
host = builder.build()
# host.app has both /api and /admin mounted
```

### Exception Handling

Global exception handling middleware:

```python
from neuroglia.hosting.web import ExceptionHandlingMiddleware

# Automatically included in WebApplicationBuilder
# Catches exceptions and formats responses

# Custom error handling
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }
```

### Lifecycle Hooks

React to application lifecycle events:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Application starting...")
    await database.connect()

    yield  # Application running

    # Shutdown
    print("Application shutting down...")
    await database.disconnect()

# Use in build
app = builder.build_app_with_lifespan(
    title="My App",
    lifespan=lifespan
)
```

## 🧪 Testing

### Testing with Builder

```python
import pytest
from neuroglia.hosting import WebApplicationBuilder

@pytest.fixture
def test_app():
    """Create test application."""
    builder = WebApplicationBuilder()

    # Use in-memory implementations
    builder.services.add_scoped(IOrderRepository, InMemoryOrderRepository)

    builder.add_controllers(["api.controllers"])

    app = builder.build_app_with_lifespan(title="Test App")
    return app

async def test_create_order(test_app):
    """Test order creation endpoint."""
    from fastapi.testclient import TestClient

    client = TestClient(test_app)
    response = client.post("/api/orders", json={
        "customer_id": "123",
        "items": [{"pizza": "Margherita", "quantity": 1}]
    })

    assert response.status_code == 201
    assert "order_id" in response.json()
```

## ⚠️ Common Mistakes

### 1. Not Building the App

```python
# ❌ WRONG: Forgot to build
builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])
# Missing: app = builder.build()

# ✅ RIGHT: Build before running
builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])
app = builder.build()
app.run()
```

### 2. Registering Controllers After Build

```python
# ❌ WRONG: Adding controllers after build
builder = WebApplicationBuilder()
app = builder.build()
builder.add_controllers(["api.controllers"])  # Too late!

# ✅ RIGHT: Register before build
builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])
app = builder.build()
```

### 3. Mixing Simple and Advanced Features

```python
# ❌ WRONG: Using advanced features without app_settings
builder = WebApplicationBuilder()  # Simple mode
builder.add_controllers(["api.controllers"], prefix="/api")
builder.add_controllers(["admin.controllers"], prefix="/admin")
# Advanced features may not work properly

# ✅ RIGHT: Use app_settings for advanced features
app_settings = ApplicationSettings()
builder = WebApplicationBuilder(app_settings)  # Advanced mode
builder.add_controllers(["api.controllers"], prefix="/api")
builder.add_controllers(["admin.controllers"], prefix="/admin")
```

## 🚫 When NOT to Use

Skip Neuroglia hosting when:

1. **Serverless Functions**: AWS Lambda, Azure Functions (stateless)
2. **Minimal APIs**: Single endpoint, no DI needed
3. **Non-Web Applications**: CLI tools, batch jobs
4. **Existing FastAPI App**: Already have complex setup

For these cases, use FastAPI directly or other appropriate tools.

## 📝 Key Takeaways

1. **WebApplicationBuilder**: Central component for app configuration
2. **Two Modes**: Simple (basic) and Advanced (production features)
3. **Auto-Discovery**: Controllers automatically found and registered
4. **Lifecycle Management**: Startup, running, graceful shutdown
5. **Background Services**: HostedService for concurrent tasks
6. **Dependency Injection**: Integrated ServiceCollection

## 🔗 Related Documentation

- [Getting Started](../getting-started.md) - Basic usage
- [Tutorial Part 1](../tutorials/mario-pizzeria-01-setup.md) - Complete setup guide
- [Dependency Injection](../patterns/dependency-injection.md) - Service registration
- [MVC Controllers](mvc-controllers.md) - Building controllers
- [Observability](observability.md) - Monitoring and tracing

## 📚 API Reference

### WebApplicationBuilder

```python
class WebApplicationBuilder:
    def __init__(
        self,
        app_settings: Optional[Union[ApplicationSettings, ApplicationSettingsWithObservability]] = None
    ):
        """Initialize builder with optional settings."""

    @property
    def services(self) -> ServiceCollection:
        """Get the service collection for DI registration."""

    @property
    def app(self) -> Optional[FastAPI]:
        """Get the FastAPI app instance (after build)."""

    @property
    def app_settings(self) -> Optional[ApplicationSettings]:
        """Get the application settings."""

    def add_controllers(
        self,
        modules: List[str],
        app: Optional[FastAPI] = None,
        prefix: str = ""
    ) -> ServiceCollection:
        """Register controllers from specified modules."""

    def build(self, auto_mount_controllers: bool = True) -> WebHostBase:
        """Build the host."""

    def build_app_with_lifespan(
        self,
        title: str = "Neuroglia Application",
        version: str = "1.0.0",
        description: str = "",
        lifespan: Optional[Callable] = None
    ) -> FastAPI:
        """Build FastAPI app with lifecycle management."""

    def use_controllers(self):
        """Mount controllers on the application."""
```

### HostedService

```python
class HostedService(ABC):
    """Base class for background services."""

    @abstractmethod
    async def start_async(self):
        """Called on application startup."""

    @abstractmethod
    async def stop_async(self):
        """Called on application shutdown."""
```

### ApplicationSettings

```python
class ApplicationSettings:
    """Base application configuration."""

    # Override with Pydantic Fields
    app_name: str = "My Application"
    environment: str = "development"
    debug: bool = False
```

---

**Next:** [Observability →](observability.md)
