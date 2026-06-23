# 🔧 Dependency Injection Pattern

_Estimated reading time: 30 minutes_

Dependency Injection (DI) is a design pattern that implements Inversion of Control (IoC) by injecting dependencies
rather than creating them internally. Neuroglia provides a comprehensive DI container that manages service registration,
lifetime, and resolution, demonstrated through **Mario's Pizzeria** implementation.

## 💡 What & Why

### ❌ The Problem: Tight Coupling and Hard-to-Test Code

When classes create their own dependencies directly, they become tightly coupled and difficult to test:

```python
# ❌ PROBLEM: Tight coupling with hardcoded dependencies
from pymongo import MongoClient

class OrderService:
    def __init__(self):
        # Creating dependencies directly = TIGHT COUPLING!
        self.mongo_client = MongoClient("mongodb://localhost:27017")
        self.db = self.mongo_client.pizzeria
        self.email_service = EmailService("smtp.gmail.com", 587)
        self.payment_gateway = StripePaymentGateway("sk_live_secret_key")
        self.logger = FileLogger("/var/log/orders.log")

    async def create_order(self, customer_id: str, items: List[dict]):
        # Use hardcoded dependencies
        order = Order(customer_id, items)
        await self.db.orders.insert_one(order.__dict__)
        await self.email_service.send_confirmation(order)
        return order

# Problems with this approach:
# ❌ Cannot test without real MongoDB, SMTP, Stripe, file system
# ❌ Cannot swap implementations (e.g., test email service)
# ❌ Configuration hardcoded in constructor
# ❌ Difficult to change database or payment provider
# ❌ Violates Single Responsibility Principle
# ❌ Cannot reuse service with different dependencies

# Testing is a NIGHTMARE:
class TestOrderService:
    def test_create_order(self):
        # Need REAL MongoDB running!
        # Need REAL SMTP server!
        # Need REAL Stripe account!
        # Need file system write permissions!
        service = OrderService()
        # This test hits REAL external systems - TERRIBLE!
        result = await service.create_order("customer-123", [])
```

**Problems with Tight Coupling:**

- ❌ **Untestable**: Cannot mock dependencies for unit testing
- ❌ **Inflexible**: Hard to swap implementations (e.g., MongoDB → PostgreSQL)
- ❌ **Configuration Hell**: Connection strings and keys hardcoded
- ❌ **Violates SRP**: Service creates AND uses dependencies
- ❌ **Difficult to Maintain**: Changes ripple through codebase
- ❌ **No Reusability**: Cannot reuse service in different contexts

### ✅ The Solution: Dependency Injection with IoC Container

Inject dependencies through constructors, allowing flexibility and testability:

```python
# ✅ SOLUTION: Dependency Injection with interfaces and IoC container
from abc import ABC, abstractmethod
from neuroglia.dependency_injection import ServiceCollection, ServiceLifetime

# Define interfaces (contracts)
class IOrderRepository(ABC):
    @abstractmethod
    async def save_async(self, order: Order):
        pass

    @abstractmethod
    async def get_by_id_async(self, order_id: str) -> Order:
        pass

class IEmailService(ABC):
    @abstractmethod
    async def send_confirmation_async(self, order: Order):
        pass

class IPaymentGateway(ABC):
    @abstractmethod
    async def process_payment_async(self, amount: Decimal) -> str:
        pass

# Service receives dependencies through constructor
class OrderService:
    def __init__(self,
                 order_repository: IOrderRepository,
                 email_service: IEmailService,
                 payment_gateway: IPaymentGateway,
                 logger: ILogger):
        # Dependencies injected, not created!
        self.order_repository = order_repository
        self.email_service = email_service
        self.payment_gateway = payment_gateway
        self.logger = logger

    async def create_order(self, customer_id: str, items: List[dict]):
        try:
            # Create order
            order = Order(customer_id, items)

            # Process payment
            transaction_id = await self.payment_gateway.process_payment_async(order.total)
            order.mark_as_paid(transaction_id)

            # Save order
            await self.order_repository.save_async(order)

            # Send confirmation
            await self.email_service.send_confirmation_async(order)

            self.logger.info(f"Order {order.id} created successfully")
            return order

        except Exception as ex:
            self.logger.error(f"Failed to create order: {ex}")
            raise

# Real implementations
class MongoOrderRepository(IOrderRepository):
    def __init__(self, mongo_client: MongoClient):
        self.collection = mongo_client.pizzeria.orders

    async def save_async(self, order: Order):
        await self.collection.insert_one(order.__dict__)

    async def get_by_id_async(self, order_id: str) -> Order:
        doc = await self.collection.find_one({"id": order_id})
        return Order.from_dict(doc)

class SmtpEmailService(IEmailService):
    def __init__(self, smtp_config: SmtpConfig):
        self.config = smtp_config

    async def send_confirmation_async(self, order: Order):
        # Send email via SMTP
        pass

class StripePaymentGateway(IPaymentGateway):
    def __init__(self, stripe_config: StripeConfig):
        self.config = stripe_config

    async def process_payment_async(self, amount: Decimal) -> str:
        # Process payment via Stripe
        return "txn_abc123"

# Configure DI container
services = ServiceCollection()

# Register dependencies with appropriate lifetimes
services.add_singleton(MongoClient, lambda: MongoClient("mongodb://localhost:27017"))
services.add_scoped(IOrderRepository, MongoOrderRepository)
services.add_singleton(IEmailService, SmtpEmailService)
services.add_singleton(IPaymentGateway, StripePaymentGateway)
services.add_singleton(ILogger, FileLogger)
services.add_scoped(OrderService)

# Build provider
provider = services.build_provider()

# Resolve service (all dependencies injected automatically!)
order_service = provider.get_service(OrderService)
await order_service.create_order("customer-123", items)

# Testing is now EASY with mocks!
class TestOrderService:
    def setup_method(self):
        # Create mock dependencies
        self.mock_repository = Mock(spec=IOrderRepository)
        self.mock_email = Mock(spec=IEmailService)
        self.mock_payment = Mock(spec=IPaymentGateway)
        self.mock_logger = Mock(spec=ILogger)

        # Inject mocks into service
        self.service = OrderService(
            self.mock_repository,
            self.mock_email,
            self.mock_payment,
            self.mock_logger
        )

    async def test_create_order_success(self):
        # Configure mock behavior
        self.mock_payment.process_payment_async.return_value = "txn_123"

        # Test with NO external dependencies!
        order = await self.service.create_order("customer-123", [
            {"name": "Margherita", "price": 12.99}
        ])

        # Verify interactions
        assert order is not None
        self.mock_repository.save_async.assert_called_once()
        self.mock_email.send_confirmation_async.assert_called_once()
        self.mock_payment.process_payment_async.assert_called_once()

# Swapping implementations is EASY!
# Want to use PostgreSQL instead of MongoDB?
services.add_scoped(IOrderRepository, PostgresOrderRepository)

# Want to use SendGrid instead of SMTP?
services.add_singleton(IEmailService, SendGridEmailService)

# Want test implementations for development?
if config.environment == "development":
    services.add_singleton(IPaymentGateway, FakePaymentGateway)
    services.add_singleton(IEmailService, ConsoleEmailService)
```

**Benefits of Dependency Injection:**

- ✅ **Testability**: Easy to mock dependencies for unit tests
- ✅ **Flexibility**: Swap implementations without changing code
- ✅ **Separation of Concerns**: Service uses dependencies, doesn't create them
- ✅ **Configuration**: Centralized service registration
- ✅ **Reusability**: Same service works with different dependencies
- ✅ **Maintainability**: Changes isolated to service registration
- ✅ **Follows SOLID**: Dependency Inversion Principle

## 🎯 Pattern Overview

Dependency Injection addresses common software design problems by:

- **Decoupling Components**: Services don't create their dependencies directly
- **Enabling Testability**: Dependencies can be easily mocked or stubbed
- **Managing Lifetimes**: Container controls when services are created and disposed
- **Configuration Flexibility**: Swap implementations without code changes
- **Cross-cutting Concerns**: Centralized service configuration and management

### Core Concepts

| Concept                   | Purpose                                | Mario's Pizzeria Example                                         |
| ------------------------- | -------------------------------------- | ---------------------------------------------------------------- |
| **ServiceCollection**     | Registry for service definitions       | Pizzeria's service catalog of all available services             |
| **ServiceProvider**       | Container for resolving services       | Kitchen coordinator that provides the right service when needed  |
| **ServiceLifetime**       | Controls service creation and disposal | Equipment usage patterns (shared vs per-order vs per-use)        |
| **Interface Abstraction** | Contracts for service implementations  | `IOrderRepository` with File, MongoDB, or Memory implementations |

## 🏗️ Service Lifetime Patterns

Understanding service lifetimes is crucial for proper resource management and performance:

### Singleton - Shared Infrastructure

**Pattern**: One instance for the entire application lifetime

```python
from neuroglia.dependency_injection import ServiceCollection

services = ServiceCollection()

# Shared infrastructure services
services.add_singleton(DatabaseConnection)      # Connection pool shared across all requests
services.add_singleton(MenuCacheService)        # Menu data cached for all customers
services.add_singleton(KitchenDisplayService)   # Single kitchen display system
services.add_singleton(PaymentGateway)          # Shared payment processing service
services.add_singleton(NotificationService)     # Single SMS/email service instance
```

**When to Use**:

- Database connection pools
- Caching services
- External API clients
- Configuration services
- Logging services

**Benefits**: Memory efficiency, shared state, connection pooling
**Risks**: Thread safety required, potential memory leaks if not disposed

### Scoped - Request Lifecycle

**Pattern**: One instance per scope (typically per HTTP request or business operation)

```python
# Per-request/per-operation services
services.add_scoped(OrderRepository)           # Order data access for this request
services.add_scoped(OrderProcessingService)    # Business logic for current order
services.add_scoped(CustomerContextService)    # Customer-specific request context
services.add_scoped(KitchenWorkflowService)    # Kitchen operations for this order
```

**When to Use**:

- Repository instances
- Business service instances
- User context services
- Request-specific caching
- Database transactions

**Benefits**: Request isolation, automatic cleanup, consistent state within scope
**Risks**: Higher memory usage than singleton

### Transient - Stateless Operations

**Pattern**: New instance every time the service is requested

```python
# Stateless calculation and validation services
services.add_transient(PizzaPriceCalculator)    # Fresh calculation each time
services.add_transient(DeliveryTimeEstimator)   # Stateless time calculations
services.add_transient(LoyaltyPointsCalculator) # Independent point calculations
services.add_transient(OrderValidator)          # Fresh validation each time
```

**When to Use**:

- Stateless calculators
- Validators
- Formatters
- Short-lived operations
- Thread-unsafe services

**Benefits**: No shared state issues, always fresh instance
**Risks**: Highest memory and CPU overhead

## 🔧 Registration Patterns

### Interface-Based Registration

**Pattern**: Register services by their abstractions to enable flexibility and testing

```python
from abc import ABC, abstractmethod
from typing import List, Optional

# Define contract
class IOrderRepository(ABC):
    @abstractmethod
    async def save_async(self, order: Order) -> None:
        pass

    @abstractmethod
    async def get_by_id_async(self, order_id: str) -> Optional[Order]:
        pass

    @abstractmethod
    async def get_by_status_async(self, status: str) -> List[Order]:
        pass

# Multiple implementations
class FileOrderRepository(IOrderRepository):
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    async def save_async(self, order: Order) -> None:
        file_path = self.data_dir / f"{order.id}.json"
        with open(file_path, 'w') as f:
            json.dump(order.__dict__, f, default=str)

class MongoOrderRepository(IOrderRepository):
    def __init__(self, mongo_client: MongoClient):
        self.collection = mongo_client.pizzeria.orders

    async def save_async(self, order: Order) -> None:
        await self.collection.replace_one(
            {"_id": order.id},
            order.__dict__,
            upsert=True
        )

# Register by interface - easy to swap implementations
services.add_scoped(IOrderRepository, FileOrderRepository)  # Development
# services.add_scoped(IOrderRepository, MongoOrderRepository)  # Production
```

### Factory Pattern Registration

**Pattern**: Use factory functions for complex service initialization

```python
def create_payment_gateway() -> IPaymentGateway:
    """Factory creates payment gateway based on configuration"""
    config = get_payment_config()

    if config.environment == "development":
        return MockPaymentGateway()
    elif config.provider == "stripe":
        return StripePaymentGateway(config.stripe_api_key)
    else:
        return SquarePaymentGateway(config.square_token)

def create_notification_service() -> INotificationService:
    """Factory creates notification service with proper credentials"""
    settings = get_app_settings()

    return TwilioNotificationService(
        account_sid=settings.twilio_sid,
        auth_token=settings.twilio_token,
        from_number=settings.pizzeria_phone
    )

# Register with factories
services.add_singleton(IPaymentGateway, factory=create_payment_gateway)
services.add_singleton(INotificationService, factory=create_notification_service)
```

### Generic Repository Pattern

**Pattern**: Generic repository implementation for multiple entity types

```python
from typing import TypeVar, Generic
from neuroglia.data.abstractions import Repository

T = TypeVar('T')
TKey = TypeVar('TKey')

class FileRepository(Repository[T, TKey], Generic[T, TKey]):
    """Generic file-based repository for any entity type"""

    def __init__(self, entity_type: type, data_dir: str = "data"):
        self.entity_type = entity_type
        self.data_dir = Path(data_dir) / entity_type.__name__.lower()
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def save_async(self, entity: T) -> None:
        file_path = self.data_dir / f"{entity.id}.json"
        with open(file_path, 'w') as f:
            json.dump(entity.__dict__, f, default=str)

# Factory functions for type-safe registration
def create_pizza_repository() -> Repository[Pizza, str]:
    return FileRepository(Pizza, "data")

def create_order_repository() -> Repository[Order, str]:
    return FileRepository(Order, "data")

# Register generic repositories
services.add_scoped(Repository[Pizza, str], factory=create_pizza_repository)
services.add_scoped(Repository[Order, str], factory=create_order_repository)
```

## 🎯 Constructor Injection Pattern

**Pattern**: Dependencies are provided through constructor parameters

```python
class OrderService:
    """Service with injected dependencies"""

    def __init__(self,
                 order_repository: IOrderRepository,
                 payment_service: IPaymentService,
                 notification_service: INotificationService,
                 mapper: IMapper):
        self.order_repository = order_repository
        self.payment_service = payment_service
        self.notification_service = notification_service
        self.mapper = mapper

    async def place_order_async(self, order_dto: OrderDto) -> OperationResult[OrderDto]:
        # Dependencies injected automatically
        order = self.mapper.map(order_dto, Order)

        # Process payment using injected service
        payment_result = await self.payment_service.process_payment_async(order.total)
        if not payment_result.success:
            return OperationResult.bad_request("Payment failed")

        # Save using injected repository
        await self.order_repository.save_async(order)

        # Send notification using injected service
        await self.notification_service.send_confirmation_async(order)

        return OperationResult.ok(self.mapper.map(order, OrderDto))

class OrderController(ControllerBase):
    """Controller with service injection"""

    def __init__(self,
                 service_provider: ServiceProvider,
                 mapper: IMapper,
                 mediator: IMediator):
        super().__init__(service_provider, mapper, mediator)
        # Dependencies resolved automatically by framework
```

## 🧪 Testing with Dependency Injection

**Pattern**: Easy mocking and testing through dependency injection

```python
import pytest
from unittest.mock import Mock, AsyncMock

class TestOrderService:
    """Test class demonstrating DI testing benefits"""

    def setup_method(self):
        # Create mocks for all dependencies
        self.order_repository = Mock(spec=IOrderRepository)
        self.payment_service = Mock(spec=IPaymentService)
        self.notification_service = Mock(spec=INotificationService)
        self.mapper = Mock(spec=IMapper)

        # Inject mocks into service
        self.order_service = OrderService(
            self.order_repository,
            self.payment_service,
            self.notification_service,
            self.mapper
        )

    @pytest.mark.asyncio
    async def test_place_order_success(self):
        # Arrange - setup mock behaviors
        order_dto = OrderDto(customer_name="Test", total=25.99)
        order = Order(id="123", customer_name="Test", total=25.99)

        self.mapper.map.return_value = order
        self.payment_service.process_payment_async = AsyncMock(
            return_value=PaymentResult(success=True)
        )
        self.order_repository.save_async = AsyncMock()
        self.notification_service.send_confirmation_async = AsyncMock()

        # Act
        result = await self.order_service.place_order_async(order_dto)

        # Assert
        assert result.is_success
        self.payment_service.process_payment_async.assert_called_once_with(25.99)
        self.order_repository.save_async.assert_called_once_with(order)
        self.notification_service.send_confirmation_async.assert_called_once_with(order)
```

## 🚀 Advanced Patterns

### Service Locator Anti-Pattern

**❌ Avoid**: Service Locator pattern hides dependencies

```python
# BAD - Service Locator hides dependencies
class OrderService:
    def process_order(self, order_dto: OrderDto):
        # Hidden dependencies - hard to test and understand
        repository = ServiceLocator.get(IOrderRepository)
        payment = ServiceLocator.get(IPaymentService)
        # ... rest of implementation
```

**✅ Prefer**: Constructor Injection makes dependencies explicit

```python
# GOOD - Dependencies are explicit and testable
class OrderService:
    def __init__(self,
                 repository: IOrderRepository,
                 payment: IPaymentService):
        self.repository = repository
        self.payment = payment
```

### Configuration-Based Registration

**Pattern**: Configure services based on environment or settings

```python
def configure_services(services: ServiceCollection, environment: str):
    """Configure services based on environment"""

    # Always register core abstractions
    services.add_transient(IMapper, AutoMapper)
    services.add_scoped(IOrderService, OrderService)

    # Environment-specific implementations
    if environment == "development":
        services.add_scoped(IOrderRepository, FileOrderRepository)
        services.add_singleton(IPaymentService, MockPaymentService)
        services.add_singleton(INotificationService, ConsoleNotificationService)

    elif environment == "testing":
        services.add_scoped(IOrderRepository, InMemoryOrderRepository)
        services.add_singleton(IPaymentService, MockPaymentService)
        services.add_singleton(INotificationService, NoOpNotificationService)

    elif environment == "production":
        services.add_scoped(IOrderRepository, MongoOrderRepository)
        services.add_singleton(IPaymentService, StripePaymentService)
        services.add_singleton(INotificationService, TwilioNotificationService)
```

## 🔗 Integration with Other Patterns

### DI + CQRS Pattern

```python
# Command handlers with injected dependencies
class PlaceOrderHandler(ICommandHandler[PlaceOrderCommand, OperationResult]):
    def __init__(self,
                 order_repository: IOrderRepository,
                 payment_service: IPaymentService):
        self.order_repository = order_repository
        self.payment_service = payment_service

    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult:
        # Implementation uses injected dependencies
        pass

# Register handlers
services.add_scoped(ICommandHandler[PlaceOrderCommand, OperationResult], PlaceOrderHandler)
```

### DI + Repository Pattern

```python
# Repository with injected infrastructure dependencies
class OrderRepository(IOrderRepository):
    def __init__(self,
                 mongo_client: MongoClient,
                 logger: ILogger,
                 cache: ICache):
        self.collection = mongo_client.pizzeria.orders
        self.logger = logger
        self.cache = cache
```

## ⚠️ Common Mistakes

### 1. **Service Locator Anti-Pattern**

```python
# ❌ WRONG: Service Locator (anti-pattern)
class OrderService:
    def __init__(self, service_locator: ServiceProvider):
        # Service locator is DI's evil twin!
        self.service_locator = service_locator

    async def create_order(self, customer_id: str):
        # Hides dependencies - what does this service need?
        repository = self.service_locator.get_service(IOrderRepository)
        email = self.service_locator.get_service(IEmailService)
        payment = self.service_locator.get_service(IPaymentGateway)
        # Dependencies are HIDDEN!

# ✅ CORRECT: Constructor injection (explicit dependencies)
class OrderService:
    def __init__(self,
                 order_repository: IOrderRepository,
                 email_service: IEmailService,
                 payment_gateway: IPaymentGateway):
        # Dependencies are EXPLICIT and visible!
        self.order_repository = order_repository
        self.email_service = email_service
        self.payment_gateway = payment_gateway
```

### 2. **Incorrect Service Lifetimes**

```python
# ❌ WRONG: Database connection as transient (creates new connection every time!)
services.add_transient(MongoClient, lambda: MongoClient("mongodb://localhost"))
# This creates a NEW MongoDB connection for EVERY service that needs it!

# ❌ WRONG: Request-specific service as singleton (shared across all requests!)
services.add_singleton(CurrentUserService)
# This shares the SAME user across all requests!

# ✅ CORRECT: Appropriate lifetimes
services.add_singleton(MongoClient, lambda: MongoClient("mongodb://localhost"))
services.add_scoped(CurrentUserService)  # One per request
services.add_transient(OrderValidator)   # Stateless, new instance each time
```

### 3. **Circular Dependencies**

```python
# ❌ WRONG: Circular dependency (A needs B, B needs A)
class OrderService:
    def __init__(self, customer_service: CustomerService):
        self.customer_service = customer_service

class CustomerService:
    def __init__(self, order_service: OrderService):
        self.order_service = order_service  # Circular!

# ✅ CORRECT: Extract shared logic or use events
class OrderService:
    def __init__(self, customer_repository: ICustomerRepository):
        self.customer_repository = customer_repository

class CustomerService:
    def __init__(self, customer_repository: ICustomerRepository):
        self.customer_repository = customer_repository

# Both use repository, no circular dependency!
```

### 4. **Not Using Interfaces**

```python
# ❌ WRONG: Depending on concrete implementations
class OrderService:
    def __init__(self, mongo_repository: MongoOrderRepository):
        # Coupled to MongoDB implementation!
        self.repository = mongo_repository

# ✅ CORRECT: Depend on abstractions
class OrderService:
    def __init__(self, order_repository: IOrderRepository):
        # Can use ANY repository implementation!
        self.repository = order_repository

# Register concrete implementation
services.add_scoped(IOrderRepository, MongoOrderRepository)
# Easy to swap: services.add_scoped(IOrderRepository, PostgresOrderRepository)
```

### 5. **Fat Constructors (Too Many Dependencies)**

```python
# ❌ WRONG: Service with too many dependencies (code smell!)
class OrderService:
    def __init__(self,
                 order_repository: IOrderRepository,
                 customer_repository: ICustomerRepository,
                 product_repository: IProductRepository,
                 payment_gateway: IPaymentGateway,
                 email_service: IEmailService,
                 sms_service: ISmsService,
                 inventory_service: IInventoryService,
                 loyalty_service: ILoyaltyService,
                 analytics_service: IAnalyticsService,
                 audit_service: IAuditService):
        # 10 dependencies = this class does TOO MUCH!
        pass

# ✅ CORRECT: Split into focused services
class OrderService:
    def __init__(self,
                 order_repository: IOrderRepository,
                 order_processor: IOrderProcessor):
        # Delegate to specialized services
        self.repository = order_repository
        self.processor = order_processor

class OrderProcessor:
    def __init__(self,
                 payment_gateway: IPaymentGateway,
                 notification_service: INotificationService):
        # Focused responsibility
        self.payment = payment_gateway
        self.notifications = notification_service
```

### 6. **Not Disposing Resources**

```python
# ❌ WRONG: Not disposing scoped services
async def handle_request():
    provider = services.build_provider()
    service = provider.get_service(OrderService)
    await service.create_order(...)
    # Provider never disposed - resource leak!

# ✅ CORRECT: Dispose scoped services properly
async def handle_request():
    scope = services.create_scope()
    try:
        service = scope.service_provider.get_service(OrderService)
        await service.create_order(...)
    finally:
        scope.dispose()  # Clean up resources!
```

## 🚫 When NOT to Use

### 1. **Simple Scripts and Utilities**

```python
# DI adds unnecessary complexity for simple scripts
class DataMigrationScript:
    """One-time data migration script"""
    def run(self):
        # Just create what you need directly
        source_db = MongoClient("mongodb://localhost:27017")
        target_db = PostgresClient("postgresql://localhost:5432")

        # No need for DI container for a simple script
        data = source_db.old_db.collection.find()
        for item in data:
            target_db.new_db.table.insert(item)
```

### 2. **Framework Entry Points (Already Have DI)**

```python
# FastAPI already has dependency injection built-in
from fastapi import Depends

@app.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    repository: IOrderRepository = Depends(get_order_repository)
):
    # FastAPI's Depends() is DI - don't add Neuroglia DI on top
    return await repository.get_by_id_async(order_id)
```

### 3. **Value Objects and DTOs**

```python
# Value objects shouldn't use DI - they should be simple data
@dataclass
class Address:
    """Simple value object - no dependencies needed"""
    street: str
    city: str
    zip_code: str

    # No constructor injection - just data!
```

### 4. **Static Utility Classes**

```python
# Static utilities don't need DI
class StringUtils:
    """Stateless utility functions"""
    @staticmethod
    def to_kebab_case(text: str) -> str:
        return text.lower().replace("_", "-")

    # No dependencies, no state, no need for DI
```

### 5. **Very Small Applications (< 100 lines)**

```python
# For tiny apps, DI is overkill
class TinyBot:
    """Simple Discord bot with 3 commands"""
    def __init__(self):
        # Just create what you need
        self.client = discord.Client()
        self.commands = ["!help", "!ping", "!joke"]

    # No need for DI container for such a small app
```

## 📝 Key Takeaways

- **Dependency Injection inverts control**: Dependencies injected, not created internally
- **Use constructor injection** for explicit, testable dependencies
- **Register services with appropriate lifetimes**: Singleton, Scoped, or Transient
- **Depend on abstractions (interfaces)**, not concrete implementations
- **Service Locator is an anti-pattern** - use constructor injection instead
- **Avoid circular dependencies** - extract shared logic or use events
- **Fat constructors indicate too many responsibilities** - split services
- **DI enables testability** by allowing easy mocking
- **Framework provides ServiceCollection and ServiceProvider** for DI management
- **Dispose scoped services properly** to prevent resource leaks

## 📚 Related Patterns

- **[🎯 CQRS Pattern](cqrs.md)** - Command and query handlers use DI for dependencies
- **[💾 Repository Pattern](repository.md)** - Repositories are registered and injected as services
- **[🔄 Event-Driven Pattern](event-driven.md)** - Event handlers use DI for their dependencies
- **[🏗️ Clean Architecture](clean-architecture.md)** - DI enables layer separation and dependency inversion

---

_Dependency Injection is fundamental to building testable, maintainable applications. Mario's Pizzeria demonstrates how proper DI patterns enable flexible architecture and easy testing._
