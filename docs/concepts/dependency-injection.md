# Dependency Injection

**Time to read: 12 minutes**

Dependency Injection (DI) is a technique where **objects receive their dependencies instead of creating them**. It's the "glue" that makes clean architecture work in Neuroglia.

## ❌ The Problem: Hard-Coded Dependencies

Without DI, classes create their own dependencies:

```python
# ❌ Handler creates its own dependencies
class PlaceOrderHandler:
    def __init__(self):
        # Creates concrete MongoDB repository
        self.repository = MongoOrderRepository()
        self.email_service = SmtpEmailService()
        self.payment_service = StripePaymentService()

    async def handle(self, command):
        order = Order(command.customer_id)
        await self.repository.save(order)
        await self.email_service.send_confirmation(order)
        await self.payment_service.charge(order)
```

**Problems:**

1. **Can't test**: Tests need real MongoDB, SMTP server, and Stripe account
2. **Can't reuse**: Tightly coupled to specific implementations
3. **Can't configure**: Same implementations for dev, test, and prod
4. **Can't mock**: No way to isolate behavior for testing
5. **Violates dependency rule**: Application layer knows about infrastructure details

## ✅ The Solution: Inject Dependencies

Pass dependencies as constructor parameters:

```python
# ✅ Handler receives dependencies
class PlaceOrderHandler:
    def __init__(self,
                 repository: IOrderRepository,        # Interface
                 email_service: IEmailService,        # Interface
                 payment_service: IPaymentService):   # Interface
        self.repository = repository
        self.email_service = email_service
        self.payment_service = payment_service

    async def handle(self, command):
        order = Order(command.customer_id)
        await self.repository.save(order)
        await self.email_service.send_confirmation(order)
        await self.payment_service.charge(order)
```

**Benefits:**

1. **Testable**: Inject test doubles (mocks, fakes)
2. **Flexible**: Swap implementations (MongoDB → PostgreSQL)
3. **Configurable**: Different implementations per environment
4. **Mockable**: Unit test in isolation
5. **Clean**: Respects dependency rule (uses interfaces)

### Who Creates the Dependencies?

A **DI container** (Neuroglia's `ServiceProvider`) creates and wires dependencies:

```python
# Configure container
services = ServiceCollection()
services.add_scoped(IOrderRepository, MongoOrderRepository)
services.add_scoped(IEmailService, SmtpEmailService)
services.add_scoped(IPaymentService, StripePaymentService)

# Container creates handler with dependencies
handler = services.build_provider().get_service(PlaceOrderHandler)
# Container automatically injects: MongoOrderRepository, SmtpEmailService, StripePaymentService
```

## 🔧 Dependency Injection in Neuroglia

### Service Registration

Neuroglia uses a `ServiceCollection` to register dependencies:

```python
from neuroglia.dependency_injection import ServiceCollection, ServiceLifetime

# Create container
services = ServiceCollection()

# Register services with different lifetimes
services.add_singleton(ConfigService)       # Created once, shared forever
services.add_scoped(OrderRepository)        # Created once per request
services.add_transient(EmailService)        # Created every time requested
```

### Service Lifetimes

**1. Singleton** - One instance for entire application

```python
services.add_singleton(ConfigService)

# Same instance everywhere
config1 = provider.get_service(ConfigService)
config2 = provider.get_service(ConfigService)
assert config1 is config2  # True - same object
```

**Use when**: Configuration, caches, shared state

**2. Scoped** - One instance per request/scope

```python
services.add_scoped(OrderRepository)

# Same instance within a scope (HTTP request)
with provider.create_scope() as scope:
    repo1 = scope.get_service(OrderRepository)
    repo2 = scope.get_service(OrderRepository)
    assert repo1 is repo2  # True - same object in scope

# Different instance in different scope
with provider.create_scope() as scope2:
    repo3 = scope2.get_service(OrderRepository)
    assert repo1 is not repo3  # True - different scope
```

**Use when**: Repositories, database connections, per-request state

**3. Transient** - New instance every time

```python
services.add_transient(EmailService)

# Different instance every time
email1 = provider.get_service(EmailService)
email2 = provider.get_service(EmailService)
assert email1 is not email2  # True - different objects
```

**Use when**: Lightweight services, stateless operations

### Constructor Injection Pattern

Neuroglia automatically injects dependencies through constructors:

```python
# 1. Define interfaces (domain layer)
class IOrderRepository(ABC):
    @abstractmethod
    async def save_async(self, order: Order): pass

class IEmailService(ABC):
    @abstractmethod
    async def send_async(self, to: str, message: str): pass

# 2. Implement interfaces (infrastructure layer)
class MongoOrderRepository(IOrderRepository):
    async def save_async(self, order: Order):
        # MongoDB implementation
        pass

class SmtpEmailService(IEmailService):
    async def send_async(self, to: str, message: str):
        # SMTP implementation
        pass

# 3. Handler requests dependencies (application layer)
class PlaceOrderHandler:
    def __init__(self,
                 repository: IOrderRepository,      # Will be injected
                 email_service: IEmailService):     # Will be injected
        self.repository = repository
        self.email_service = email_service

    async def handle(self, command: PlaceOrderCommand):
        order = Order(command.customer_id, command.items)
        await self.repository.save_async(order)
        await self.email_service.send_async(order.customer.email, "Order confirmed")

# 4. Register with DI container
services = ServiceCollection()
services.add_scoped(IOrderRepository, MongoOrderRepository)
services.add_scoped(IEmailService, SmtpEmailService)
services.add_scoped(PlaceOrderHandler)  # Container auto-wires dependencies

# 5. Resolve and use
provider = services.build_provider()
handler = provider.get_service(PlaceOrderHandler)
# handler.repository is MongoOrderRepository instance
# handler.email_service is SmtpEmailService instance
```

### Registration Patterns

**Interface → Implementation**

```python
services.add_scoped(IOrderRepository, MongoOrderRepository)
# When someone asks for IOrderRepository, give them MongoOrderRepository
```

**Concrete Class**

```python
services.add_scoped(OrderService)
# Register and resolve by concrete class
```

**Factory Function**

```python
def create_email_service(provider):
    config = provider.get_service(ConfigService)
    return SmtpEmailService(config.smtp_host, config.smtp_port)

services.add_scoped(IEmailService, factory=create_email_service)
# Use factory for complex initialization
```

## 🏗️ Real-World Example: Mario's Pizzeria

```python
# main.py - Application startup
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper

def create_app():
    builder = WebApplicationBuilder()

    # Configure core services
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos", "domain.entities"])

    # Register domain services
    builder.services.add_scoped(IOrderRepository, MongoOrderRepository)
    builder.services.add_scoped(ICustomerRepository, MongoCustomerRepository)
    builder.services.add_scoped(IMenuRepository, MongoMenuRepository)

    # Register application services
    builder.services.add_scoped(OrderService)
    builder.services.add_scoped(CustomerService)

    # Register infrastructure
    builder.services.add_singleton(ConfigService)
    builder.services.add_scoped(IEmailService, SendGridEmailService)
    builder.services.add_scoped(IPaymentService, StripePaymentService)

    # Add SubApp with controllers
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            controllers=["api.controllers"]
        )
    )

    return builder.build()

# Controller automatically gets dependencies
class OrdersController(ControllerBase):
    def __init__(self,
                 service_provider: ServiceProvider,
                 mapper: Mapper,
                 mediator: Mediator):  # All injected!
        super().__init__(service_provider, mapper, mediator)

    @post("/orders")
    async def create_order(self, dto: CreateOrderDto):
        command = self.mapper.map(dto, PlaceOrderCommand)
        result = await self.mediator.execute_async(command)
        return self.process(result)
```

## 🧪 Testing with DI

### Unit Tests: Inject Mocks

```python
from unittest.mock import Mock

async def test_place_order_handler():
    # Create test doubles
    mock_repo = Mock(spec=IOrderRepository)
    mock_email = Mock(spec=IEmailService)

    # Inject mocks
    handler = PlaceOrderHandler(mock_repo, mock_email)

    # Test
    command = PlaceOrderCommand(customer_id="123", items=[...])
    await handler.handle(command)

    # Verify behavior
    mock_repo.save_async.assert_called_once()
    mock_email.send_async.assert_called_once()
```

### Integration Tests: Inject Test Implementations

```python
async def test_order_workflow():
    # Use in-memory implementations for integration testing
    services = ServiceCollection()
    services.add_scoped(IOrderRepository, InMemoryOrderRepository)
    services.add_scoped(IEmailService, FakeEmailService)

    provider = services.build_provider()
    handler = provider.get_service(PlaceOrderHandler)

    # Test with real workflow (no external dependencies)
    command = PlaceOrderCommand(customer_id="123", items=[...])
    result = await handler.handle(command)

    assert result.is_success
```

## ⚠️ Common Mistakes

### 1. Mixing Service Lifetimes Incorrectly

```python
# ❌ WRONG: Singleton depends on Scoped
class ConfigService:  # Singleton
    def __init__(self, repository: IOrderRepository):  # Scoped!
        self.repository = repository

services.add_singleton(ConfigService)
services.add_scoped(IOrderRepository, MongoOrderRepository)
# ConfigService lives forever, but OrderRepository should be per-request!
```

**Rule**: Higher lifetime can't depend on lower lifetime.

```
✅ Singleton → Singleton
✅ Scoped → Singleton
✅ Scoped → Scoped
✅ Transient → Singleton
✅ Transient → Scoped
✅ Transient → Transient

❌ Singleton → Scoped
❌ Singleton → Transient
❌ Scoped → Transient
```

### 2. Registering Concrete Implementation Instead of Interface

```python
# ❌ WRONG: Handler depends on concrete class
class PlaceOrderHandler:
    def __init__(self, repository: MongoOrderRepository):  # Concrete!
        self.repository = repository

# ✅ RIGHT: Handler depends on interface
class PlaceOrderHandler:
    def __init__(self, repository: IOrderRepository):  # Interface!
        self.repository = repository

services.add_scoped(IOrderRepository, MongoOrderRepository)
```

### 3. Creating Dependencies Manually

```python
# ❌ WRONG: Creating dependency manually
class OrdersController:
    def __init__(self, service_provider: ServiceProvider):
        self.repository = MongoOrderRepository()  # NO!

# ✅ RIGHT: Let container inject
class OrdersController:
    def __init__(self,
                 service_provider: ServiceProvider,
                 repository: IOrderRepository):  # Injected!
        super().__init__(service_provider)
        self.repository = repository
```

### 4. Circular Dependencies

```python
# ❌ WRONG: A depends on B, B depends on A
class ServiceA:
    def __init__(self, service_b: ServiceB): pass

class ServiceB:
    def __init__(self, service_a: ServiceA): pass
# Container can't resolve this!

# ✅ RIGHT: Introduce abstraction or event-driven communication
class ServiceA:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        # Use events instead of direct dependency
```

## 🚫 When NOT to Use DI

DI has overhead. Skip it when:

1. **Scripts/One-Off Tools**: Simple scripts don't need DI
2. **No Tests**: If you're never testing, DI adds complexity
3. **Single Implementation**: If you'll never swap implementations
4. **Prototypes**: Quick throwaway code

For small apps, manual dependency management is fine:

```python
# Simple script - no DI needed
def main():
    repo = MongoOrderRepository()
    handler = PlaceOrderHandler(repo)
    # ...
```

## 📝 Key Takeaways

1. **Constructor Injection**: Dependencies passed as parameters
2. **Interface Segregation**: Depend on interfaces, not implementations
3. **Service Lifetimes**: Singleton (app), Scoped (request), Transient (always new)
4. **DI Container**: Automatically resolves and injects dependencies
5. **Testability**: Inject mocks/fakes for testing

## 🔄 DI + Clean Architecture

DI is the **mechanism** that enables clean architecture:

```
Domain defines interfaces → Application uses interfaces → Infrastructure implements interfaces
                           ↓
                    DI Container wires everything at runtime
```

Without DI, application layer would need to create infrastructure (violating dependency rule).

## 🚀 Next Steps

- **See it work**: [Tutorial Part 1](../tutorials/mario-pizzeria-01-setup.md) shows DI setup
- **Understand CQRS**: [CQRS](cqrs.md) uses DI for handler resolution
- **Mediator pattern**: [Mediator](mediator.md) relies on DI to find handlers

## 📚 Further Reading

- [Martin Fowler - Dependency Injection](https://martinfowler.com/articles/injection.html)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Neuroglia DI documentation](../features/index.md)

---

**Previous:** [← Clean Architecture](clean-architecture.md) | **Next:** [Domain-Driven Design →](domain-driven-design.md)
