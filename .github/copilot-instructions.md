# GitHub Copilot Instructions for Neuroglia Python Framework

## Framework Overview

Neuroglia is a lightweight, opinionated Python framework built on FastAPI that enforces clean architecture
principles and provides comprehensive tooling for building maintainable microservices. The framework emphasizes
CQRS, event-driven architecture, dependency injection, and domain-driven design patterns.

## Architecture Layers

The framework follows a strict layered architecture with clear separation of concerns:

```
src/
├── api/           # 🌐 API Layer (Controllers, DTOs, Routes)
├── application/   # 💼 Application Layer (Commands, Queries, Handlers, Services)
├── domain/        # 🏛️ Domain Layer (Entities, Value Objects, Business Rules)
└── integration/   # 🔌 Integration Layer (External APIs, Repositories, Infrastructure)
```

**Dependency Rule**: Dependencies only point inward (API → Application → Domain ← Integration)

## Core Framework Modules

### `neuroglia.core`

- **OperationResult**: Standardized result pattern for operations with success/failure states
- **ProblemDetails**: RFC 7807 problem details for API error responses
- **TypeFinder**: Dynamic type discovery and reflection utilities
- **TypeRegistry**: Type caching and registration
- **ModuleLoader**: Dynamic module loading capabilities

### `neuroglia.dependency_injection`

- **ServiceCollection**: Container for service registrations
- **ServiceProvider**: Service resolution and lifetime management
- **ServiceLifetime**: Singleton, Scoped, Transient lifetimes
- **ServiceDescriptor**: Service registration metadata

### `neuroglia.mediation`

- **Mediator**: Central message dispatcher for CQRS
- **Command/Query**: Request types for write/read operations
- **CommandHandler/QueryHandler**: Request processors
- **PipelineBehavior**: Cross-cutting concerns (validation, logging, etc.)

### `neuroglia.mvc`

- **ControllerBase**: Base class for all API controllers
- **Automatic Discovery**: Controllers are auto-registered
- **FastAPI Integration**: Full compatibility with FastAPI decorators

### `neuroglia.data`

- **Entity/AggregateRoot**: Domain model base classes
- **DomainEvent**: Business events from domain entities
- **Repository/QueryableRepository**: Abstract data access patterns
- **FlexibleRepository**: Repository with flexible querying capabilities
- **Queryable/QueryProvider**: LINQ-style query composition
- **VersionedState/AggregateState**: State management for aggregates

### `neuroglia.data.resources`

- **Resource**: Kubernetes-style resource abstraction
- **ResourceController**: Reconciliation-based resource management
- **ResourceWatcher**: Resource change observation
- **StateMachine**: Declarative state machine engine
- **ResourceSpec/ResourceStatus**: Resource specifications and status

### `neuroglia.eventing`

- **DomainEvent**: Business events from domain entities
- **EventHandler**: Event processing logic
- **EventBus**: Event publishing and subscription

### `neuroglia.eventing.cloud_events`

- **CloudEvent**: CloudEvents v1.0 specification implementation
- **CloudEventPublisher**: Event publishing infrastructure
- **CloudEventBus**: In-memory cloud event bus
- **CloudEventIngestor**: Event ingestion from external sources
- **CloudEventMiddleware**: FastAPI middleware for cloud event handling

### `neuroglia.mapping`

- **Mapper**: Object-to-object transformations
- **AutoMapper**: Convention-based mapping

### `neuroglia.hosting`

- **WebApplicationBuilder**: Application bootstrapping
- **HostedService**: Background services
- **ApplicationLifetime**: Startup/shutdown management

### `neuroglia.application`

- **BackgroundTaskScheduler**: Distributed task processing with Redis backend

### `neuroglia.serialization`

- **JsonSerializer**: JSON serialization with type handling
- **JsonEncoder**: Custom type encoders (enums, decimals, datetime)
- **TypeRegistry**: Type discovery and caching
- **Automatic Conversion**: Built-in support for common Python types

### `neuroglia.validation`

- **BusinessRule**: Fluent business rule validation
- **ValidationResult**: Comprehensive error reporting
- **PropertyValidator**: Field-level validation
- **EntityValidator**: Object-level validation
- **Decorators**: Method parameter validation support

### `neuroglia.reactive`

- **Observable**: RxPy integration for reactive patterns
- **Observer**: Event stream processing
- **Reactive Pipelines**: Async data transformation

### `neuroglia.expressions`

- **JavaScriptExpressionTranslator**: JS expression evaluation
- **Dynamic Expressions**: Runtime expression parsing

### `neuroglia.utils`

- **CaseConversion**: snake_case ↔ camelCase ↔ PascalCase transformations
- **CamelModel**: Pydantic base class with automatic case conversion
- **TypeFinder**: Dynamic type discovery utilities

### `neuroglia.integration`

- **HttpServiceClient**: Resilient HTTP client with circuit breakers and retry policies
- **AsyncCacheRepository**: Redis-based distributed caching layer
- **Request/Response Interceptors**: Middleware for authentication, logging, and monitoring
- **Integration Events**: Standardized events for external system integration

### `neuroglia.observability`

- **OpenTelemetry Integration**: Comprehensive tracing, metrics, and logging
- **TracerProvider/MeterProvider**: OTLP exporters with resource detection
- **Context Propagation**: Distributed tracing across service boundaries
- **Automatic Instrumentation**: FastAPI, HTTPX, and logging integration
- **Decorators**: Manual instrumentation helpers (@trace_async, @trace_sync)

## Key Patterns and Conventions

### 1. Dependency Injection Pattern

Always use constructor injection in controllers and services:

```python
class UserController(ControllerBase):
    def __init__(self,
                 service_provider: ServiceProviderBase,
                 mapper: Mapper,
                 mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
```

**Service Registration:**

```python
# In startup configuration
services.add_scoped(UserService)  # Per-request lifetime
services.add_singleton(CacheService)  # Application lifetime
services.add_transient(EmailService)  # New instance per resolve
```

### 2. CQRS with Mediator Pattern

Separate commands (write) from queries (read).

**IMPORTANT**: All handlers inherit 12 helper methods from `RequestHandler`:

- Success: `ok()`, `created()`, `accepted()`, `no_content()`
- Client Errors: `bad_request()`, `unauthorized()`, `forbidden()`, `not_found()`, `conflict()`, `unprocessable_entity()`
- Server Errors: `internal_server_error()`, `service_unavailable()`

**Always use helper methods** - never construct `OperationResult` manually.

```python
# Command (Write Operation)
@dataclass
class CreateUserCommand(Command[OperationResult[UserDto]]):
    email: str
    first_name: str
    last_name: str

class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
    async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
        # Validation → use self.bad_request()
        if not command.email:
            return self.bad_request("Email is required")

        # Business logic
        user = User(command.email, command.first_name, command.last_name)
        await self.user_repository.save_async(user)

        # Success → use self.created()
        return self.created(self.mapper.map(user, UserDto))

# Query (Read Operation)
@dataclass
class GetUserByIdQuery(Query[UserDto]):
    user_id: str

class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, UserDto]):
    async def handle_async(self, query: GetUserByIdQuery) -> UserDto:
        user = await self.user_repository.get_by_id_async(query.user_id)
        return self.mapper.map(user, UserDto)
```

### 3. Controller Implementation

Controllers should be thin and delegate to mediator:

```python
from classy_fastapi.decorators import get, post, put, delete

class UsersController(ControllerBase):

    @get("/{user_id}", response_model=UserDto)
    async def get_user(self, user_id: str) -> UserDto:
        query = GetUserByIdQuery(user_id=user_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/", response_model=UserDto, status_code=201)
    async def create_user(self, create_user_dto: CreateUserDto) -> UserDto:
        command = self.mapper.map(create_user_dto, CreateUserCommand)
        result = await self.mediator.execute_async(command)
        return self.process(result)
```

### 4. Repository Pattern

Abstract data access behind interfaces:

```python
class UserRepository(Repository[User, str]):
    async def get_by_email_async(self, email: str) -> Optional[User]:
        # Implementation specific to storage type
        pass

    async def save_async(self, user: User) -> None:
        # Implementation specific to storage type
        pass
```

### 5. Domain Events

Domain entities should raise events for important business occurrences:

```python
class User(Entity):
    def __init__(self, email: str, first_name: str, last_name: str):
        super().__init__()
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

        # Raise domain event
        self.raise_event(UserCreatedEvent(
            user_id=self.id,
            email=self.email
        ))

@dataclass
class UserCreatedEvent(DomainEvent):
    user_id: str
    email: str

class SendWelcomeEmailHandler(EventHandler[UserCreatedEvent]):
    async def handle_async(self, event: UserCreatedEvent):
        await self.email_service.send_welcome_email(event.email)
```

### 6. Application Startup

Bootstrap applications using WebApplicationBuilder:

```python
from neuroglia.hosting.web import WebApplicationBuilder

def create_app():
    builder = WebApplicationBuilder()

    # Configure services
    services = builder.services
    services.add_scoped(UserService)
    services.add_scoped(UserRepository)
    services.add_mediator()
    services.add_controllers(["api.controllers"])

    # Build and configure app
    app = builder.build()
    app.use_controllers()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run()
```

## File and Module Naming Conventions

### Project Structure

```
src/
└── myapp/
    ├── api/
    │   ├── controllers/
    │   │   ├── users_controller.py
    │   │   └── orders_controller.py
    │   └── dtos/
    │       ├── user_dto.py
    │       └── create_user_dto.py
    ├── application/
    │   ├── commands/
    │   │   └── create_user_command.py
    │   ├── queries/
    │   │   └── get_user_query.py
    │   ├── handlers/
    │   │   ├── create_user_handler.py
    │   │   └── get_user_handler.py
    │   └── services/
    │       └── user_service.py
    ├── domain/
    │   ├── entities/
    │   │   └── user.py
    │   ├── events/
    │   │   └── user_events.py
    │   └── repositories/
    │       └── user_repository.py
    └── integration/
        ├── repositories/
        │   └── mongo_user_repository.py
        └── services/
            └── email_service.py
```

### Naming Patterns

- **Controllers**: `{Entity}Controller` (e.g., `UsersController`)
- **Commands**: `{Action}{Entity}Command` (e.g., `CreateUserCommand`)
- **Queries**: `{Action}{Entity}Query` (e.g., `GetUserByIdQuery`)
- **Handlers**: `{Command/Query}Handler` (e.g., `CreateUserHandler`)
- **DTOs**: `{Purpose}Dto` (e.g., `UserDto`, `CreateUserDto`)
- **Events**: `{Entity}{Action}Event` (e.g., `UserCreatedEvent`)
- **Repositories**: `{Entity}Repository` (e.g., `UserRepository`)

## Import Patterns

Always import from specific modules to maintain clear dependencies:

```python
# Core Framework
from neuroglia.core import OperationResult, ProblemDetails, TypeFinder, TypeRegistry
from neuroglia.dependency_injection import ServiceCollection, ServiceProvider, ServiceLifetime
from neuroglia.mediation import Mediator, Command, Query, CommandHandler, QueryHandler
from neuroglia.mvc import ControllerBase
from neuroglia.hosting.web import WebApplicationBuilder

# Data Access & Repositories
from neuroglia.data import (
    Entity, AggregateRoot, DomainEvent,
    Repository, QueryableRepository, FlexibleRepository,
    Queryable, QueryProvider,
    VersionedState, AggregateState
)

# Resource-Oriented Architecture
from neuroglia.data.resources import (
    Resource, ResourceController, ResourceWatcher,
    StateMachine, ResourceSpec, ResourceStatus
)

# Eventing
from neuroglia.eventing import DomainEvent, EventHandler, EventBus

# CloudEvents
from neuroglia.eventing.cloud_events import (
    CloudEvent, CloudEventPublisher, CloudEventBus,
    CloudEventIngestor, CloudEventMiddleware
)

# Integration & Background Services
from neuroglia.integration import (
    HttpServiceClient, HttpRequestOptions,
    AsyncCacheRepository, CacheRepositoryOptions
)
from neuroglia.application import BackgroundTaskScheduler

# Serialization & Mapping
from neuroglia.serialization import JsonSerializer, JsonEncoder
from neuroglia.mapping import Mapper

# Validation & Utilities
from neuroglia.validation import BusinessRule, ValidationResult, PropertyValidator, EntityValidator
from neuroglia.utils import CaseConversion, CamelModel, TypeFinder
from neuroglia.reactive import Observable, Observer

# Observability (OpenTelemetry)
from neuroglia.observability import (
    configure_opentelemetry, get_tracer, get_meter,
    trace_async, trace_sync,
    instrument_fastapi_app
)

# Avoid
from neuroglia import *
```

## Advanced Framework Patterns

### 7. Resource-Oriented Architecture (ROA)

Implement resource controllers and watchers for Kubernetes-style resource management:

```python
from neuroglia.data.resources import (
    ResourceControllerBase, ResourceWatcherBase,
    Resource, ResourceSpec, ResourceStatus
)

class LabInstanceSpec(ResourceSpec):
    desired_state: str
    configuration: dict

class LabInstanceStatus(ResourceStatus):
    current_state: str
    ready: bool

class LabInstance(Resource[LabInstanceSpec, LabInstanceStatus]):
    pass

class LabResourceController(ResourceControllerBase[LabInstance]):
    async def reconcile_async(self, resource: LabInstance) -> None:
        # Handle resource state reconciliation
        if resource.spec.desired_state == "running":
            await self.provision_lab_instance(resource)
        elif resource.spec.desired_state == "stopped":
            await self.cleanup_lab_instance(resource)

class LabInstanceWatcher(ResourceWatcherBase[LabInstance]):
    async def handle_async(self, event: ResourceChangeEvent[LabInstance]) -> None:
        # React to resource changes
        await self.controller.reconcile_async(event.resource)
```

### 8. Advanced Validation with Business Rules

Use fluent validation APIs for complex domain validation:

```python
from neuroglia.validation import BusinessRule, ValidationResult

class OrderValidator:
    async def validate_order(self, order: CreateOrderCommand) -> ValidationResult:
        return await BusinessRule.evaluate_async([
            BusinessRule.for_property(order.customer_id)
                .required()
                .must_exist_in_repository(self.customer_repository),

            BusinessRule.for_property(order.items)
                .not_empty()
                .each_item_must(self.validate_order_item),

            BusinessRule.when(order.payment_method == "credit")
                .then(order.credit_limit)
                .must_be_greater_than(order.total_amount)
        ])
```

### 9. Case Conversion and API Compatibility

Use automatic case conversion for API serialization compatibility:

```python
from neuroglia.utils import CamelModel

class CreateUserDto(CamelModel):  # Automatically converts snake_case to camelCase
    first_name: str  # Serializes as "firstName"
    last_name: str   # Serializes as "lastName"
    email_address: str  # Serializes as "emailAddress"
```

### 10. Reactive Programming Patterns

Implement reactive data processing with observables:

```python
from neuroglia.reactive import Observable

class OrderProcessingService:
    def __init__(self):
        self.order_stream = Observable.create(self.setup_order_stream)

    async def setup_order_stream(self, observer):
        # Setup reactive processing pipeline
        await self.order_stream \
            .filter(lambda order: order.is_valid) \
            .map(self.transform_order) \
            .subscribe(observer.on_next)
```

## Common Anti-Patterns to Avoid

1. **Direct database calls in controllers** - Always use mediator
2. **Domain logic in handlers** - Keep handlers thin, logic in domain
3. **Tight coupling between layers** - Respect dependency directions
4. **Anemic domain models** - Domain entities should have behavior
5. **Fat controllers** - Controllers should only orchestrate
6. **Ignoring async/await** - Use async patterns throughout
7. **Manual serialization** - Use JsonSerializer with automatic type handling
8. **Inconsistent case conversion** - Use CamelModel for API compatibility
9. **Synchronous validation** - Use async business rule validation
10. **Missing resource reconciliation** - Implement proper resource controllers
11. **Authorization in controllers** - Implement RBAC in handlers (application layer)
12. **Missing observability** - Add tracing, metrics, and logging with OpenTelemetry

## Advanced Framework Features

### Observability with OpenTelemetry

The framework provides comprehensive observability through OpenTelemetry integration:

```python
from neuroglia.observability import (
    configure_opentelemetry,
    get_tracer,
    get_meter,
    trace_async,
    trace_sync
)

# Configure in application startup
def create_app():
    builder = WebApplicationBuilder()

    # Configure OpenTelemetry
    configure_opentelemetry(
        service_name="mario-pizzeria",
        service_version="1.0.0",
        otlp_endpoint="http://localhost:4317",
        export_logs=True,
        export_traces=True,
        export_metrics=True
    )

    # Continue with application setup...
    return builder.build()

# Use tracing decorators in handlers
class PlaceOrderHandler(CommandHandler):
    def __init__(self):
        super().__init__()
        self.tracer = get_tracer(__name__)
        self.meter = get_meter(__name__)
        self.order_counter = self.meter.create_counter(
            "orders_placed_total",
            description="Total number of orders placed"
        )

    @trace_async(name="place_order")
    async def handle_async(self, command: PlaceOrderCommand):
        # Automatic span creation
        with self.tracer.start_as_current_span("validate_order") as span:
            span.set_attribute("customer_id", command.customer_id)
            # Validation logic

        # Increment counter
        self.order_counter.add(1, {"customer_type": "vip"})

        # Business logic continues...
```

**Key Observability Patterns:**

- Use `@trace_async` and `@trace_sync` decorators for automatic tracing
- Create custom spans for important operations with `tracer.start_as_current_span()`
- Add span attributes for contextual information
- Use counters, gauges, and histograms for metrics
- Logs are automatically correlated with traces
- Context propagation works automatically across service boundaries

### Role-Based Access Control (RBAC)

RBAC is implemented at the **application layer** (handlers), not at the API layer:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

# Extract user context in controller
class OrdersController(ControllerBase):

    def _get_user_info(self, credentials: HTTPAuthorizationCredentials) -> dict:
        """Extract user information from JWT token."""
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", [])
        }

    @post("/", response_model=OrderDto)
    async def create_order(
        self,
        dto: CreateOrderDto,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> OrderDto:
        user_info = self._get_user_info(credentials)

        command = CreateOrderCommand(
            customer_id=dto.customer_id,
            items=dto.items,
            user_context=user_info  # Pass to handler
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

# Authorization in handler (application layer)
class CreateOrderHandler(CommandHandler):
    async def handle_async(self, command: CreateOrderCommand):
        # Role-based authorization
        if not self._has_role(command.user_context, "customer"):
            return self.forbidden("Only customers can place orders")

        # Permission-based authorization
        if not self._has_permission(command.user_context, "orders:create"):
            return self.forbidden("Insufficient permissions")

        # Resource-level authorization
        if not self._is_own_order(command.user_context, command.customer_id):
            return self.forbidden("Cannot place orders for other customers")

        # Business logic
        order = Order(command.customer_id, command.items)
        await self.repository.save_async(order)
        return self.created(order)

    def _has_role(self, user_context: dict, role: str) -> bool:
        return role in user_context.get("roles", [])

    def _has_permission(self, user_context: dict, permission: str) -> bool:
        return permission in user_context.get("permissions", [])

    def _is_own_order(self, user_context: dict, customer_id: str) -> bool:
        return user_context.get("user_id") == customer_id
```

**RBAC Best Practices:**

- **Always implement authorization in handlers**, never in controllers
- Pass user context (roles, permissions, user_id) from JWT to commands/queries
- Use helper methods for common authorization checks
- Default to deny access (fail securely)
- Combine role-based, permission-based, and resource-level checks
- Audit authorization failures for security monitoring
- Keep role/permission names configurable (not hardcoded)

### SubApp Pattern for UI/API Separation

Use FastAPI SubApp mounting for clean separation of concerns:

```python
from neuroglia.hosting.web import WebApplicationBuilder, SubAppConfig

def create_app():
    builder = WebApplicationBuilder()

    # Configure core services
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos"])

    # Add API SubApp
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            title="Application API",
            controllers=["api.controllers"],
            docs_url="/docs"
        )
    )

    # Add UI SubApp
    builder.add_sub_app(
        SubAppConfig(
            path="/",
            name="ui",
            title="Application UI",
            controllers=["ui.controllers"],
            static_files=[("/static", "static/dist")]
        )
    )

    return builder.build()
```

**SubApp Benefits:**

- Clean separation between UI and API concerns
- Different middleware for different SubApps
- Independent scaling and deployment
- Clear API boundaries
- Easy migration to microservices

4. **Anemic domain models** - Domain entities should have behavior
5. **Fat controllers** - Controllers should only orchestrate
6. **Ignoring async/await** - Use async patterns throughout
7. **Manual serialization** - Use JsonSerializer with automatic type handling
8. **Inconsistent case conversion** - Use CamelModel for API compatibility
9. **Synchronous validation** - Use async business rule validation
10. **Missing resource reconciliation** - Implement proper resource controllers

## Testing Patterns & Automated Test Maintenance

### Test File Organization

The framework follows a strict test organization pattern in `./tests/`:

```
tests/
├── __init__.py
├── conftest.py              # Shared test fixtures and configuration
├── cases/                   # Unit tests (organized by feature)
│   ├── test_mediator.py
│   ├── test_service_provider.py
│   ├── test_mapper.py
│   ├── test_*_repository.py
│   └── test_*_handler.py
├── integration/             # Integration tests
│   ├── test_*_controller.py
│   ├── test_*_workflow.py
│   └── test_*_api.py
└── fixtures/               # Test data and mock objects
    ├── domain/
    ├── application/
    └── integration/
```

### Automated Test Creation Rules

**When making ANY code changes, ALWAYS ensure corresponding tests exist and are updated:**

#### 1. New Framework Features (src/neuroglia/)

**For every new class, method, or function added to the framework:**

```python
# If adding to src/neuroglia/mediation/mediator.py
# MUST create/update tests/cases/test_mediator.py

class TestMediator:
    def setup_method(self):
        self.services = ServiceCollection()
        self.mediator = self.services.add_mediator().build_provider().get_service(Mediator)

    @pytest.mark.asyncio
    async def test_new_feature_behavior(self):
        # Test the new feature thoroughly
        pass
```

#### 2. New Controllers (api/controllers/)

**For every new controller, ALWAYS create integration tests:**

```python
# File: tests/integration/test_{entity}_controller.py
@pytest.mark.integration
class Test{Entity}Controller:
    @pytest.fixture
    def test_app(self):
        # Setup test application with dependencies
        return create_test_app()

    @pytest.mark.asyncio
    async def test_get_{entity}_success(self, test_client):
        response = await test_client.get("/api/{entities}/123")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_{entity}_success(self, test_client):
        data = {"field": "value"}
        response = await test_client.post("/api/{entities}", json=data)
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_{entity}_validation_error(self, test_client):
        invalid_data = {}
        response = await test_client.post("/api/{entities}", json=invalid_data)
        assert response.status_code == 400
```

#### 3. New Command/Query Handlers (application/handlers/)

**For every new handler, ALWAYS create unit tests:**

```python
# File: tests/cases/test_{action}_{entity}_handler.py
class Test{Action}{Entity}Handler:
    def setup_method(self):
        # Mock all dependencies
        self.repository = Mock(spec={Entity}Repository)
        self.mapper = Mock(spec=Mapper)
        self.event_bus = Mock(spec=EventBus)
        self.handler = {Action}{Entity}Handler(
            self.repository,
            self.mapper,
            self.event_bus
        )

    @pytest.mark.asyncio
    async def test_handle_success_scenario(self):
        # Test successful execution
        command = {Action}{Entity}Command(field="value")
        result = await self.handler.handle_async(command)

        assert result.is_success
        self.repository.save_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_validation_failure(self):
        # Test validation scenarios
        invalid_command = {Action}{Entity}Command(field=None)
        result = await self.handler.handle_async(invalid_command)

        assert not result.is_success
        assert "validation" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_handle_repository_exception(self):
        # Test error handling
        self.repository.save_async.side_effect = Exception("Database error")
        command = {Action}{Entity}Command(field="value")

        result = await self.handler.handle_async(command)
        assert not result.is_success
```

#### 4. New Domain Entities (domain/entities/)

**For every new entity, create comprehensive unit tests:**

```python
# File: tests/cases/test_{entity}.py
class Test{Entity}:
    def test_entity_creation(self):
        entity = {Entity}(required_field="value")
        assert entity.required_field == "value"
        assert entity.id is not None

    def test_entity_raises_domain_events(self):
        entity = {Entity}(required_field="value")
        events = entity.get_uncommitted_events()

        assert len(events) == 1
        assert isinstance(events[0], {Entity}CreatedEvent)

    def test_entity_business_rules(self):
        # Test domain business logic
        entity = {Entity}(required_field="value")

        # Test valid business operation
        result = entity.perform_business_operation()
        assert result.is_success

        # Test invalid business operation
        invalid_result = entity.perform_invalid_operation()
        assert not invalid_result.is_success
```

#### 5. New Repositories (integration/repositories/)

**For every new repository, create both unit and integration tests:**

```python
# Unit tests: tests/cases/test_{entity}_repository.py
class Test{Entity}Repository:
    def setup_method(self):
        self.mock_collection = Mock()
        self.repository = {Entity}Repository(self.mock_collection)

    @pytest.mark.asyncio
    async def test_save_async(self):
        entity = {Entity}(field="value")
        await self.repository.save_async(entity)
        self.mock_collection.insert_one.assert_called_once()

# Integration tests: tests/integration/test_{entity}_repository_integration.py
@pytest.mark.integration
class Test{Entity}RepositoryIntegration:
    @pytest.fixture
    async def repository(self, mongo_client):
        return {Entity}Repository(mongo_client.test_db.{entities})

    @pytest.mark.asyncio
    async def test_full_crud_operations(self, repository):
        # Test complete CRUD workflow
        entity = {Entity}(field="value")

        # Create
        await repository.save_async(entity)

        # Read
        retrieved = await repository.get_by_id_async(entity.id)
        assert retrieved.field == "value"

        # Update
        retrieved.field = "updated"
        await repository.save_async(retrieved)

        # Delete
        await repository.delete_async(entity.id)
        deleted = await repository.get_by_id_async(entity.id)
        assert deleted is None
```

### Test Coverage Requirements

**All new code MUST achieve minimum 90% test coverage:**

1. **Unit Tests**: Cover all business logic, validation, and error scenarios
2. **Integration Tests**: Cover complete workflows and API endpoints
3. **Edge Cases**: Test boundary conditions and exceptional scenarios
4. **Async Operations**: All async methods must have async test coverage

### Test Fixtures and Utilities

**Use shared fixtures for consistency:**

```python
# tests/conftest.py additions for new features
@pytest.fixture
def mock_{entity}_repository():
    repository = Mock(spec={Entity}Repository)
    repository.get_by_id_async.return_value = create_test_{entity}()
    return repository

@pytest.fixture
def test_{entity}():
    return {Entity}(
        field1="test_value1",
        field2="test_value2"
    )

@pytest.fixture
async def {entity}_test_data():
    # Create comprehensive test data sets
    return [
        create_test_{entity}(field="value1"),
        create_test_{entity}(field="value2"),
    ]
```

### Test Naming Conventions

**Follow strict naming patterns:**

- **Test Files**: `test_{feature}.py` or `test_{entity}_{action}.py`
- **Test Classes**: `Test{ClassName}` matching the class being tested
- **Test Methods**: `test_{method_name}_{scenario}` (e.g., `test_handle_async_success`)
- **Integration Tests**: Include `@pytest.mark.integration` decorator
- **Async Tests**: Include `@pytest.mark.asyncio` decorator

### Automated Test Validation

**When creating or modifying code, ALWAYS:**

1. **Check Existing Tests**: Verify if tests exist for the modified code
2. **Update Tests**: Modify existing tests to match code changes
3. **Add Missing Tests**: Create new tests for new functionality
4. **Validate Coverage**: Ensure test coverage remains above 90%
5. **Test All Scenarios**: Include success, failure, and edge cases
6. **Mock Dependencies**: Use proper mocking for unit tests
7. **Test Async Operations**: Ensure all async code has async tests

### Test Execution Patterns

**Run tests appropriately:**

```bash
# Unit tests only
pytest tests/cases/ -v

# Integration tests only
pytest tests/integration/ -m integration -v

# All tests with coverage
pytest --cov=src/neuroglia --cov-report=html --cov-report=term

# Specific feature tests
pytest tests/cases/test_mediator.py -v
```

### Test Code Quality Standards

**All test code must:**

1. **Be Readable**: Clear, descriptive test names and scenarios
2. **Be Maintainable**: Use fixtures and utilities to reduce duplication
3. **Be Fast**: Unit tests should complete in milliseconds
4. **Be Isolated**: Tests should not depend on external systems (except integration tests)
5. **Be Deterministic**: Tests should always produce the same result
6. **Follow AAA Pattern**: Arrange, Act, Assert structure

## Error Handling Patterns

Use RequestHandler helper methods for consistent error handling:

**Available Helper Methods** (all inherit from `RequestHandler`):

```python
# Success responses (2xx)
self.ok(data)                      # 200 OK
self.created(data)                 # 201 Created
self.accepted(data)                # 202 Accepted
self.no_content()                  # 204 No Content

# Client errors (4xx)
self.bad_request(detail)           # 400 Bad Request
self.unauthorized(detail)          # 401 Unauthorized
self.forbidden(detail)             # 403 Forbidden
self.not_found(entity_type, key)   # 404 Not Found
self.conflict(message)             # 409 Conflict
self.unprocessable_entity(detail)  # 422 Unprocessable Entity

# Server errors (5xx)
self.internal_server_error(detail) # 500 Internal Server Error
self.service_unavailable(detail)   # 503 Service Unavailable
```

**Complete Example:**

```python
class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
    async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
        try:
            # Input validation → 400
            if not command.email:
                return self.bad_request("Email is required")

            # Business validation → 409
            if await self.user_repository.exists_by_email(command.email):
                return self.conflict("User with this email already exists")

            # Authorization → 403
            if not command.user_context.can_create_users:
                return self.forbidden("Insufficient permissions to create users")

            # Business logic
            user = User(command.email, command.first_name, command.last_name)
            await self.user_repository.save_async(user)

            user_dto = self.mapper.map(user, UserDto)
            return self.created(user_dto)  # 201

        except Exception as ex:
            return self.internal_server_error(f"Failed to create user: {str(ex)}")  # 500
```

**DO NOT construct OperationResult manually:**

```python
# ❌ WRONG - Don't do this
result = OperationResult("OK", 200)
result.data = user
return result

# ✅ CORRECT - Use helper methods
return self.ok(user)
```

## Performance Considerations

1. **Use scoped services for repositories** - Enables caching within request
2. **Implement async throughout** - All I/O operations should be async
3. **Use read models for queries** - Separate optimized read models from write models
4. **Leverage event-driven architecture** - For decoupled, scalable processing
5. **Implement caching strategies** - Use singleton services for expensive operations

## Security Best Practices

1. **Validate all inputs** - Use Pydantic models for automatic validation
2. **Implement authentication middleware** - Protect endpoints appropriately
3. **Use dependency injection for security services** - Makes testing easier
4. **Audit important operations** - Use events for audit trails
5. **Follow principle of least privilege** - Controllers should only access what they need

## IDE-Specific Instructions

When using this framework in VS Code with Copilot:

1. **Suggest imports** based on the framework's module structure
2. **Follow naming conventions** for consistency across the codebase
3. **Implement complete CQRS patterns** when creating new features
4. **Generate corresponding tests** for any new handlers or controllers
5. **Respect layer boundaries** when suggesting code changes
6. **Use async/await** by default for all I/O operations
7. **Suggest dependency injection** patterns for new services
8. **Add observability** decorators (`@trace_async`) to handlers
9. **Implement RBAC** at application layer (handlers), not API layer
10. **Use SubApp pattern** for UI/API separation when applicable
11. **Include type hints** for all function signatures
12. **Reference sample applications** (Mario's Pizzeria, OpenBank, Simple UI) for patterns

### Automatic Test Maintenance

**CRITICAL: When making ANY code changes, ALWAYS ensure tests are created or updated:**

#### For New Framework Code (src/neuroglia/)

- **Automatically create** `tests/cases/test_{module}.py` for any new framework module
- **Include comprehensive unit tests** covering all public methods and edge cases
- **Mock all external dependencies** and test error scenarios
- **Use async test patterns** for all async framework methods

#### For New Application Code

- **Controllers**: Create `tests/integration/test_{entity}_controller.py` with full API endpoint testing
- **Handlers**: Create `tests/cases/test_{action}_{entity}_handler.py` with success/failure scenarios
- **Entities**: Create `tests/cases/test_{entity}.py` with business rule validation
- **Repositories**: Create both unit and integration tests for data access

#### Test Creation Rules

1. **Never suggest code changes without corresponding test updates**
2. **Always check if tests exist before modifying code**
3. **Create missing tests when encountering untested code**
4. **Update existing tests when modifying tested code**
5. **Follow test naming conventions strictly**
6. **Include both positive and negative test cases**
7. **Ensure 90%+ test coverage for all new code**

#### Test Templates to Use

- Use the test patterns defined in "Testing Patterns & Automated Test Maintenance"
- Follow AAA (Arrange, Act, Assert) pattern
- Include proper fixtures from `tests/conftest.py`
- Use `@pytest.mark.asyncio` for async tests
- Use `@pytest.mark.integration` for integration tests

## Documentation Maintenance

### Automatic Documentation Updates

When making changes to the framework, **always** update the relevant documentation:

#### README.md Updates

- **New Features**: Add to the "🚀 Key Features" section with appropriate emoji and description
- **Breaking Changes**: Update version requirements and migration notes
- **API Changes**: Update code examples in Quick Start section
- **Dependencies**: Update the "📋 Requirements" section
- **Testing**: Keep testing documentation current with new test capabilities

#### MkDocs Documentation (/docs)

**Core Documentation Files:**

- `docs/index.md` - Main documentation homepage
- `docs/getting-started.md` - Tutorial and setup guide
- `docs/architecture.md` - Architecture principles and patterns

**Feature Documentation (/docs/features/):**

- `dependency-injection.md` - DI container and service registration
- `cqrs-mediation.md` - Command/Query patterns and handlers
- `mvc-controllers.md` - Controller development and routing
- `data-access.md` - Repository pattern and data persistence

**Sample Documentation (/docs/samples/):**

- `openbank.md` - Banking domain sample with event sourcing
- `api_gateway.md` - Microservice gateway patterns
- `desktop_controller.md` - Background services example

#### Documentation Update Rules

1. **New Framework Features**: Create or update relevant `/docs/features/` files
2. **New Code Examples**: Add realistic, working examples to documentation
3. **API Changes**: Update all affected documentation files immediately
4. **Sample Applications**: Keep sample docs synchronized with actual sample code
5. **Cross-References**: Maintain consistent linking between docs using relative paths

#### MkDocs Navigation (mkdocs.yml)

When adding new documentation:

```yaml
nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - Architecture: architecture.md
  - Features:
      - Dependency Injection: features/dependency-injection.md
      - CQRS & Mediation: features/cqrs-mediation.md
      - MVC Controllers: features/mvc-controllers.md
      - Data Access: features/data-access.md
      - [NEW FEATURE]: features/new-feature.md
  - Sample Applications:
      - OpenBank: samples/openbank.md
      - API Gateway: samples/api_gateway.md
      - Desktop Controller: samples/desktop_controller.md
```

#### Documentation Standards

**Code Examples:**

- Always provide complete, runnable examples
- Include necessary imports
- Use realistic variable names and scenarios
- Follow framework naming conventions
- Include error handling where appropriate

**Format Consistency:**

- Use consistent emoji in headings (🎯 🏗️ 🚀 🔧 etc.)
- Follow markdown best practices
- Use proper code highlighting with language tags
- Include "Related Documentation" sections with links

**Content Guidelines:**

- Start with overview and key concepts
- Provide step-by-step tutorials
- Include common use cases and patterns
- Add troubleshooting sections for complex topics
- Reference actual framework code when possible

#### Automatic Tasks for Copilot

When suggesting code changes:

1. **Check Documentation Impact**: Identify which docs need updates
2. **Suggest Doc Updates**: Provide updated documentation alongside code changes
3. **Maintain Examples**: Ensure all code examples remain valid and current
4. **Update Cross-References**: Fix any broken internal links
5. **Version Compatibility**: Update version requirements if needed

#### Documentation File Templates

**New Feature Documentation:**

```markdown
# 🎯 [Feature Name]

Brief description of the feature and its purpose.

## 🎯 Overview

Key concepts and benefits.

## 🏗️ Basic Usage

Simple examples to get started.

## 🚀 Advanced Features

Complex scenarios and patterns.

## 🧪 Testing

How to test code using this feature.

## 🔗 Related Documentation

- [Related Feature](related-feature.md)
- [Getting Started](../getting-started.md)
```

**Sample Application Documentation:**

```markdown
# 🏦 [Sample Name]

Description of what the sample demonstrates.

## 🎯 What You'll Learn

- Key pattern 1
- Key pattern 2
- Key pattern 3

## 🏗️ Architecture

System architecture and components.

## 🚀 Getting Started

Step-by-step setup instructions.

## 💡 Key Implementation Details

Important code patterns and decisions.

## 🔗 Related Documentation

Links to relevant feature documentation.
```

Remember: Documentation is code - it should be maintained with the same rigor as the framework itself. Every new feature, API change, or sample application must have corresponding documentation updates.

## Final Reminder

Neuroglia enforces clean architecture - always respect the dependency rule and maintain clear separation of concerns between layers. Keep documentation current and comprehensive for the best developer experience.

### Test Automation Priority

**MOST IMPORTANT: Test automation is mandatory when making code changes:**

1. **Tests are NOT optional** - Every code change must include corresponding test updates
2. **Check test coverage** - Ensure 90%+ coverage is maintained for all new code
3. **Follow test patterns** - Use the comprehensive testing patterns defined above
4. **Test all scenarios** - Include success, failure, validation, and edge cases
5. **Maintain test quality** - Tests should be as well-written as production code
6. **Use proper mocking** - Mock external dependencies appropriately
7. **Validate async operations** - All async code must have async test coverage

**Remember: Code without tests is incomplete code in the Neuroglia framework.**

## Key Sample Applications Reference

### Mario's Pizzeria

- **Location**: `samples/mario-pizzeria/`
- **Focus**: CQRS, event-driven architecture, MongoDB persistence, OpenTelemetry observability
- **Documentation**: `docs/mario-pizzeria.md`, `docs/guides/mario-pizzeria-tutorial.md`
- **Tutorial Series**: 9-part comprehensive tutorial in `docs/tutorials/`

### OpenBank

- **Location**: `samples/openbank/`
- **Focus**: Event sourcing with KurrentDB, CQRS with read/write models, snapshots, projections
- **Documentation**: `docs/samples/openbank.md`
- **Key Patterns**: Event sourcing, eventual consistency, read model reconciliation

### Simple UI

- **Location**: `samples/simple-ui/`
- **Focus**: SubApp pattern, stateless JWT authentication, RBAC at application layer
- **Documentation**: `docs/samples/simple-ui.md`, `docs/guides/rbac-authorization.md`
- **Key Patterns**: UI/API separation, role-based authorization, permission checks

## Documentation Navigation Map

### Getting Started

- `docs/getting-started.md` - Framework introduction
- `docs/guides/3-min-bootstrap.md` - Quick start
- `docs/guides/local-development.md` - Development setup

### Core Features

- `docs/features/simple-cqrs.md` - CQRS implementation
- `docs/features/data-access.md` - Repository patterns
- `docs/features/mvc-controllers.md` - Controller implementation
- `docs/features/observability.md` - **NEW**: Comprehensive OpenTelemetry guide
- `docs/features/serialization.md` - JSON serialization

### Guides (3-Tier Structure)

- **Getting Started**: Project setup, testing setup, local dev
- **Development**: Mario's tutorial, Simple UI app, JSON config
- **Operations**: **NEW**: OpenTelemetry integration, RBAC & authorization

### Patterns

- `docs/patterns/clean-architecture.md` - Architecture principles
- `docs/patterns/cqrs.md` - Command/Query separation
- `docs/patterns/repository.md` - Repository pattern
- `docs/patterns/persistence-patterns.md` - Persistence strategies
- `docs/patterns/unit-of-work.md` - DEPRECATED (use repository-based event publishing)

### References

- `docs/references/python_typing_guide.md` - Type hints & generics
- `docs/references/12-factor-app.md` - Cloud-native principles
- `docs/references/source_code_naming_convention.md` - Naming standards

## Recent Framework Improvements (v0.6.0+)

1. **Observability Enhancement**:

   - Expanded observability guide from 838 to 2,079 lines
   - Architecture overview with Mermaid diagrams
   - Infrastructure setup (Docker Compose, Kubernetes)
   - Layer-by-layer developer implementation guide
   - Metric types comparison (Counter, Gauge, Histogram)
   - Complete data flow visualization

2. **RBAC Documentation**:

   - Comprehensive RBAC guide with practical patterns
   - JWT authentication integration
   - Role-based, permission-based, and resource-level authorization
   - Simple UI sample demonstrating RBAC implementation

3. **Documentation Reorganization**:

   - Reorganized MkDocs navigation (3-tier Guides structure)
   - Cross-referenced all observability documentation
   - Added documentation maps and learning paths
   - Enhanced sample documentation (OpenBank, Simple UI)

4. **SubApp Pattern**:
   - Clean UI/API separation pattern
   - Simple UI sample demonstrating implementation
   - Bootstrap 5 frontend integration
   - Stateless JWT authentication
