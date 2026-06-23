# CQRS (Command Query Responsibility Segregation)

**Time to read: 13 minutes**

CQRS separates **write operations (Commands)** from **read operations (Queries)**. Instead of one model doing everything, you have specialized models for reading and writing.

## ❌ The Problem: One Model for Everything

Traditional approach uses same model for reads and writes:

```python
# ❌ Single model handles everything
class OrderService:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    # Write operation
    def create_order(self, customer_id: str, items: List[dict]) -> Order:
        order = Order(customer_id)
        for item in items:
            order.add_item(item['pizza'], item['quantity'])
        self.repository.save(order)
        return order

    # Read operation
    def get_order(self, order_id: str) -> Order:
        return self.repository.get_by_id(order_id)

    # Read operation
    def get_customer_orders(self, customer_id: str) -> List[Order]:
        return self.repository.find_by_customer(customer_id)

    # Read operation (complex query)
    def get_order_statistics(self, date_from, date_to):
        orders = self.repository.find_by_date_range(date_from, date_to)
        # Complex aggregation logic here...
        return statistics
```

**Problems:**

1. **Conflicting concerns**: Write needs validation, reads need speed
2. **Complex queries**: Domain model not optimized for reporting
3. **Scalability**: Can't scale reads and writes independently
4. **Performance**: Writes and reads contend for same resources
5. **Security**: Same permissions for reads and writes

## ✅ The Solution: Separate Read and Write Models

Split operations into Commands (write) and Queries (read):

```
┌────────────────────────────────────────────────┐
│                 Application                    │
│                                                │
│  Commands (Write)        Queries (Read)       │
│  ┌────────────────┐      ┌─────────────────┐ │
│  │ PlaceOrder     │      │ GetOrderById    │ │
│  │ ConfirmOrder   │      │ GetCustomerOrds │ │
│  │ CancelOrder    │      │ GetStatistics   │ │
│  └────────┬───────┘      └────────┬────────┘ │
│           │                       │           │
│           ▼                       ▼           │
│  ┌────────────────┐      ┌─────────────────┐ │
│  │ Write Model    │      │ Read Model      │ │
│  │ (Domain Agg)   │      │ (Optimized DTO) │ │
│  │ - Rich domain  │      │ - Flat, denorm  │ │
│  │ - Validations  │      │ - Fast queries  │ │
│  └────────┬───────┘      └────────┬────────┘ │
│           │                       │           │
│           ▼                       ▼           │
│  ┌────────────────┐      ┌─────────────────┐ │
│  │ Write DB       │      │ Read DB         │ │
│  │ (Normalized)   │      │ (Denormalized)  │ │
│  └────────────────┘      └─────────────────┘ │
│           │                       ▲           │
│           └───────── Events ──────┘           │
│                                                │
└────────────────────────────────────────────────┘
```

**Benefits:**

1. **Optimized models**: Write model for consistency, read model for speed
2. **Independent scaling**: Scale reads and writes separately
3. **Simpler code**: Each operation has single purpose
4. **Better performance**: Reads don't lock writes
5. **Flexibility**: Different databases for reads and writes

## 🏗️ Commands: Write Operations

Commands represent **intentions to change state**:

```python
from dataclasses import dataclass
from neuroglia.mediation import Command, OperationResult

@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    """
    Command: Imperative name (verb).
    Expresses intention to change state.
    """
    customer_id: str
    items: List[OrderItemDto]
    delivery_address: DeliveryAddressDto

@dataclass
class ConfirmOrderCommand(Command[OperationResult]):
    """Command to confirm an order."""
    order_id: str

@dataclass
class CancelOrderCommand(Command[OperationResult]):
    """Command to cancel an order."""
    order_id: str
    reason: str
```

**Command Characteristics:**

- **Imperative names**: `PlaceOrder`, `ConfirmOrder`, `CancelOrder` (actions)
- **Write operations**: Change system state
- **Can fail**: Validation, business rules
- **Return results**: Success/failure, errors
- **Single purpose**: Do one thing

## 🏗️ Queries: Read Operations

Queries represent **requests for data**:

```python
from dataclasses import dataclass
from neuroglia.mediation import Query

@dataclass
class GetOrderByIdQuery(Query[OrderDto]):
    """
    Query: Question-like name.
    Requests data without changing state.
    """
    order_id: str

@dataclass
class GetCustomerOrdersQuery(Query[List[OrderDto]]):
    """Query to get customer's orders."""
    customer_id: str
    status: Optional[OrderStatus] = None

@dataclass
class GetOrderStatisticsQuery(Query[OrderStatistics]):
    """Query for order statistics."""
    date_from: datetime
    date_to: datetime
```

**Query Characteristics:**

- **Question names**: `GetOrderById`, `GetCustomerOrders` (questions)
- **Read-only**: Don't change state
- **Never fail**: Return empty/null if not found
- **Return data**: DTOs, lists, aggregates
- **Can be cached**: Since they don't change state

## 🔧 CQRS in Neuroglia

### Command Handlers

Handle write operations:

```python
from neuroglia.mediation import CommandHandler, OperationResult
from neuroglia.mapping import Mapper

class PlaceOrderCommandHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    """Handles PlaceOrderCommand - write operation."""

    def __init__(self,
                 repository: IOrderRepository,
                 mapper: Mapper):
        self.repository = repository
        self.mapper = mapper

    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
        """
        Command handler:
        1. Validate
        2. Create domain entity
        3. Apply business rules
        4. Persist
        5. Return result
        """
        # 1. Validate
        if not command.items:
            return self.bad_request("Order must have at least one item")

        # 2. Create domain entity
        order = Order(command.customer_id)

        # 3. Apply business rules (through domain model)
        for item_dto in command.items:
            order.add_item(
                item_dto.pizza_name,
                item_dto.size,
                item_dto.quantity,
                item_dto.price
            )

        order.set_delivery_address(self.mapper.map(
            command.delivery_address,
            DeliveryAddress
        ))

        # 4. Persist
        await self.repository.save_async(order)

        # 5. Return result
        order_dto = self.mapper.map(order, OrderDto)
        return self.created(order_dto)
```

### Query Handlers

Handle read operations:

```python
from neuroglia.mediation import QueryHandler

class GetOrderByIdQueryHandler(QueryHandler[GetOrderByIdQuery, OrderDto]):
    """Handles GetOrderByIdQuery - read operation."""

    def __init__(self,
                 repository: IOrderRepository,
                 mapper: Mapper):
        self.repository = repository
        self.mapper = mapper

    async def handle_async(self, query: GetOrderByIdQuery) -> Optional[OrderDto]:
        """
        Query handler:
        1. Retrieve data
        2. Transform to DTO
        3. Return (don't validate, don't modify)
        """
        # 1. Retrieve
        order = await self.repository.get_by_id_async(query.order_id)

        if not order:
            return None

        # 2. Transform
        return self.mapper.map(order, OrderDto)

class GetCustomerOrdersQueryHandler(QueryHandler[GetCustomerOrdersQuery, List[OrderDto]]):
    """Handles GetCustomerOrdersQuery - read operation."""

    def __init__(self,
                 repository: IOrderRepository,
                 mapper: Mapper):
        self.repository = repository
        self.mapper = mapper

    async def handle_async(self, query: GetCustomerOrdersQuery) -> List[OrderDto]:
        """Optimized read - may use denormalized read model."""
        # Query optimized read model (not domain model!)
        orders = await self.repository.find_by_customer_async(
            query.customer_id,
            status=query.status
        )

        return [self.mapper.map(o, OrderDto) for o in orders]
```

### Using Mediator

Mediator dispatches commands and queries to handlers:

```python
from neuroglia.mediation import Mediator

class OrdersController:
    def __init__(self, mediator: Mediator):
        self.mediator = mediator

    @post("/orders")
    async def create_order(self, dto: CreateOrderDto) -> OrderDto:
        """Write operation - use command."""
        command = PlaceOrderCommand(
            customer_id=dto.customer_id,
            items=dto.items,
            delivery_address=dto.delivery_address
        )

        result = await self.mediator.execute_async(command)
        return self.process(result)  # Returns 201 Created

    @get("/orders/{order_id}")
    async def get_order(self, order_id: str) -> OrderDto:
        """Read operation - use query."""
        query = GetOrderByIdQuery(order_id=order_id)

        result = await self.mediator.execute_async(query)

        if not result:
            raise HTTPException(status_code=404, detail="Order not found")

        return result  # Returns 200 OK

    @get("/customers/{customer_id}/orders")
    async def get_customer_orders(self, customer_id: str) -> List[OrderDto]:
        """Read operation - use query."""
        query = GetCustomerOrdersQuery(customer_id=customer_id)

        return await self.mediator.execute_async(query)
```

## 🚀 Advanced: Separate Read and Write Models

For high-scale systems, use different databases:

```python
# Write Model: Domain aggregate (normalized, consistent)
class Order(AggregateRoot):
    """Write model - rich domain model."""
    def __init__(self, customer_id: str):
        super().__init__()
        self.customer_id = customer_id
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING

    def add_item(self, pizza_name: str, ...):
        # Business logic, validation
        pass

# Write Repository: Saves domain aggregates
class OrderWriteRepository:
    """Saves to write database (normalized)."""
    async def save_async(self, order: Order):
        await self.mongo_collection.insert_one({
            "id": order.id,
            "customer_id": order.customer_id,
            "items": [item.to_dict() for item in order.items],
            "status": order.status.value
        })

# Read Model: Flat DTO (denormalized, fast)
@dataclass
class OrderReadModel:
    """Read model - optimized for queries."""
    order_id: str
    customer_id: str
    customer_name: str  # Denormalized from Customer
    customer_email: str  # Denormalized from Customer
    total: Decimal
    item_count: int
    status: str
    created_at: datetime
    # Flattened, no joins needed!

# Read Repository: Queries read model
class OrderReadRepository:
    """Queries from read database (denormalized)."""
    async def get_by_id_async(self, order_id: str) -> OrderReadModel:
        # Query denormalized view - very fast!
        doc = await self.read_collection.find_one({"order_id": order_id})
        return OrderReadModel(**doc)

# Synchronize via events
class OrderConfirmedHandler:
    """Updates read model when write model changes."""
    async def handle(self, event: OrderConfirmedEvent):
        # Update read model
        await self.read_repo.update({
            "order_id": event.order_id,
            "status": "confirmed",
            "confirmed_at": datetime.utcnow()
        })
```

## 🧪 Testing CQRS

### Test Command Handlers

```python
async def test_place_order_command():
    """Test write operation."""
    # Arrange
    mock_repo = Mock(spec=IOrderRepository)
    handler = PlaceOrderCommandHandler(mock_repo, mapper)

    command = PlaceOrderCommand(
        customer_id="123",
        items=[OrderItemDto("Margherita", PizzaSize.LARGE, 1, Decimal("15.99"))],
        delivery_address=DeliveryAddressDto("123 Main St", "City", "12345")
    )

    # Act
    result = await handler.handle_async(command)

    # Assert
    assert result.is_success
    assert result.status_code == 201
    mock_repo.save_async.assert_called_once()

async def test_place_order_validation():
    """Test command validation."""
    handler = PlaceOrderCommandHandler(mock_repo, mapper)

    command = PlaceOrderCommand(
        customer_id="123",
        items=[],  # Invalid: no items
        delivery_address=DeliveryAddressDto("123 Main St", "City", "12345")
    )

    result = await handler.handle_async(command)

    assert not result.is_success
    assert result.status_code == 400
    assert "at least one item" in result.error_message
```

### Test Query Handlers

```python
async def test_get_order_query():
    """Test read operation."""
    # Arrange
    mock_repo = Mock(spec=IOrderRepository)
    mock_repo.get_by_id_async.return_value = create_test_order()

    handler = GetOrderByIdQueryHandler(mock_repo, mapper)
    query = GetOrderByIdQuery(order_id="123")

    # Act
    result = await handler.handle_async(query)

    # Assert
    assert result is not None
    assert result.order_id == "123"
    mock_repo.get_by_id_async.assert_called_once_with("123")

async def test_get_order_not_found():
    """Test query with no result."""
    mock_repo = Mock(spec=IOrderRepository)
    mock_repo.get_by_id_async.return_value = None

    handler = GetOrderByIdQueryHandler(mock_repo, mapper)
    query = GetOrderByIdQuery(order_id="999")

    result = await handler.handle_async(query)

    assert result is None  # Query returns None, doesn't raise
```

## ⚠️ Common Mistakes

### 1. Queries that Modify State

```python
# ❌ WRONG: Query modifies state
class GetOrderByIdQueryHandler(QueryHandler):
    async def handle_async(self, query):
        order = await self.repository.get_by_id_async(query.order_id)
        order.last_viewed = datetime.utcnow()  # NO! Modifying state in query!
        await self.repository.save_async(order)
        return order

# ✅ RIGHT: Queries are read-only
class GetOrderByIdQueryHandler(QueryHandler):
    async def handle_async(self, query):
        order = await self.repository.get_by_id_async(query.order_id)
        return self.mapper.map(order, OrderDto)  # Read-only
```

### 2. Commands that Return Data

```python
# ❌ WRONG: Command returns full entity
class PlaceOrderCommand(Command[Order]):  # Returns entity
    pass

# ✅ RIGHT: Command returns result/DTO
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):  # Returns DTO
    pass
```

### 3. Business Logic in Query Handlers

```python
# ❌ WRONG: Validation in query
class GetOrderQueryHandler(QueryHandler):
    async def handle_async(self, query):
        if not query.order_id:
            raise ValueError("Order ID required")  # Query shouldn't validate!
        return await self.repository.get_by_id_async(query.order_id)

# ✅ RIGHT: Validation in command only
class ConfirmOrderCommandHandler(CommandHandler):
    async def handle_async(self, command):
        if not command.order_id:
            return self.bad_request("Order ID required")  # Validation in command
        # ...
```

## 🚫 When NOT to Use CQRS

CQRS adds complexity. Skip when:

1. **Simple CRUD**: Basic create/read/update/delete
2. **Low Scale**: Single-server application
3. **No Specialized Reads**: Reads and writes have same needs
4. **Prototypes**: Quick experiments
5. **Small Team**: Learning curve not worth it

For simple apps, traditional layered architecture works fine.

## 📝 Key Takeaways

1. **Separation**: Commands write, queries read
2. **Optimization**: Each side optimized for its purpose
3. **Scalability**: Scale reads and writes independently
4. **Clarity**: Single responsibility per operation
5. **Flexibility**: Different models, databases possible

## 🔄 CQRS + Other Patterns

```
Command → Command Handler → Domain Model → Write DB
                                    ↓
                                 Event
                                    ↓
                               Event Handler → Read Model → Read DB
                                                    ↑
Query → Query Handler ──────────────────────────────┘
```

## 🚀 Next Steps

- **Implement it**: [Tutorial Part 3](../tutorials/mario-pizzeria-03-cqrs.md) builds CQRS
- **Dispatch requests**: [Mediator Pattern](mediator.md) routes commands/queries
- **Handle events**: [Event-Driven Architecture](event-driven.md) synchronizes models

## 📚 Further Reading

- Greg Young's [CQRS Documents](https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf)
- Martin Fowler's [CQRS](https://martinfowler.com/bliki/CQRS.html)
- Microsoft's [CQRS Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs)

---

**Previous:** [← Aggregates & Entities](aggregates-entities.md) | **Next:** [Mediator Pattern →](mediator.md)
