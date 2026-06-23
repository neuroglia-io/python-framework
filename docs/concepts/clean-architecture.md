# Clean Architecture

**Time to read: 10 minutes**

Clean Architecture is a way of organizing code into layers with **clear responsibilities and dependencies**. It's the foundation of how Neuroglia structures applications.

## ❌ The Problem: "Big Ball of Mud"

Without architectural guidance, code becomes tangled:

```python
# ❌ Everything mixed together
class OrderService:
    def create_order(self, data):
        # UI logic
        if not data.get("customer_name"):
            return {"error": "Name required"}, 400

        # Business logic
        order = Order()
        order.customer = data["customer_name"]
        order.total = data["total"]

        # Database access (MongoDB specific)
        mongo_client.db.orders.insert_one(order.__dict__)

        # Email sending
        smtp.send_mail(to=data["email"], subject="Order confirmed")

        # Return HTTP response
        return {"order_id": order.id}, 201
```

**Problems:**

- Can't test without database and email server
- Can't switch from MongoDB to PostgreSQL
- Business rules mixed with HTTP and infrastructure
- Changes in UI requirements force changes in business logic

## ✅ The Solution: Layers with Dependency Rules

Clean Architecture organizes code into **concentric layers**:

```
┌─────────────────────────────────────────┐
│        Infrastructure (Outer)          │  ← Frameworks, DB, External APIs
│  ┌─────────────────────────────────┐  │
│  │   Application (Orchestration)   │  │  ← Use Cases, Handlers
│  │  ┌─────────────────────────┐   │  │
│  │  │   Domain (Core)         │   │  │  ← Business Rules, Entities
│  │  │                         │   │  │
│  │  └─────────────────────────┘   │  │
│  └─────────────────────────────────┘  │
└─────────────────────────────────────────┘

Dependency Rule: Inner layers don't know about outer layers
                 Dependencies point INWARD only
```

### The Layers

**1. Domain (Core) - The Heart**

- **What**: Business entities, rules, and logic
- **Depends on**: Nothing (pure Python)
- **Example**: `Order`, `Customer`, `Pizza` entities with business rules

```python
# ✅ Domain layer - No dependencies on framework or database
class Order:
    def add_pizza(self, pizza: Pizza):
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")  # Business rule
        self.items.append(pizza)
```

**2. Application (Orchestration) - The Use Cases**

- **What**: Application-specific business logic, use cases
- **Depends on**: Domain only
- **Example**: Command handlers, query handlers, application services

```python
# ✅ Application layer - Orchestrates domain operations
class PlaceOrderHandler:
    def __init__(self, order_repository: IOrderRepository):
        self.repository = order_repository  # Interface, not implementation!

    async def handle(self, command: PlaceOrderCommand):
        order = Order(command.customer_id)
        order.add_pizza(command.pizza)
        await self.repository.save(order)  # Uses interface
        return order
```

**3. Infrastructure (Outer) - The Details**

- **What**: Frameworks, databases, external services
- **Depends on**: Domain and Application (implements their interfaces)
- **Example**: MongoDB repositories, HTTP clients, email services

```python
# ✅ Infrastructure layer - Implements domain interfaces
class MongoOrderRepository(IOrderRepository):
    def __init__(self, mongo_client):
        self.client = mongo_client

    async def save(self, order: Order):
        # MongoDB-specific implementation
        await self.client.db.orders.insert_one(order.to_dict())
```

### The Dependency Rule

**Critical principle**: Dependencies point INWARD only.

```
✅ ALLOWED:
Application → Domain (handlers use entities)
Infrastructure → Domain (repositories implement domain interfaces)
Infrastructure → Application (implements handler interfaces)

❌ FORBIDDEN:
Domain → Application (entities don't know about handlers)
Domain → Infrastructure (entities don't know about MongoDB)
Application → Infrastructure (handlers use interfaces, not implementations)
```

## 🔧 Clean Architecture in Neuroglia

### Project Structure

Neuroglia enforces clean architecture through directory structure:

```
my-app/
├── domain/              # 🏛️ Domain Layer (Inner)
│   ├── entities/        # Business entities
│   ├── events/          # Domain events
│   └── repositories/    # Repository INTERFACES (not implementations)
│
├── application/         # 💼 Application Layer (Middle)
│   ├── commands/        # Write operations
│   ├── queries/         # Read operations
│   ├── events/          # Event handlers
│   └── services/        # Application services
│
├── integration/         # 🔌 Infrastructure Layer (Outer)
│   ├── repositories/    # Repository IMPLEMENTATIONS (MongoDB, etc.)
│   └── services/        # External service integrations
│
└── api/                 # 🌐 Presentation Layer (Outer)
    ├── controllers/     # REST endpoints
    └── dtos/            # Data transfer objects
```

### Dependency Flow Example

```python
# 1. Domain defines interface (no implementation)
# domain/repositories/order_repository.py
class IOrderRepository(ABC):
    @abstractmethod
    async def save_async(self, order: Order): pass

# 2. Application uses interface (doesn't care about implementation)
# application/commands/place_order_handler.py
class PlaceOrderHandler:
    def __init__(self, repository: IOrderRepository):  # Interface!
        self.repository = repository

    async def handle(self, cmd: PlaceOrderCommand):
        order = Order(cmd.customer_id)
        await self.repository.save_async(order)  # Uses interface

# 3. Infrastructure implements interface
# integration/repositories/mongo_order_repository.py
class MongoOrderRepository(IOrderRepository):
    async def save_async(self, order: Order):
        # MongoDB-specific code here
        pass

# 4. DI container wires them together at runtime
# main.py
services.add_scoped(IOrderRepository, MongoOrderRepository)
```

**The magic**: Handler never knows about MongoDB! You can swap to PostgreSQL by changing one line in `main.py`.

## 🧪 Testing Benefits

Clean Architecture makes testing easy:

```python
# Test with in-memory repository (no database needed!)
class InMemoryOrderRepository(IOrderRepository):
    def __init__(self):
        self.orders = {}

    async def save_async(self, order: Order):
        self.orders[order.id] = order

# Test handler
async def test_place_order():
    repo = InMemoryOrderRepository()  # No MongoDB!
    handler = PlaceOrderHandler(repo)

    cmd = PlaceOrderCommand(customer_id="123", pizza="Margherita")
    result = await handler.handle(cmd)

    assert result.is_success
    assert len(repo.orders) == 1  # Verify order was saved
```

## ⚠️ Common Mistakes

### 1. Domain Depending on Infrastructure

```python
# ❌ WRONG: Entity knows about MongoDB
class Order:
    def save(self):
        mongo_client.db.orders.insert_one(self.__dict__)  # NO!

# ✅ RIGHT: Entity is pure business logic
class Order:
    def add_pizza(self, pizza):
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")
```

### 2. Application Depending on Concrete Implementations

```python
# ❌ WRONG: Handler depends on concrete MongoDB repository
class PlaceOrderHandler:
    def __init__(self):
        self.repo = MongoOrderRepository()  # Tight coupling!

# ✅ RIGHT: Handler depends on interface
class PlaceOrderHandler:
    def __init__(self, repo: IOrderRepository):  # Interface!
        self.repo = repo
```

### 3. Putting Everything in Domain

```python
# ❌ WRONG: Email sending in domain entity
class Order:
    def confirm(self):
        self.status = OrderStatus.CONFIRMED
        EmailService.send_confirmation(self.customer)  # NO!

# ✅ RIGHT: Domain events, infrastructure listens
class Order:
    def confirm(self):
        self.status = OrderStatus.CONFIRMED
        self.raise_event(OrderConfirmedEvent(...))  # Yes!

# Infrastructure reacts to event
class OrderConfirmedHandler:
    async def handle(self, event: OrderConfirmedEvent):
        await self.email_service.send_confirmation(...)
```

## 🚫 When NOT to Use

Clean Architecture has **overhead**. Consider simpler approaches when:

1. **Prototype/Throwaway Code**: If you're just testing an idea
2. **Tiny Scripts**: < 100 lines, no tests, no maintenance
3. **CRUD Apps**: Simple database operations with no business logic
4. **Single Developer, Short Timeline**: Clean Architecture shines in teams and long-term projects

For small apps, start simple and refactor to clean architecture when complexity grows.

## 📝 Key Takeaways

1. **Layers**: Domain (core) → Application (use cases) → Infrastructure (details)
2. **Dependency Rule**: Dependencies point INWARD only
3. **Interfaces**: Inner layers define interfaces, outer layers implement
4. **Testability**: Swap real implementations with test doubles
5. **Flexibility**: Change databases/frameworks without touching business logic

## 🚀 Next Steps

- **Apply it**: [Tutorial Part 1](../tutorials/mario-pizzeria-01-setup.md) sets up clean architecture
- **Understand DI**: [Dependency Injection](dependency-injection.md) makes this work
- **See it work**: [Domain-Driven Design](domain-driven-design.md) for the domain layer

## 📚 Further Reading

- Robert C. Martin's "Clean Architecture" (book)
- [The Clean Architecture (blog post)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Neuroglia tutorials](../tutorials/index.md) - see it in practice

---

**Previous:** [← Core Concepts Index](index.md) | **Next:** [Dependency Injection →](dependency-injection.md)
