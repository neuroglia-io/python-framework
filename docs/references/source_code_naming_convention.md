# 🏷️ Source Code Naming Conventions

Consistent naming conventions are crucial for maintainable, readable, and professional codebases. The Neuroglia framework
follows Python's established conventions while adding domain-specific patterns for clean architecture. This reference
provides comprehensive guidelines for naming across all layers of your application.

## 🎯 What You'll Learn

- When to use snake_case vs CamelCase vs PascalCase across different contexts
- Naming patterns for entities, events, handlers, controllers, and methods
- Layer-specific conventions that enforce clean architecture boundaries
- Benefits of consistent naming conventions for team productivity
- Mario's Pizzeria examples demonstrating proper naming in practice

---

## 📋 Benefits of Naming Conventions

### 🧠 Cognitive Load Reduction

Consistent patterns reduce mental overhead when reading code. Developers can instantly identify the purpose and layer of any component based on its name.

### 👥 Team Collaboration

Standardized naming eliminates debates about "what to call this" and ensures new team members can navigate the codebase intuitively.

### 🔍 Searchability & Navigation

Well-named components are easier to find using IDE search, grep, and other tools. Consistent patterns enable powerful refactoring operations.

### 🏗️ Architecture Enforcement

Naming conventions reinforce clean architecture boundaries - you can immediately tell if a component violates layer dependencies.

### 🚀 Productivity & Maintenance

Less time spent deciphering unclear names means more time focused on business logic and feature development.

---

## 🐍 Python Language Conventions

The framework strictly follows [PEP 8](https://peps.python.org/pep-0008/) and Python naming conventions as the foundation:

### snake_case Usage

**Files and Modules:**

```python
# ✅ Correct
user_service.py
create_order_command.py
bank_account_repository.py

# ❌ Incorrect
UserService.py
CreateOrderCommand.py
BankAccount-Repository.py
```

**Variables and Functions:**

```python
# ✅ Correct
user_name = "Mario"
total_amount = calculate_order_total()
order_placed_at = datetime.now()

def process_payment_async(amount: Decimal) -> bool:
    pass

# ❌ Incorrect
userName = "Mario"
totalAmount = calculateOrderTotal()
OrderPlacedAt = datetime.now()

def ProcessPaymentAsync(amount: Decimal) -> bool:
    pass
```

**Method and Attribute Names:**

```python
class Pizza:
    def __init__(self):
        self.pizza_name = ""        # snake_case attributes
        self.base_price = Decimal("0")
        self.available_sizes = []

    def calculate_total_price(self):  # snake_case methods
        pass

    async def save_to_database_async(self):  # async suffix
        pass
```

### PascalCase Usage

**Classes, Types, and Interfaces:**

```python
# ✅ Correct - Classes
class OrderService:
    pass

class CreatePizzaCommand:
    pass

class PizzaOrderHandler:
    pass

# ✅ Correct - Type Variables
TEntity = TypeVar("TEntity")
TKey = TypeVar("TKey")
TResult = TypeVar("TResult")

# ✅ Correct - Exceptions
class ValidationException(Exception):
    pass

class OrderNotFoundException(Exception):
    pass
```

**Enums:**

```python
class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
```

### UPPER_CASE Usage

**Constants:**

```python
# ✅ Correct - Module-level constants
DEFAULT_PIZZA_SIZE = "medium"
MAX_ORDER_ITEMS = 20
API_BASE_URL = "https://api.mariospizza.com"

# ✅ Correct - Class constants
class PizzaService:
    DEFAULT_COOKING_TIME = 15  # minutes
    MAX_TOPPINGS_PER_PIZZA = 8
```

---

## 🏗️ Layer-Specific Naming Conventions

The framework enforces different naming patterns for each architectural layer to maintain clean separation of concerns.

### 🌐 API Layer (`api/`)

The API layer handles HTTP requests and responses, following REST conventions.

**Controllers:**

```python
# Pattern: {Entity}Controller (PascalCase)
class PizzasController(ControllerBase):
    pass

class OrdersController(ControllerBase):
    pass

class CustomersController(ControllerBase):
    pass

# ❌ Avoid
class PizzaController:      # Singular form
class Pizza_Controller:     # snake_case
class pizzaController:      # camelCase
```

**Controller Methods:**

```python
class PizzasController(ControllerBase):
    # Pattern: HTTP verb + descriptive name (snake_case)
    @get("/{pizza_id}")
    async def get_pizza(self, pizza_id: str) -> PizzaDto:
        pass

    @post("/")
    async def create_pizza(self, pizza_dto: CreatePizzaDto) -> PizzaDto:
        pass

    @put("/{pizza_id}")
    async def update_pizza(self, pizza_id: str, pizza_dto: UpdatePizzaDto) -> PizzaDto:
        pass

    @delete("/{pizza_id}")
    async def delete_pizza(self, pizza_id: str) -> None:
        pass

    # Complex operations get descriptive names
    @post("/{pizza_id}/customize")
    async def customize_pizza_toppings(self, pizza_id: str, toppings: List[str]) -> PizzaDto:
        pass
```

**DTOs (Data Transfer Objects):**

```python
# Pattern: {Purpose}{Entity}Dto (PascalCase)
@dataclass
class PizzaDto:
    pizza_id: str           # snake_case fields
    pizza_name: str
    base_price: Decimal
    available_sizes: List[str]

@dataclass
class CreatePizzaDto:
    pizza_name: str
    base_price: Decimal
    ingredient_ids: List[str]

@dataclass
class UpdatePizzaDto:
    pizza_name: Optional[str] = None
    base_price: Optional[Decimal] = None

# Specialized DTOs
@dataclass
class PizzaMenuItemDto:     # Specific context
    pass

@dataclass
class PizzaInventoryDto:    # Different view
    pass
```

### 💼 Application Layer (`application/`)

The application layer orchestrates business operations through commands, queries, and handlers.

**Commands (Write Operations):**

```python
# Pattern: {Verb}{Entity}Command (PascalCase)
@dataclass
class CreatePizzaCommand(Command[OperationResult[PizzaDto]]):
    pizza_name: str         # snake_case fields
    base_price: Decimal
    ingredient_ids: List[str]

@dataclass
class UpdatePizzaCommand(Command[OperationResult[PizzaDto]]):
    pizza_id: str
    pizza_name: Optional[str] = None
    base_price: Optional[Decimal] = None

@dataclass
class DeletePizzaCommand(Command[OperationResult]):
    pizza_id: str

# Complex business operations
@dataclass
class ProcessOrderPaymentCommand(Command[OperationResult[PaymentDto]]):
    order_id: str
    payment_method: PaymentMethod
    amount: Decimal
```

**Queries (Read Operations):**

```python
# Pattern: {Action}{Entity}Query (PascalCase)
@dataclass
class GetPizzaByIdQuery(Query[PizzaDto]):
    pizza_id: str

@dataclass
class GetPizzasByTypeQuery(Query[List[PizzaDto]]):
    pizza_type: PizzaType
    include_unavailable: bool = False

@dataclass
class SearchPizzasQuery(Query[List[PizzaDto]]):
    search_term: str
    max_results: int = 50

# Complex queries with business logic
@dataclass
class GetPopularPizzasForRegionQuery(Query[List[PizzaDto]]):
    region_code: str
    date_range: DateRange
    min_order_count: int = 10
```

**Handlers:**

```python
# Pattern: {Command/Query}Handler (PascalCase)
class CreatePizzaCommandHandler(CommandHandler[CreatePizzaCommand, OperationResult[PizzaDto]]):
    def __init__(self,
                 pizza_repository: PizzaRepository,
                 mapper: Mapper,
                 event_bus: EventBus):
        self._pizza_repository = pizza_repository    # snake_case fields
        self._mapper = mapper
        self._event_bus = event_bus

    async def handle_async(self, command: CreatePizzaCommand) -> OperationResult[PizzaDto]:
        # snake_case method names and variables
        validation_result = await self._validate_command(command)
        if not validation_result.is_success:
            return validation_result

        pizza = Pizza(
            name=command.pizza_name,
            base_price=command.base_price
        )

        await self._pizza_repository.save_async(pizza)

        # Raise domain event
        pizza_created_event = PizzaCreatedEvent(
            pizza_id=pizza.id,
            pizza_name=pizza.name
        )
        await self._event_bus.publish_async(pizza_created_event)

        return self.created(self._mapper.map(pizza, PizzaDto))
```

**Services:**

```python
# Pattern: {Entity}Service or {Purpose}Service (PascalCase)
class PizzaService:
    async def calculate_cooking_time_async(self, pizza: Pizza) -> int:
        pass

    async def check_ingredient_availability_async(self, ingredients: List[str]) -> bool:
        pass

class OrderService:
    async def process_order_async(self, order: Order) -> OperationResult[Order]:
        pass

class PaymentService:
    async def process_payment_async(self, payment_info: PaymentInfo) -> PaymentResult:
        pass

# Specialized services
class PizzaRecommendationService:
    pass

class OrderNotificationService:
    pass
```

### 🏛️ Domain Layer (`domain/`)

The domain layer contains core business logic and entities, following domain-driven design principles.

**Entities:**

```python
# Pattern: {BusinessConcept} (PascalCase, singular)
class Pizza(Entity[str]):
    def __init__(self, name: str, base_price: Decimal):
        super().__init__()
        self.name = name                    # snake_case attributes
        self.base_price = base_price
        self.available_sizes = []
        self.created_at = datetime.now()

    # Business method names in snake_case
    def add_ingredient(self, ingredient: Ingredient) -> None:
        if not self.can_add_ingredient(ingredient):
            raise BusinessRuleViolation("Cannot add ingredient to pizza")

        self.ingredients.append(ingredient)
        self.raise_event(IngredientAddedEvent(self.id, ingredient.id))

    def calculate_total_price(self, size: PizzaSize) -> Decimal:
        base_cost = self.base_price * size.price_multiplier
        ingredient_cost = sum(i.price for i in self.ingredients)
        return base_cost + ingredient_cost

    def can_add_ingredient(self, ingredient: Ingredient) -> bool:
        # Business rules
        return len(self.ingredients) < self.MAX_INGREDIENTS

class Order(Entity[str]):
    def __init__(self, customer_id: str):
        super().__init__()
        self.customer_id = customer_id
        self.order_items = []
        self.status = OrderStatus.PENDING
        self.total_amount = Decimal("0")

    def add_pizza(self, pizza: Pizza, quantity: int) -> None:
        if self.status != OrderStatus.PENDING:
            raise BusinessRuleViolation("Cannot modify confirmed order")

        order_item = OrderItem(pizza, quantity)
        self.order_items.append(order_item)
        self._recalculate_total()

        self.raise_event(PizzaAddedToOrderEvent(self.id, pizza.id, quantity))
```

**Value Objects:**

```python
# Pattern: {Concept} (PascalCase, represents a value)
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

@dataclass(frozen=True)
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"

    def to_display_string(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"

@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self):
        if "@" not in self.value:
            raise ValueError("Invalid email address")
```

**Domain Events:**

```python
# Pattern: {Entity}{Action}Event (PascalCase)
@dataclass
class PizzaCreatedEvent(DomainEvent[str]):
    pizza_id: str
    pizza_name: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class OrderConfirmedEvent(DomainEvent[str]):
    order_id: str
    customer_id: str
    total_amount: Decimal
    estimated_delivery: datetime

@dataclass
class PaymentProcessedEvent(DomainEvent[str]):
    payment_id: str
    order_id: str
    amount: Decimal
    payment_method: str

# Complex business events
@dataclass
class PizzaCustomizationCompletedEvent(DomainEvent[str]):
    pizza_id: str
    customization_options: Dict[str, Any]
    final_price: Decimal
```

**Repository Interfaces:**

```python
# Pattern: {Entity}Repository (PascalCase)
class PizzaRepository(Repository[Pizza, str]):
    @abstractmethod
    async def get_by_name_async(self, name: str) -> Optional[Pizza]:
        pass

    @abstractmethod
    async def get_popular_pizzas_async(self, limit: int = 10) -> List[Pizza]:
        pass

    @abstractmethod
    async def search_by_ingredients_async(self, ingredients: List[str]) -> List[Pizza]:
        pass

class OrderRepository(Repository[Order, str]):
    @abstractmethod
    async def get_by_customer_id_async(self, customer_id: str) -> List[Order]:
        pass

    @abstractmethod
    async def get_pending_orders_async(self) -> List[Order]:
        pass
```

**Business Exceptions:**

```python
# Pattern: {Reason}Exception (PascalCase)
class BusinessRuleViolation(Exception):
    def __init__(self, message: str, rule_name: str = None):
        super().__init__(message)
        self.rule_name = rule_name

class PizzaNotAvailableException(BusinessRuleViolation):
    def __init__(self, pizza_name: str):
        super().__init__(f"Pizza '{pizza_name}' is not available")
        self.pizza_name = pizza_name

class InsufficientInventoryException(BusinessRuleViolation):
    def __init__(self, ingredient_name: str, requested: int, available: int):
        super().__init__(f"Insufficient {ingredient_name}: requested {requested}, available {available}")
        self.ingredient_name = ingredient_name
```

### 🔌 Integration Layer (`integration/`)

The integration layer handles external systems, databases, and infrastructure concerns.

**Repository Implementations:**

```python
# Pattern: {Technology}{Entity}Repository (PascalCase)
class MongoDbPizzaRepository(PizzaRepository):
    def __init__(self, database: Database):
        self._collection = database.pizzas    # snake_case field

    async def save_async(self, pizza: Pizza) -> None:
        pizza_doc = {
            "_id": pizza.id,
            "name": pizza.name,
            "base_price": float(pizza.base_price),
            "ingredients": [i.to_dict() for i in pizza.ingredients],
            "created_at": pizza.created_at.isoformat()
        }
        await self._collection.insert_one(pizza_doc)

    async def get_by_id_async(self, pizza_id: str) -> Optional[Pizza]:
        doc = await self._collection.find_one({"_id": pizza_id})
        return self._map_to_pizza(doc) if doc else None

class InMemoryPizzaRepository(PizzaRepository):
    def __init__(self):
        self._store: Dict[str, Pizza] = {}    # snake_case field

    async def save_async(self, pizza: Pizza) -> None:
        self._store[pizza.id] = pizza
```

**External Service Clients:**

```python
# Pattern: {Service}Client or {System}Service (PascalCase)
class PaymentGatewayClient:
    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url
        self._http_client = httpx.AsyncClient()

    async def process_payment_async(self, payment_request: PaymentRequest) -> PaymentResponse:
        pass

    async def refund_payment_async(self, transaction_id: str) -> RefundResponse:
        pass

class EmailNotificationService:
    async def send_order_confirmation_async(self, order: Order, customer_email: str) -> None:
        pass

    async def send_delivery_notification_async(self, order: Order) -> None:
        pass

class InventoryManagementService:
    async def check_ingredient_availability_async(self, ingredient_id: str) -> int:
        pass

    async def reserve_ingredients_async(self, reservations: List[IngredientReservation]) -> bool:
        pass
```

**Configuration Models:**

```python
# Pattern: {Purpose}Settings or {System}Config (PascalCase)
class DatabaseSettings(BaseSettings):
    connection_string: str           # snake_case fields
    database_name: str
    connection_timeout: int = 30

    class Config:
        env_prefix = "DATABASE_"

class ApiSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = ["*"]

class PaymentGatewaySettings(BaseSettings):
    api_key: str
    webhook_secret: str
    sandbox_mode: bool = True
    timeout_seconds: int = 30
```

---

## 🧪 Testing Naming Conventions

Consistent test naming makes it easy to understand what's being tested and why tests might be failing.

### Test Files

```python
# Pattern: test_{module_under_test}.py
test_pizza_service.py
test_order_controller.py
test_create_pizza_command_handler.py
test_mongo_pizza_repository.py
```

### Test Classes

```python
# Pattern: Test{ClassUnderTest}
class TestPizzaService:
    pass

class TestCreatePizzaCommandHandler:
    pass

class TestOrderController:
    pass
```

### Test Methods

```python
class TestPizzaService:
    # Pattern: test_{method}_{scenario}_{expected_result}
    def test_calculate_total_price_with_large_pizza_returns_correct_amount(self):
        pass

    def test_add_ingredient_with_max_ingredients_raises_exception(self):
        pass

    def test_create_pizza_with_valid_data_returns_success(self):
        pass

    # Async tests
    @pytest.mark.asyncio
    async def test_save_pizza_async_with_valid_data_saves_successfully(self):
        pass

    @pytest.mark.asyncio
    async def test_get_pizza_by_id_async_with_nonexistent_id_returns_none(self):
        pass
```

### Test Fixtures and Utilities

```python
# Pattern: create_{entity} or {entity}_fixture
@pytest.fixture
def pizza_fixture():
    return Pizza(name="Margherita", base_price=Decimal("12.99"))

@pytest.fixture
def customer_fixture():
    return Customer(name="Mario", email="mario@test.com")

def create_test_pizza(name: str = "Test Pizza") -> Pizza:
    return Pizza(name=name, base_price=Decimal("10.00"))

def create_mock_repository() -> Mock:
    repository = Mock(spec=PizzaRepository)
    repository.save_async.return_value = None
    return repository
```

---

## 🔄 Case Conversion Patterns

The framework provides utilities to handle different naming conventions across system boundaries.

### API Boundary Conversion

```python
# Internal Python code uses snake_case
class PizzaService:
    def __init__(self):
        self.total_price = Decimal("0")      # snake_case
        self.cooking_time = 15
        self.ingredient_list = []

# API DTOs can use camelCase for frontend compatibility
class PizzaDto(CamelModel):
    pizza_name: str          # Becomes "pizzaName" in JSON
    base_price: Decimal      # Becomes "basePrice" in JSON
    cooking_time: int        # Becomes "cookingTime" in JSON
    ingredient_list: List[str]  # Becomes "ingredientList" in JSON

# Frontend receives camelCase JSON
{
    "pizzaName": "Margherita",
    "basePrice": 12.99,
    "cookingTime": 15,
    "ingredientList": ["tomato", "mozzarella", "basil"]
}
```

### Database Field Mapping

```python
# Python entity with snake_case
class Pizza(Entity):
    def __init__(self):
        self.pizza_name = ""         # snake_case in Python
        self.base_price = Decimal("0")
        self.created_at = datetime.now()

# MongoDB document mapping
pizza_document = {
    "pizza_name": pizza.pizza_name,      # snake_case in database
    "base_price": float(pizza.base_price),
    "created_at": pizza.created_at.isoformat()
}

# SQL table with snake_case columns
CREATE TABLE pizzas (
    pizza_id UUID PRIMARY KEY,
    pizza_name VARCHAR(100) NOT NULL,    -- snake_case columns
    base_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 📁 File and Directory Naming

Consistent file organization makes codebases navigable and maintainable.

### File Naming Patterns

```
# ✅ Correct - snake_case for all files
pizza_service.py
create_order_command.py
mongo_pizza_repository.py
order_controller.py
pizza_created_event.py

# ❌ Incorrect
PizzaService.py
CreateOrderCommand.py
MongoPizzaRepository.py
OrderController.py
```

### Directory Structure

```
src/marios_pizzeria/
├── api/                          # Layer directories
│   ├── controllers/              # Component type directories
│   │   ├── pizzas_controller.py  # Plural for REST controllers
│   │   ├── orders_controller.py
│   │   └── customers_controller.py
│   └── dtos/
│       ├── pizza_dto.py          # Singular entity + dto
│       ├── create_pizza_dto.py   # Action + entity + dto
│       └── order_dto.py
├── application/
│   ├── commands/
│   │   ├── pizzas/               # Group by entity
│   │   │   ├── create_pizza_command.py
│   │   │   ├── update_pizza_command.py
│   │   │   └── delete_pizza_command.py
│   │   └── orders/
│   │       ├── create_order_command.py
│   │       └── confirm_order_command.py
│   ├── queries/
│   │   ├── get_pizza_by_id_query.py
│   │   └── search_pizzas_query.py
│   └── handlers/
│       ├── create_pizza_handler.py
│       └── process_order_handler.py
├── domain/
│   ├── entities/
│   │   ├── pizza.py              # Singular entity names
│   │   ├── order.py
│   │   └── customer.py
│   ├── events/
│   │   ├── pizza_events.py       # Group related events
│   │   └── order_events.py
│   ├── repositories/
│   │   ├── pizza_repository.py   # Abstract interfaces
│   │   └── order_repository.py
│   └── exceptions/
│       ├── business_exceptions.py
│       └── validation_exceptions.py
└── integration/
    ├── repositories/
    │   ├── mongodb_pizza_repository.py  # Technology + entity + repository
    │   └── postgres_order_repository.py
    ├── services/
    │   ├── payment_gateway_client.py
    │   └── email_notification_service.py
    └── configuration/
        ├── database_settings.py
        └── api_settings.py
```

---

## ⚡ Common Anti-Patterns to Avoid

### ❌ Inconsistent Casing

```python
# ❌ Mixed conventions in same context
class PizzaService:
    def __init__(self):
        self.pizzaName = ""          # camelCase in Python
        self.base_price = Decimal("0")  # snake_case
        self.CookingTime = 15        # PascalCase

# ✅ Consistent snake_case
class PizzaService:
    def __init__(self):
        self.pizza_name = ""
        self.base_price = Decimal("0")
        self.cooking_time = 15
```

### ❌ Unclear Abbreviations

```python
# ❌ Cryptic abbreviations
class PzSvc:           # Pizza Service?
    def calc_ttl_prc(self):  # Calculate total price?
        pass

def proc_ord(ord_id):  # Process order?
    pass

# ✅ Clear, descriptive names
class PizzaService:
    def calculate_total_price(self):
        pass

def process_order(order_id: str):
    pass
```

### ❌ Misleading Names

```python
# ❌ Name doesn't match behavior
class PizzaService:
    def get_pizza(self, pizza_id: str):
        # Actually creates and saves a new pizza!
        pizza = Pizza("New Pizza", Decimal("10.00"))
        self.repository.save(pizza)
        return pizza

# ✅ Name matches behavior
class PizzaService:
    def create_pizza(self, name: str, price: Decimal) -> Pizza:
        pizza = Pizza(name, price)
        self.repository.save(pizza)
        return pizza

    def get_pizza(self, pizza_id: str) -> Optional[Pizza]:
        return self.repository.get_by_id(pizza_id)
```

### ❌ Generic Names

```python
# ❌ Too generic
class Manager:
    pass

class Helper:
    pass

def process(data):
    pass

# ✅ Specific and descriptive
class OrderManager:
    pass

class PizzaValidationHelper:
    pass

def process_payment_transaction(payment_info: PaymentInfo):
    pass
```

---

## 🎯 Framework-Specific Patterns

### Command and Query Naming

```python
# Commands (imperative, action-oriented)
class CreatePizzaCommand:         # Create + Entity + Command
class UpdateOrderStatusCommand:   # Update + Entity + Attribute + Command
class ProcessPaymentCommand:      # Process + Concept + Command
class CancelOrderCommand:         # Cancel + Entity + Command

# Queries (descriptive, question-oriented)
class GetPizzaByIdQuery:          # Get + Entity + Criteria + Query
class FindOrdersByCustomerQuery:  # Find + Entity + Criteria + Query
class SearchPizzasQuery:          # Search + Entity + Query
class CountActiveOrdersQuery:     # Count + Description + Query
```

### Event Naming

```python
# Domain Events (past tense, what happened)
class PizzaCreatedEvent:          # Entity + Action + Event
class OrderConfirmedEvent:        # Entity + Action + Event
class PaymentProcessedEvent:      # Concept + Action + Event
class InventoryUpdatedEvent:      # System + Action + Event

# Integration Events (external system communication)
class CustomerRegisteredIntegrationEvent:  # Action + Integration + Event
class OrderShippedIntegrationEvent:        # Action + Integration + Event
```

### Repository Naming

```python
# Abstract repositories (domain layer)
class PizzaRepository(Repository[Pizza, str]):
    pass

# Concrete implementations (integration layer)
class MongoDbPizzaRepository(PizzaRepository):
    pass

class PostgreSqlOrderRepository(OrderRepository):
    pass

class InMemoryCustomerRepository(CustomerRepository):  # For testing
    pass
```

---

## 🚀 Best Practices Summary

### ✅ Do's

1. **Be Consistent**: Use the same patterns throughout your codebase
2. **Be Descriptive**: Names should clearly indicate purpose and behavior
3. **Follow Layer Conventions**: Different layers have different naming patterns
4. **Use Standard Suffixes**: Command, Query, Handler, Repository, Service, etc.
5. **Group Related Items**: Use directories and modules to organize related code
6. **Consider Context**: API DTOs might need different casing than internal models
7. **Test Names Should Tell Stories**: Long, descriptive test method names are good

### ❌ Don'ts

1. **Don't Mix Conventions**: Pick snake_case or camelCase and stick to it within context
2. **Don't Use Abbreviations**: Prefer `customer_service` over `cust_svc`
3. **Don't Use Generic Names**: Avoid `Manager`, `Helper`, `Utility` without context
4. **Don't Ignore Framework Patterns**: Follow established Command/Query/Handler patterns
5. **Don't Violate Layer Naming**: Controllers in API layer, Handlers in Application layer
6. **Don't Use Misleading Names**: Names should match actual behavior
7. **Don't Skip Namespace Prefixes**: Use clear module organization

---

## 🍕 Mario's Pizzeria Example

Here's how all these conventions work together in a complete feature:

```python
# Domain Layer - domain/entities/pizza.py
class Pizza(Entity[str]):
    def __init__(self, name: str, base_price: Decimal):
        super().__init__()
        self.name = name
        self.base_price = base_price
        self.toppings = []

    def add_topping(self, topping: Topping) -> None:
        if len(self.toppings) >= self.MAX_TOPPINGS:
            raise TooManyToppingsException(self.name)

        self.toppings.append(topping)
        self.raise_event(ToppingAddedEvent(self.id, topping.id))

# Domain Layer - domain/events/pizza_events.py
@dataclass
class PizzaCreatedEvent(DomainEvent[str]):
    pizza_id: str
    pizza_name: str
    base_price: Decimal

# Application Layer - application/commands/create_pizza_command.py
@dataclass
class CreatePizzaCommand(Command[OperationResult[PizzaDto]]):
    pizza_name: str
    base_price: Decimal
    topping_ids: List[str]

# Application Layer - application/handlers/create_pizza_handler.py
class CreatePizzaCommandHandler(CommandHandler[CreatePizzaCommand, OperationResult[PizzaDto]]):
    async def handle_async(self, command: CreatePizzaCommand) -> OperationResult[PizzaDto]:
        pizza = Pizza(command.pizza_name, command.base_price)
        await self._pizza_repository.save_async(pizza)
        return self.created(self._mapper.map(pizza, PizzaDto))

# API Layer - api/controllers/pizzas_controller.py
class PizzasController(ControllerBase):
    @post("/", response_model=PizzaDto, status_code=201)
    async def create_pizza(self, create_dto: CreatePizzaDto) -> PizzaDto:
        command = self.mapper.map(create_dto, CreatePizzaCommand)
        result = await self.mediator.execute_async(command)
        return self.process(result)

# Integration Layer - integration/repositories/mongodb_pizza_repository.py
class MongoDbPizzaRepository(PizzaRepository):
    async def save_async(self, pizza: Pizza) -> None:
        document = self._map_to_document(pizza)
        await self._collection.insert_one(document)
```

This example demonstrates how naming conventions create a clear, navigable codebase where each component's purpose and location are immediately obvious.

## 🔗 Related Documentation

- [Python Typing Guide](python_typing_guide.md) - Complete guide to type hints, generics, and advanced typing patterns
- [Python Object-Oriented Programming](python_object_oriented.md) - OOP principles and class design
- [CQRS & Mediation](../patterns/cqrs.md) - Command and query pattern implementation
- [Dependency Injection](../patterns/dependency-injection.md) - Service registration and naming patterns
