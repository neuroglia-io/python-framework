# 🤖 AI Agent Quick Reference Guide

**Fast-track guide for AI agents to understand and work with the Neuroglia Python Framework**

!!! warning "Read This First"

    Before using this guide, review the **[Documentation Philosophy](documentation-philosophy.md)** to understand how to interpret patterns, evaluate trade-offs, and adapt examples to specific contexts. This is a toolbox, not a rulebook.

---

## 🎯 Framework Overview

**Neuroglia** is a clean architecture Python framework built on FastAPI that enforces separation of concerns, CQRS, dependency injection, and event-driven patterns for maintainable microservices.

### 🏗️ Core Architecture

```
src/
├── api/           # 🌐 Controllers, DTOs, Routes (FastAPI)
├── application/   # 💼 Commands, Queries, Handlers, Services
├── domain/        # 🏛️ Entities, Value Objects, Business Rules
└── integration/   # 🔌 Repositories, External APIs, Infrastructure
```

**Dependency Rule**: `API → Application → Domain ← Integration`

---

## ⚡ Quick Start Patterns

### 1. CQRS Command/Query Pattern

```python
# Commands (Write operations)
@dataclass
class CreateOrderCommand(Command[Order]):
    customer_id: str
    items: List[OrderItemDto]

class CreateOrderHandler(CommandHandler[CreateOrderCommand, Order]):
    async def handle_async(self, command: CreateOrderCommand) -> Order:
        # Business logic here
        return order

# Queries (Read operations)
@dataclass
class GetOrderQuery(Query[Optional[Order]]):
    order_id: str

class GetOrderHandler(QueryHandler[GetOrderQuery, Optional[Order]]):
    async def handle_async(self, query: GetOrderQuery) -> Optional[Order]:
        return await self.repository.get_by_id_async(query.order_id)
```

### 2. API Controllers (FastAPI Integration)

```python
from neuroglia.mvc import ControllerBase
from classy_fastapi.decorators import get, post

class OrdersController(ControllerBase):
    @post("/", response_model=OrderDto, status_code=201)
    async def create_order(self, dto: CreateOrderDto) -> OrderDto:
        command = self.mapper.map(dto, CreateOrderCommand)
        order = await self.mediator.execute_async(command)
        return self.mapper.map(order, OrderDto)

    @get("/{order_id}", response_model=OrderDto)
    async def get_order(self, order_id: str) -> OrderDto:
        query = GetOrderQuery(order_id=order_id)
        order = await self.mediator.execute_async(query)
        return self.mapper.map(order, OrderDto)
```

### 3. Repository Pattern

```python
# Abstract repository
class OrderRepository(Repository[Order, str]):
    async def get_by_customer_async(self, customer_id: str) -> List[Order]:
        pass

# MongoDB implementation
class MongoOrderRepository(MongoRepository[Order, str]):
    async def get_by_customer_async(self, customer_id: str) -> List[Order]:
        cursor = self.collection.find({"customer_id": customer_id})
        return [self._to_entity(doc) async for doc in cursor]
```

### 4. Dependency Injection & Application Setup

```python
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper

def create_app():
    builder = WebApplicationBuilder()

    # Configure core services
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos", "domain.entities"])

    # Register custom services
    builder.services.add_scoped(OrderRepository, MongoOrderRepository)

    # Add SubApp with controllers
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            controllers=["api.controllers"]
        )
    )

    app = builder.build()
    return app
```

### 5. Observability with OpenTelemetry

```python
from neuroglia.observability import configure_opentelemetry, get_tracer, trace_async

# Configure OpenTelemetry (in main.py)
configure_opentelemetry(
    service_name="mario-pizzeria",
    service_version="1.0.0",
    otlp_endpoint="http://localhost:4317"
)

# Use in handlers
tracer = get_tracer(__name__)

class PlaceOrderHandler(CommandHandler):
    @trace_async(name="place_order")
    async def handle_async(self, command: PlaceOrderCommand):
        with tracer.start_as_current_span("validate_order"):
            # Business logic with automatic tracing
            pass
```

### 6. Role-Based Access Control (RBAC)

```python
from fastapi import Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

class OrdersController(ControllerBase):
    @post("/", response_model=OrderDto)
    async def create_order(
        self,
        dto: CreateOrderDto,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> OrderDto:
        # Extract user info from JWT
        user_info = self._decode_jwt(credentials.credentials)

        # Pass to handler for RBAC check
        command = CreateOrderCommand(
            customer_id=dto.customer_id,
            items=dto.items,
            user_info=user_info  # Handler checks roles/permissions
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

# RBAC in handler (application layer)
class CreateOrderHandler(CommandHandler):
    async def handle_async(self, command: CreateOrderCommand):
        # Authorization check based on roles
        if "customer" not in command.user_info.get("roles", []):
            return self.forbidden("Insufficient permissions")

        # Business logic
        order = Order(command.customer_id, command.items)
        await self.repository.save_async(order)
        return self.created(order)
```

---

## 🧩 Framework Modules Reference

| Module                                | Purpose                   | Key Classes                                                                |
| ------------------------------------- | ------------------------- | -------------------------------------------------------------------------- |
| **`neuroglia.core`**                  | Base types, utilities     | `OperationResult`, `Entity`, `ValueObject`                                 |
| **`neuroglia.dependency_injection`**  | DI container              | `ServiceCollection`, `ServiceProvider`, `ServiceLifetime`                  |
| **`neuroglia.mediation`**             | CQRS patterns             | `Mediator`, `Command`, `Query`, `CommandHandler`, `QueryHandler`           |
| **`neuroglia.mvc`**                   | FastAPI controllers       | `ControllerBase`, auto-discovery                                           |
| **`neuroglia.data`**                  | Repository & persistence  | `Repository`, `MongoRepository`, `InMemoryRepository`, `EventStore`        |
| **`neuroglia.data.resources`**        | Resource management       | `ResourceController`, `ResourceWatcher`, `Reconciler`                      |
| **`neuroglia.eventing`**              | Event handling            | `DomainEvent`, `EventHandler`, `EventBus`                                  |
| **`neuroglia.eventing.cloud_events`** | CloudEvents integration   | `CloudEvent`, `CloudEventPublisher`, `CloudEventIngestor`                  |
| **`neuroglia.mapping`**               | Object mapping            | `Mapper`, convention-based mapping                                         |
| **`neuroglia.hosting`**               | App lifecycle             | `WebApplicationBuilder`, `WebApplication`, `HostedService`                 |
| **`neuroglia.serialization`**         | JSON/data serialization   | `JsonSerializer`, `JsonEncoder`, `TypeRegistry`                            |
| **`neuroglia.validation`**            | Business rule validation  | `BusinessRule`, `ValidationResult`, `PropertyValidator`, `EntityValidator` |
| **`neuroglia.reactive`**              | Reactive programming      | `Observable`, `Observer` (RxPy integration)                                |
| **`neuroglia.integration`**           | External services         | `HttpServiceClient`, `CacheRepository`, `BackgroundTaskScheduler`          |
| **`neuroglia.utils`**                 | Utility functions         | `CaseConversion`, `CamelModel`, `TypeFinder`                               |
| **`neuroglia.expressions`**           | Expression evaluation     | `JavaScriptExpressionTranslator`                                           |
| **`neuroglia.observability`**         | OpenTelemetry integration | Tracing, metrics, logging with OTLP exporters                              |

---

## 📁 Sample Applications

The framework includes complete sample applications that demonstrate real-world usage:

### 🍕 Mario's Pizzeria (`samples/mario-pizzeria/`)

- **Full CQRS implementation** with sophisticated domain models
- **MongoDB repositories** for orders, customers, pizzas
- **Event-driven architecture** with domain events
- **Complete API** with OpenAPI documentation
- **OpenTelemetry observability** with distributed tracing, metrics, and logging

**Key Files:**

- `domain/entities/`: `Order`, `Pizza`, `Customer` with business logic
- `application/commands/`: `PlaceOrderCommand`, `CreatePizzaCommand`
- `application/queries/`: `GetOrderByIdQuery`, `GetMenuItemsQuery`
- `api/controllers/`: `OrdersController`, `MenuController`

### 🏦 OpenBank (`samples/openbank/`)

- **Event sourcing** with KurrentDB (EventStoreDB)
- **CQRS with separate read/write models**
- **Complex domain modeling** (accounts, transactions, persons)
- **Banking business rules** and validation
- **Read model projections** and eventual consistency
- **Snapshot strategies** for performance

### 🎨 Simple UI (`samples/simple-ui/`)

- **SubApp pattern** for UI/API separation
- **Stateless JWT authentication** without server-side sessions
- **Role-Based Access Control (RBAC)** at query/command level
- **Bootstrap 5 frontend** with Parcel bundler
- **Clean separation** of concerns between UI and API

### 🎛️ Desktop Controller (`samples/desktop-controller/`)

- **Background services** and scheduled tasks
- **System integration** patterns
- **Resource management** examples

### 🧪 Lab Resource Manager (`samples/lab-resource-manager/`)

- **Resource-Oriented Architecture** (ROA)
- **Watcher/Controller patterns** (like Kubernetes operators)
- **Reconciliation loops** for resource management

### 🌐 API Gateway (`samples/api-gateway/`)

- **Microservice gateway** patterns
- **AI/ML integration** examples
- **Service orchestration** and routing
- **Background task processing** with Redis

---

## 🔍 Where to Find Information

### 📚 Documentation Structure (`docs/`)

| Section                  | Purpose                | Key Files                                |
| ------------------------ | ---------------------- | ---------------------------------------- |
| **`getting-started.md`** | Framework introduction | Quick start, core concepts               |
| **`features/`**          | Feature documentation  | One file per major feature               |
| **`patterns/`**          | Architecture patterns  | CQRS, Clean Architecture, Event Sourcing |
| **`samples/`**           | Sample walkthroughs    | Detailed sample explanations             |
| **`references/`**        | Technical references   | Python best practices, 12-Factor App     |
| **`guides/`**            | Step-by-step tutorials | Mario's Pizzeria tutorial                |

### 🎯 Key Documentation Files

- **[Getting Started](getting-started.md)** - Framework overview and quick start
- **[Mario's Pizzeria Tutorial](guides/mario-pizzeria-tutorial.md)** - Complete walkthrough
- **[CQRS & Mediation](patterns/cqrs.md)** - Command/Query patterns
- **[MVC Controllers](features/mvc-controllers.md)** - FastAPI controller patterns
- **[Data Access](features/data-access.md)** - Repository and persistence
- **[Dependency Injection](patterns/dependency-injection.md)** - DI container usage
- **[Observability](features/observability.md)** - OpenTelemetry tracing, metrics, logging
- **[RBAC & Authorization](guides/rbac-authorization.md)** - Role-based access control patterns
- **[OpenTelemetry Integration](guides/opentelemetry-integration.md)** - Infrastructure setup guide
- **[Python Typing Guide](references/python_typing_guide.md)** - Type hints & generics

### 📖 Additional Resources

- **`README.md`** - Project overview and installation
- **`pyproject.toml`** - Dependencies and build configuration
- **`src/neuroglia/`** - Complete framework source code
- **`tests/`** - Comprehensive test suite with examples

---

## 💡 Common Patterns & Best Practices

### ✅ Do This

```python
# ✅ Use constructor injection
class OrderService:
    def __init__(self, repository: OrderRepository, event_bus: EventBus):
        self.repository = repository
        self.event_bus = event_bus

# ✅ Separate commands and queries
class PlaceOrderCommand(Command[Order]): pass
class GetOrderQuery(Query[Optional[Order]]): pass

# ✅ Use domain events
class Order(Entity):
    def place_order(self):
        # Business logic
        self.raise_event(OrderPlacedEvent(order_id=self.id))

# ✅ Type hints everywhere
async def handle_async(self, command: PlaceOrderCommand) -> Order:
    return order
```

### ❌ Avoid This

```python
# ❌ Direct database access in controllers
class OrderController:
    def create_order(self):
        # Don't access database directly
        connection.execute("INSERT INTO...")

# ❌ Mixing concerns
class OrderHandler:
    def handle(self, command):
        # Don't mix business logic with infrastructure
        send_email()  # Infrastructure concern

# ❌ Missing type hints
def process_order(order):  # What type is order?
    return result  # What type is result?
```

---

## 🚀 Quick Commands

```bash
# Install framework (when available)
pip install neuroglia

# Run sample applications
cd samples/mario-pizzeria && python main.py
cd samples/openbank && python main.py

# Run tests
pytest tests/

# Generate documentation
mkdocs serve

# CLI tool (when available)
pyneuroctl --help
pyneuroctl samples list
pyneuroctl new myapp --template minimal
```

---

## 🎯 For AI Agents: Key Takeaways

1. **Architecture**: Clean Architecture with strict dependency rules
2. **Patterns**: CQRS, DI, Repository, Domain Events are core
3. **Code Style**: Heavy use of type hints, dataclasses, async/await
4. **Framework Integration**: Built on FastAPI, uses Pydantic extensively
5. **Sample Code**: Always reference `samples/mario-pizzeria/` for real examples
6. **Documentation**: Comprehensive docs in `docs/` with practical examples
7. **Testing**: Full test coverage with patterns for all architectural layers
8. **Observability**: OpenTelemetry integration for distributed tracing, metrics, and logging
9. **Security**: RBAC patterns with JWT authentication at application layer
10. **Event Sourcing**: Full support with KurrentDB (EventStoreDB) in OpenBank sample

**When writing Neuroglia code:**

- Follow the layered architecture strictly
- Use CQRS for all business operations
- Leverage dependency injection throughout
- Include comprehensive type hints
- Reference Mario's Pizzeria sample for patterns
- Maintain separation of concerns between layers
- Implement observability with OpenTelemetry decorators
- Handle authorization in handlers (application layer), not controllers
- Use SubApp pattern for clean UI/API separation

## 🤖 Quick Framework Setup for AI Agents

```python
# Minimal Neuroglia application setup
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper

def create_app():
    builder = WebApplicationBuilder()

    # Configure essential services
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos"])

    # Add SubApp with controllers
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            controllers=["api.controllers"]
        )
    )

    # Build application
    app = builder.build()
    return app

if __name__ == "__main__":
    app = create_app()
    app.run()
```

**Need more detail?** Start with [Getting Started](getting-started.md) then dive into specific [feature documentation](features/index.md) or explore the [Mario's Pizzeria sample](mario-pizzeria.md).
