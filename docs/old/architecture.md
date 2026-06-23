# 🏗️ Architecture Guide

<!-- markdownlint-disable MD046 -->

!!! danger "⚠️ Deprecated"

    This page is deprecated and will be removed in a future version. The content has been migrated to more focused sections:

    - **[Clean Architecture Pattern](patterns/clean-architecture.md)** - Four-layer separation and dependency rules
    - **[CQRS Pattern](patterns/cqrs.md)** - Command Query Responsibility Segregation
    - **[Event-Driven Pattern](patterns/event-driven.md)** - Domain events and messaging
    - **[Mario's Pizzeria](mario-pizzeria.md)** - Complete bounded context example
    - **[Features](features/index.md)** - Framework-specific implementation details

    Please use the new structure for the most up-to-date documentation.

Neuroglia's clean architecture is demonstrated through **Mario's Pizzeria**, showing how layered architecture promotes separation of concerns, testability, and maintainability in a real-world application.

## 🎯 What You'll Learn

- **Clean Architecture Layers**: How Mario's Pizzeria separates concerns across API, Application, Domain, and Integration layers
- **Dependency Flow**: How pizza order workflow demonstrates the dependency rule in practice
- **CQRS Implementation**: How command and query separation works in kitchen operations
- **Event-Driven Design**: How domain events coordinate between pizza preparation and customer notifications
- **Testing Strategy**: How architecture enables comprehensive testing at every layer

## 🍕 Mario's Pizzeria Architecture

### Overview: From Order to Pizza

Mario's Pizzeria demonstrates clean architecture through the complete pizza ordering and preparation workflow:

```text
┌─────────────────────────────────────────────────┐
│            🌐 API Layer (Controllers)           │  ← Customer & Staff Interface
│   OrdersController │ MenuController │ Kitchen   │
│   Authentication   │ Error Handling │ Swagger   │
└─────────────────────┬───────────────────────────┘
                      │ orchestrates
┌─────────────────────▼───────────────────────────┐
│       💼 Application Layer (CQRS + Events)      │  ← Business Workflow
│  PlaceOrderCommand │ GetMenuQuery │ Handlers    │
│  OrderPlacedEvent  │ Kitchen Workflow Pipeline  │
└─────────────────────┬───────────────────────────┘
                      │ uses
┌─────────────────────▼───────────────────────────┐
│         🏛️ Domain Layer (Business Logic)        │  ← Pizza Business Rules
│    Order Entity    │    Pizza Entity           │
│  Kitchen Workflow  │  Pricing Rules            │
│   Domain Events    │  Business Validation      │
└─────────────────────▲───────────────────────────┘
                      │ implements
┌─────────────────────┴───────────────────────────┐
│      🔌 Integration Layer (External Systems)    │  ← Data & External APIs
│  Order Repository  │  Payment Gateway          │
│   File Storage     │  MongoDB │ Event Store    │
│  SMS Notifications │  Email Service            │
└─────────────────────────────────────────────────┘
```

### The Dependency Rule in Action

Pizza order flow demonstrates how dependencies always point inward:

1. **API Layer** → Application Layer: Controller calls `PlaceOrderCommand`
2. **Application Layer** → Domain Layer: Handler uses `Order` entity business logic
3. **Integration Layer** → Domain Layer: Repository implements domain `IOrderRepository` interface
4. **Never**: Domain layer doesn't know about API controllers or database implementation

## 🏢 Layer Details with Pizza Examples

### 📡 API Layer: Customer & Staff Interface

**Purpose**: External interface for Mario's Pizzeria operations

**Responsibilities**:

- HTTP endpoints for orders, menu, kitchen operations
- Customer and staff authentication (OAuth 2.0)
- Request validation and error handling
- OpenAPI documentation generation

**Key Components**:

```python
# src/api/controllers/orders_controller.py
class OrdersController(ControllerBase):
    """Handle customer pizza orders"""

    @post("/", response_model=OrderDto, status_code=201)
    async def place_order(self, order_request: PlaceOrderDto) -> OrderDto:
        """Place new pizza order"""
        command = PlaceOrderCommand(
            customer_name=order_request.customer_name,
            customer_phone=order_request.customer_phone,
            pizzas=order_request.pizzas,
            payment_method=order_request.payment_method
        )

        result = await self.mediator.execute_async(command)
        return self.process(result)  # Framework handles success/error response

# src/api/dtos/order_dto.py
class PlaceOrderDto(BaseModel):
    """Request DTO for placing pizza orders"""
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., regex=r"^\+?1?[2-9]\d{9}$")
    customer_address: str = Field(..., min_length=10, max_length=200)
    pizzas: List[PizzaOrderDto] = Field(..., min_items=1, max_items=20)
    payment_method: str = Field(..., regex="^(cash|card|online)$")
```

**Architecture Benefits**:

- **Framework Independence**: Pure business logic with no external dependencies

### 🔌 Integration Layer: External Systems

**Purpose**: Handles external system interactions and data persistence

**Responsibilities**:

- Data persistence (file storage, MongoDB, event store)
- External API integration (payment, notifications)
- Infrastructure concerns (caching, logging)
- Implements domain interfaces

**Integration Components**:

```python
# src/integration/repositories/file_order_repository.py
class FileOrderRepository(IOrderRepository):
    """File-based order repository for development"""

    def __init__(self, orders_directory: str = "data/orders"):
        self.orders_directory = Path(orders_directory)
        self.orders_directory.mkdir(parents=True, exist_ok=True)

    async def save_async(self, order: Order) -> Order:
        """Save order to JSON file"""
        order_file = self.orders_directory / f"{order.id}.json"

        order_data = {
            "id": order.id,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_address": order.customer_address,
            "pizzas": [self._pizza_to_dict(pizza) for pizza in order.pizzas],
            "status": order.status.value,
            "order_time": order.order_time.isoformat(),
            "total_amount": float(order.total_amount)
        }

        async with aiofiles.open(order_file, 'w') as f:
            await f.write(json.dumps(order_data, indent=2))

        return order

# src/integration/services/payment_service.py
class StripePaymentService(IPaymentService):
    """Payment processing using Stripe API"""

    async def process_payment_async(self,
                                    amount: Decimal,
                                    payment_method: str) -> PaymentResult:
        """Process payment through Stripe"""
        try:
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency="usd",
                payment_method=payment_method,
                confirm=True,
                return_url="https://marios-pizzeria.com/payment-success"
            )

            return PaymentResult(
                is_success=True,
                transaction_id=intent.id,
                amount_processed=amount
            )

        except stripe.error.StripeError as e:
            return PaymentResult(
                is_success=False,
                error_message=str(e)
            )

# src/integration/services/notification_service.py
class TwilioNotificationService(INotificationService):
    """SMS notifications using Twilio"""

    async def send_order_confirmation_async(self, order: Order) -> None:
        """Send order confirmation SMS"""
        from twilio.rest import Client

        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )

        message = (f"Hi {order.customer_name}! Your pizza order #{order.id} "
                  f"has been confirmed. Total: ${order.total_amount}. "
                  f"Estimated ready time: {order.estimated_ready_time.strftime('%I:%M %p')}")

        await client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=order.customer_phone
        )

    async def send_order_ready_notification_async(self, order: Order) -> None:
        """Send order ready SMS"""
        message = (f"🍕 Your order #{order.id} is ready for pickup at Mario's Pizzeria! "
                  f"Please arrive within 15 minutes to keep your pizzas hot.")

        # Implementation details...
```

## 🎯 CQRS Implementation in Mario's Pizzeria

### Command and Query Separation

Mario's Pizzeria demonstrates CQRS (Command Query Responsibility Segregation):

```python
# Commands: Change state (Write operations)
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    """Command to place new pizza order"""
    pass

class UpdateOrderStatusCommand(Command[OperationResult[OrderDto]]):
    """Command to update order status in kitchen"""
    pass

class CancelOrderCommand(Command[OperationResult[OrderDto]]):
    """Command to cancel existing order"""
    pass

# Queries: Read state (Read operations)
class GetOrderByIdQuery(Query[OrderDto]):
    """Query to get specific order details"""
    pass

class GetKitchenQueueQuery(Query[List[KitchenOrderDto]]):
    """Query to get orders in kitchen preparation queue"""
    pass

class GetMenuQuery(Query[List[PizzaDto]]):
    """Query to get available pizza menu"""
    pass
```

### Benefits of CQRS in Pizzeria Context

**Write Side (Commands)**:

- **Order Placement**: Validates business rules, processes payments
- **Kitchen Operations**: Updates order status, manages workflow
- **Menu Management**: Updates pizza availability, pricing

**Read Side (Queries)**:

- **Customer App**: Fast menu browsing, order tracking
- **Kitchen Display**: Real-time queue updates
- **Analytics**: Revenue reports, performance metrics

**Separate Optimization**:

- Commands use MongoDB for ACID transactions
- Queries use optimized read models for fast retrieval
- Analytics use event store for historical data

## 📊 Event-Driven Architecture

### Domain Events in Pizza Workflow

Events coordinate between different parts of Mario's Pizzeria:

```python
# Domain events flow through the system
OrderPlacedEvent → KitchenNotificationHandler → Kitchen Display Update
                ↘ CustomerConfirmationHandler → SMS Confirmation
                ↘ InventoryHandler → Update Pizza Availability

OrderReadyEvent → CustomerNotificationHandler → "Order Ready" SMS
               ↘ DeliveryScheduleHandler → Schedule Delivery

OrderCompletedEvent → AnalyticsHandler → Update Revenue Metrics
                   ↘ CustomerHistoryHandler → Update Customer Profile
```

### Event Handler Examples

```python
class KitchenNotificationHandler(EventHandler[OrderPlacedEvent]):
    """Update kitchen display when new order placed"""

    async def handle_async(self, event: OrderPlacedEvent):
        # Add order to kitchen queue
        command = AddToKitchenQueueCommand(
            order_id=event.order_id,
            estimated_ready_time=event.estimated_ready_time
        )
        await self.mediator.execute_async(command)

class CustomerNotificationHandler(EventHandler[OrderReadyEvent]):
    """Notify customer when order is ready"""

    async def handle_async(self, event: OrderReadyEvent):
        # Send SMS notification
        await self.notification_service.send_order_ready_notification_async(
            order_id=event.order_id,
            customer_phone=event.customer_phone
        )

class RevenueAnalyticsHandler(EventHandler[OrderCompletedEvent]):
    """Update revenue analytics when order completed"""

    async def handle_async(self, event: OrderCompletedEvent):
        # Update daily revenue
        command = UpdateDailyRevenueCommand(
            date=event.completed_at.date(),
            amount=event.total_amount,
            order_count=1
        )
        await self.mediator.execute_async(command)
```

## 🧪 Testing Strategy Across Layers

### Layer-Specific Testing Approaches

Each layer in Mario's Pizzeria has specific testing strategies:

**API Layer (Controllers)**:

- **Unit Tests**: Mock mediator, test HTTP status codes and response formatting
- **Integration Tests**: Test full HTTP request/response cycle with real dependencies
- **Contract Tests**: Validate request/response schemas match OpenAPI spec

```python
@pytest.mark.asyncio
async def test_place_order_success(orders_controller, mock_mediator):
    """Test successful order placement through controller"""
    # Arrange
    order_request = PlaceOrderDto(
        customer_name="Test Customer",
        customer_phone="+1234567890",
        pizzas=[PizzaOrderDto(name="Margherita", size="large", quantity=1)]
    )

    expected_order = OrderDto(id="order_123", status="received")
    mock_mediator.execute_async.return_value = OperationResult.success(expected_order)

    # Act
    result = await orders_controller.place_order(order_request)

    # Assert
    assert result.id == "order_123"
    assert result.status == "received"
```

**Application Layer (Handlers)**:

- **Unit Tests**: Mock all dependencies (repositories, external services)
- **Behavior Tests**: Verify business workflow logic and error handling
- **Event Tests**: Validate domain events are raised correctly

```python
@pytest.mark.asyncio
async def test_place_order_handler_workflow(mock_order_repo, mock_payment_service):
    """Test complete order placement workflow"""
    # Arrange
    handler = PlaceOrderCommandHandler(mock_order_repo, mock_payment_service, ...)
    command = PlaceOrderCommand(customer_name="Test", pizzas=[...])

    mock_payment_service.process_payment_async.return_value = PaymentResult(success=True)
    mock_order_repo.save_async.return_value = Order(id="order_123")

    # Act
    result = await handler.handle_async(command)

    # Assert
    assert result.is_success
    mock_payment_service.process_payment_async.assert_called_once()
    mock_order_repo.save_async.assert_called_once()
```

**Domain Layer (Entities & Services)**:

- **Unit Tests**: Pure business logic testing with no external dependencies
- **Business Rule Tests**: Validate invariants and business constraints
- **Event Tests**: Ensure domain events are raised for business-significant changes

```python
def test_order_total_calculation():
    """Test pizza order total calculation business logic"""
    # Arrange
    pizzas = [
        Pizza("Margherita", "large", ["extra_cheese"]),
        Pizza("Pepperoni", "medium", [])
    ]

    # Act
    order = Order.create_new("Customer", "+1234567890", "Address", pizzas, "card")

    # Assert
    expected_subtotal = Decimal("15.99") + Decimal("12.99")  # Pizza prices
    expected_tax = expected_subtotal * Decimal("0.0875")     # 8.75% tax
    expected_delivery = Decimal("2.99")                      # Delivery fee
    expected_total = expected_subtotal + expected_tax + expected_delivery

    assert order.total_amount == expected_total.quantize(Decimal("0.01"))

def test_order_status_transition_validation():
    """Test order status transition business rules"""
    # Arrange
    order = Order.create_new("Customer", "+1234567890", "Address", [], "card")

    # Act & Assert - Valid transition
    order.update_status(OrderStatus.PREPARING, "chef_mario")
    assert order.status == OrderStatus.PREPARING

    # Act & Assert - Invalid transition
    with pytest.raises(DomainException):
        order.update_status(OrderStatus.DELIVERED, "chef_mario")  # Cannot skip to delivered

def test_domain_events_raised():
    """Test that domain events are raised correctly"""
    # Arrange
    pizzas = [Pizza("Margherita", "large", [])]

    # Act
    order = Order.create_new("Customer", "+1234567890", "Address", pizzas, "card")

    # Assert
    events = order.get_uncommitted_events()
    assert len(events) == 1
    assert isinstance(events[0], OrderPlacedEvent)
    assert events[0].order_id == order.id
```

**Integration Layer (Repositories & Services)**:

- **Unit Tests**: Mock external dependencies (databases, APIs)
- **Integration Tests**: Test against real external systems in controlled environments
- **Contract Tests**: Validate external API integrations

```python
@pytest.mark.integration
async def test_file_order_repository_roundtrip():
    """Test saving and retrieving orders from file system"""
    # Arrange
    repository = FileOrderRepository("test_data/orders")
    order = Order.create_new("Test Customer", "+1234567890", "Test Address", [], "cash")

    # Act
    saved_order = await repository.save_async(order)
    retrieved_order = await repository.get_by_id_async(saved_order.id)

    # Assert
    assert retrieved_order is not None
    assert retrieved_order.customer_name == "Test Customer"
    assert retrieved_order.id == saved_order.id

@pytest.mark.integration
async def test_stripe_payment_service():
    """Test payment processing with Stripe (using test API keys)"""
    # Arrange
    payment_service = StripePaymentService()
    amount = Decimal("29.99")

    # Act
    result = await payment_service.process_payment_async(amount, "pm_card_visa")

    # Assert
    assert result.is_success
    assert result.amount_processed == amount
    assert result.transaction_id is not None
```

### End-to-End Testing

Full workflow testing across all layers:

```python
@pytest.mark.e2e
async def test_complete_pizza_order_workflow():
    """Test complete order workflow from API to persistence"""
    async with TestClient(create_pizzeria_app()) as client:
        # 1. Get menu
        menu_response = await client.get("/api/menu/pizzas")
        assert menu_response.status_code == 200

        # 2. Place order
        order_data = {
            "customer_name": "E2E Test Customer",
            "customer_phone": "+1234567890",
            "customer_address": "123 Test St",
            "pizzas": [{"name": "Margherita", "size": "large", "quantity": 1}],
            "payment_method": "card"
        }

        order_response = await client.post("/api/orders/", json=order_data)
        assert order_response.status_code == 201
        order = order_response.json()

        # 3. Update order status (kitchen)
        status_update = {"status": "preparing", "notes": "Started preparation"}
        status_response = await client.put(
            f"/api/kitchen/orders/{order['id']}/status",
            json=status_update,
            headers={"Authorization": "Bearer {kitchen_token}"}
        )
        assert status_response.status_code == 200

        # 4. Verify order status
        check_response = await client.get(f"/api/orders/{order['id']}")
        updated_order = check_response.json()
        assert updated_order["status"] == "preparing"
```

## 🛠️ Dependency Injection Configuration

### Service Registration for Mario's Pizzeria

```python
from neuroglia.hosting.web import WebApplicationBuilder

def configure_pizzeria_services(builder: WebApplicationBuilder):
    """Configure all services for Mario's Pizzeria"""

    # Domain services
    builder.services.add_scoped(KitchenWorkflowService)
    builder.services.add_scoped(PricingService)

    # Application services
    builder.services.add_mediator()
    builder.services.add_auto_mapper()

    # Infrastructure services (environment-specific)
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "development":
        # File-based repositories for development
        builder.services.add_scoped(IOrderRepository, FileOrderRepository)
        builder.services.add_scoped(IPizzaRepository, FilePizzaRepository)
        builder.services.add_scoped(INotificationService, ConsoleNotificationService)
        builder.services.add_scoped(IPaymentService, MockPaymentService)

    else:  # production
        # MongoDB repositories for production
        builder.services.add_scoped(IOrderRepository, MongoOrderRepository)
        builder.services.add_scoped(IPizzaRepository, MongoPizzaRepository)
        builder.services.add_scoped(INotificationService, TwilioNotificationService)
        builder.services.add_scoped(IPaymentService, StripePaymentService)

    # Event handlers
    builder.services.add_scoped(EventHandler[OrderPlacedEvent], KitchenNotificationHandler)
    builder.services.add_scoped(EventHandler[OrderReadyEvent], CustomerNotificationHandler)
    builder.services.add_scoped(EventHandler[OrderCompletedEvent], AnalyticsHandler)

    # Controllers
    builder.services.add_controllers([
        "api.controllers.orders_controller",
        "api.controllers.menu_controller",
        "api.controllers.kitchen_controller"
    ])
```

## 🚀 Benefits of This Architecture

### For Mario's Pizzeria Business

- **Scalability**: Can handle increasing order volume by scaling individual layers
- **Maintainability**: Business logic changes are isolated to domain layer
- **Testability**: Comprehensive testing at every layer ensures reliability
- **Flexibility**: Easy to change storage, payment providers, or notification methods
- **Team Productivity**: Clear boundaries enable parallel development

### For Development Teams

- **Clear Responsibilities**: Each layer has well-defined purpose and boundaries
- **Technology Independence**: Can swap infrastructure without changing business logic
- **Parallel Development**: Teams can work on different layers simultaneously
- **Easy Onboarding**: New developers understand system through consistent patterns

### For Long-Term Maintenance

- **Evolution Support**: Architecture supports changing business requirements
- **Technology Updates**: Infrastructure can be updated without business logic changes
- **Performance Optimization**: Each layer can be optimized independently
- **Monitoring & Debugging**: Clear separation aids in troubleshooting issues

## 🔗 Related Documentation

- [Getting Started Guide](getting-started.md) - Complete Mario's Pizzeria tutorial
- [CQRS & Mediation](../patterns/cqrs.md) - Command and query patterns in depth
- [Dependency Injection](../patterns/dependency-injection.md) - Service registration and DI patterns
- [MVC Controllers](features/mvc-controllers.md) - API layer implementation details
- [Data Access](features/data-access.md) - Repository patterns and data persistence
- [Source Code Naming Conventions](references/source_code_naming_convention.md) - Consistent naming across all architectural layers
- [12-Factor App Compliance](references/12-factor-app.md) - Cloud-native architecture principles with framework implementation

---

_This architecture guide demonstrates clean architecture principles using Mario's Pizzeria as a comprehensive
example. The layered approach shown here scales from simple applications to complex enterprise systems while
maintaining clear separation of concerns and testability._

### 💼 Application Layer: Pizza Business Workflow

**Purpose**: Orchestrates pizza business operations and workflows

**Responsibilities**:

- Command and query handling (CQRS)
- Business workflow coordination
- Domain event processing
- Cross-cutting concerns (logging, validation, caching)

**Key Components**:

```python
# src/application/commands/place_order_command.py
@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    """Command to place a pizza order"""
    customer_name: str
    customer_phone: str
    customer_address: str
    pizzas: List[PizzaOrderDto]
    payment_method: str

# src/application/handlers/place_order_handler.py
class PlaceOrderCommandHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    """Handles pizza order placement business workflow"""

    def __init__(self,
                 order_repository: IOrderRepository,
                 pizza_repository: IPizzaRepository,
                 payment_service: IPaymentService,
                 notification_service: INotificationService,
                 mapper: Mapper):
        self.order_repository = order_repository
        self.pizza_repository = pizza_repository
        self.payment_service = payment_service
        self.notification_service = notification_service
        self.mapper = mapper

    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
        """Execute pizza order placement workflow"""
        try:
            # 1. Validate pizzas are available
            for pizza_request in command.pizzas:
                pizza = await self.pizza_repository.get_by_name_async(pizza_request.name)
                if not pizza or not pizza.is_available:
                    return self.bad_request(f"Pizza '{pizza_request.name}' is not available")

            # 2. Calculate order total using domain logic
            order = Order.create_new(
                customer_name=command.customer_name,
                customer_phone=command.customer_phone,
                customer_address=command.customer_address,
                pizzas=command.pizzas,
                payment_method=command.payment_method
            )

            # 3. Process payment (integration layer)
            payment_result = await self.payment_service.process_payment_async(
                order.total_amount, command.payment_method
            )

            if not payment_result.is_success:
                return self.bad_request("Payment processing failed")

            order.mark_payment_processed(payment_result.transaction_id)

            # 4. Save order (integration layer)
            saved_order = await self.order_repository.save_async(order)

            # 5. Domain event will trigger kitchen notification automatically
            # (OrderPlacedEvent is raised by Order entity)

            # 6. Send customer confirmation
            await self.notification_service.send_order_confirmation_async(saved_order)

            # 7. Return success result
            order_dto = self.mapper.map(saved_order, OrderDto)
            return self.created(order_dto)

        except Exception as ex:
            return self.internal_server_error(f"Failed to place order: {str(ex)}")
```

**Architecture Benefits**:

- **Single Responsibility**: Each handler has one clear purpose
- **Testability**: Easy to unit test handlers with mocked repositories
- **Transaction Management**: Clear transaction boundaries
- **Event-Driven**: Domain events enable loose coupling

### 🏛️ Domain Layer: Pizza Business Logic

**Purpose**: Contains core pizza business rules and entities

**Responsibilities**:

- Business entities with behavior
- Domain services for complex business logic
- Domain events for business-significant occurrences
- Business rule validation and invariants

**Key Components**:

**Key Components**:

- **Controllers**: Handle HTTP requests and delegate to application layer
- **DTOs**: Data Transfer Objects for API contracts
- **Middleware**: Cross-cutting concerns like authentication, logging

**Example Structure**:

```text
api/
├── controllers/
│   ├── users_controller.py
│   └── orders_controller.py
├── models/
│   ├── user_dto.py
│   └── order_dto.py
└── middleware/
    ├── auth_middleware.py
    └── logging_middleware.py
```

**Best Practices**:

- Keep controllers thin - delegate business logic to application layer
- Use DTOs to define API contracts
- Validate input at the API boundary
- Map between DTOs and domain models

### 💼 Application Layer (`src/application/`)

**Purpose**: Orchestrates business workflows and coordinates domain operations

**Responsibilities**:

- Command and query handling
- Business workflow orchestration
- Transaction management
- Event publishing
- Application services

**Key Components**:

- **Commands**: Represent actions that change state
- **Queries**: Represent read operations
- **Handlers**: Process commands and queries
- **Services**: Application-specific business logic

**Example Structure**:

```text
application/
├── commands/
│   ├── create_user_command.py
│   └── update_user_command.py
├── queries/
│   ├── get_user_query.py
│   └── list_users_query.py
├── services/
│   ├── user_service.py
│   └── notification_service.py
└── events/
    ├── user_created_event.py
    └── user_updated_event.py
```

**Best Practices**:

- Each command/query should have a single responsibility
- Use the mediator pattern to decouple handlers
- Keep application services focused on coordination
- Publish domain events for side effects

### 🏛️ Domain Layer (`src/domain/`)

**Purpose**: Contains the core business logic and rules

**Responsibilities**:

- Business entities and aggregates
- Value objects
- Domain services
- Business rules and invariants
- Domain events

**Key Components**:

- **Entities**: Objects with identity and lifecycle
- **Value Objects**: Immutable objects defined by their attributes
- **Aggregates**: Consistency boundaries
- **Domain Services**: Business logic that doesn't belong to entities

**Example Structure**:

```text
domain/
├── models/
│   ├── user.py
│   ├── order.py
│   └── address.py
├── services/
│   ├── pricing_service.py
│   └── validation_service.py
└── events/
    ├── user_registered.py
    └── order_placed.py
```

**Best Practices**:

- Keep domain models rich with behavior
- Enforce business invariants
- Use domain events for decoupling
- Avoid dependencies on infrastructure

### 🔌 Integration Layer (`src/integration/`)

**Purpose**: Handles external integrations and infrastructure concerns

**Responsibilities**:

- Database repositories
- External API clients
- Message queue integration
- File system operations
- Caching

**Key Components**:

- **Repositories**: Data access implementations
- **API Clients**: External service integrations
- **DTOs**: External data contracts
- **Infrastructure Services**: Technical concerns

**Example Structure**:

```text
integration/
├── repositories/
│   ├── user_repository.py
│   └── order_repository.py
├── clients/
│   ├── payment_client.py
│   └── email_client.py
├── models/
│   ├── user_entity.py
│   └── payment_dto.py
└── services/
    ├── cache_service.py
    └── file_service.py
```

**Best Practices**:

- Implement domain repository interfaces
- Handle external failures gracefully
- Use DTOs for external data contracts
- Isolate infrastructure concerns

## 🔄 Data Flow

### Command Flow (Write Operations)

1. **Controller** receives HTTP request with DTO
2. **Controller** maps DTO to Command and sends to Mediator
3. **Mediator** routes Command to appropriate Handler
4. **Handler** loads domain entities via Repository
5. **Handler** executes business logic on domain entities
6. **Handler** saves changes via Repository
7. **Handler** publishes domain events
8. **Handler** returns result to Controller
9. **Controller** maps result to DTO and returns HTTP response

```text
HTTP Request → Controller → Command → Handler → Domain → Repository → Database
                    ↓           ↓        ↓
               HTTP Response ← DTO ← Result ← Events
```

### Query Flow (Read Operations)

1. **Controller** receives HTTP request with parameters
2. **Controller** creates Query and sends to Mediator
3. **Mediator** routes Query to appropriate Handler
4. **Handler** loads data via Repository or Read Model
5. **Handler** returns data to Controller
6. **Controller** maps data to DTO and returns HTTP response

```text
HTTP Request → Controller → Query → Handler → Repository → Database
                    ↓         ↓       ↓
               HTTP Response ← DTO ← Result
```

## 🎭 Patterns Implemented

### 1. Command Query Responsibility Segregation (CQRS)

Separates read and write operations to optimize performance and scalability:

```python
# Command (Write)
@dataclass
class CreateUserCommand(Command[OperationResult[UserDto]]):
    email: str
    first_name: str
    last_name: str

# Query (Read)
@dataclass
class GetUserQuery(Query[OperationResult[UserDto]]):
    user_id: str
```

### 2. Mediator Pattern

Decouples components by routing requests through a central mediator:

```python
# In controller
result = await self.mediator.execute_async(command)
```

### 3. Repository Pattern

Abstracts data access and provides a consistent interface:

```python
class UserRepository(Repository[User, str]):
    async def add_async(self, user: User) -> User:
        # Implementation details
        pass
```

### 4. Event Sourcing (Optional)

Stores state changes as events rather than current state:

```python
class User(AggregateRoot[str]):
    def register(self, email: str, name: str):
        self.apply(UserRegisteredEvent(email, name))
```

### 5. Dependency Injection

Manages object creation and dependencies:

```python
# Automatic registration
builder.services.add_scoped(UserService)

# Resolution
user_service = provider.get_required_service(UserService)
```

## 🧪 Testing Architecture

The layered architecture makes testing straightforward:

### Unit Tests

Test individual components in isolation:

```python
def test_user_registration():
    # Arrange
    command = CreateUserCommand("test@example.com", "John", "Doe")
    handler = CreateUserCommandHandler(mock_repository)

    # Act
    result = await handler.handle_async(command)

    # Assert
    assert result.is_success
```

### Integration Tests

Test interactions between layers:

```python
def test_create_user_endpoint():
    # Test API → Application → Domain integration
    response = test_client.post("/api/v1/users", json=user_data)
    assert response.status_code == 201
```

### Architecture Tests

Verify architectural constraints:

```python
def test_domain_has_no_infrastructure_dependencies():
    # Ensure domain layer doesn't depend on infrastructure
    domain_modules = get_domain_modules()
    for module in domain_modules:
        assert not has_infrastructure_imports(module)
```

## 🚀 Benefits

### Maintainability

- **Clear boundaries**: Each layer has well-defined responsibilities
- **Loose coupling**: Changes in one layer don't affect others
- **High cohesion**: Related functionality is grouped together

### Testability

- **Isolated testing**: Each layer can be tested independently
- **Mock dependencies**: External dependencies can be easily mocked
- **Fast tests**: Business logic tests don't require infrastructure

### Scalability

- **CQRS**: Read and write models can be optimized separately
- **Event-driven**: Asynchronous processing for better performance
- **Microservice ready**: Clear boundaries make extraction easier

### Flexibility

- **Technology agnostic**: Swap implementations without affecting business logic
- **Framework independence**: Business logic isn't tied to web framework
- **Future-proof**: Architecture adapts to changing requirements
