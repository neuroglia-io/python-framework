# 🗄️ Repository Pattern with State Separation - Detailed Explanation

## Your Question: How Does State Separation Impact the Repository?

You asked: **"I understand that the aggregate's state will be stored instead of the entire object but still i'm not sure [how this works in the repository]"**

Let me show you exactly how the repository layer changes with proper state separation.

---

## 🎯 The Current Problem

### What Currently Happens (Mario Pizzeria Today)

When you save an Order aggregate:

```python
# Current: Custom AggregateRoot without state separation
class Order(AggregateRoot):  # Extends custom Entity[str]
    def __init__(self, customer_id: str):
        super().__init__()
        self.customer_id = customer_id      # ← Field on aggregate
        self.pizzas = []                    # ← Field on aggregate
        self.status = OrderStatus.PENDING   # ← Field on aggregate
        # ... ALL fields directly on the aggregate object
```

When you call `repository.add_async(order)`:

```python
# What the repository tries to do:
async def add_async(self, order: Order):
    # Problem: Need to serialize the entire Order object
    order_dict = {
        'id': order.id,
        'customer_id': order.customer_id,           # ← Extract each field manually
        'pizzas': [self._serialize_pizza(p) for p in order.pizzas],  # ← Complex
        'status': order.status.value,
        # ... must know all fields

        # PROBLEM: What about methods?
        # 'add_pizza': order.add_pizza,  # ← Can't serialize this!
        # 'confirm_order': order.confirm_order,  # ← Can't serialize this!
        # '_pending_events': order._pending_events,  # ← Should NOT serialize this!
    }

    await self._save_to_file(order_dict)  # or MongoDB
```

**Issues**:

1. ❌ Repository must know ALL fields of the aggregate
2. ❌ Repository must manually exclude methods and events
3. ❌ When you add a field to Order, you must update the repository
4. ❌ Serialization logic is complex and error-prone
5. ❌ Can't use framework's generic serialization

---

## ✅ The Solution: State Separation

### What Will Happen (After Refactoring)

With proper state separation:

```python
# NEW: Separate state object
@dataclass
class OrderState(AggregateState[str]):
    """Pure state - only data, no behavior"""
    customer_id: str
    pizzas: list[Pizza] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    order_time: datetime = field(default_factory=datetime.now)
    confirmed_time: Optional[datetime] = None
    # ... all state fields, NO methods


# NEW: Aggregate with behavior only
class Order(AggregateRoot[OrderState, str]):
    """Aggregate root - behavior only, state in self.state"""

    def __init__(self, customer_id: str):
        super().__init__()
        # Initialize state fields
        self.state.customer_id = customer_id
        self.state.pizzas = []
        self.state.status = OrderStatus.PENDING
        self.state.order_time = datetime.now()

        # Raise event
        self.register_event(OrderCreatedEvent(...))

    # All methods access state via self.state.*
    def add_pizza(self, pizza: Pizza):
        self.state.pizzas.append(pizza)  # ← Access via state
        self.register_event(PizzaAddedEvent(...))

    def confirm_order(self):
        self.state.status = OrderStatus.CONFIRMED  # ← Access via state
        self.register_event(OrderConfirmedEvent(...))
```

Now when you call `repository.add_async(order)`:

```python
# NEW: Simple serialization
async def add_async(self, order: Order):
    # Extract state object - it's ALREADY separated!
    state_dict = self._serialize_state(order.state)  # ← Just serialize state!

    # That's it! State is a clean data object with no methods
    await self._save_to_file(state_dict)
```

---

## 📊 State Serialization: Before and After

### Before (Current - Complex)

```python
class FileOrderRepository(FileSystemRepository[Order, str]):

    async def add_async(self, order: Order) -> None:
        """Must manually extract every field"""

        # Manually build dictionary from aggregate fields
        order_dict = {
            'id': order.id,
            'customer_id': order.customer_id,
            'status': order.status.value,  # Convert enum
            'order_time': order.order_time.isoformat(),  # Convert datetime
            'confirmed_time': order.confirmed_time.isoformat() if order.confirmed_time else None,
            'cooking_started_time': order.cooking_started_time.isoformat() if order.cooking_started_time else None,
            'actual_ready_time': order.actual_ready_time.isoformat() if order.actual_ready_time else None,
            'estimated_ready_time': order.estimated_ready_time.isoformat() if order.estimated_ready_time else None,
            'notes': order.notes,

            # Complex nested serialization
            'pizzas': [
                {
                    'id': pizza.id,
                    'name': pizza.name,
                    'size': pizza.size.value,
                    'base_price': str(pizza.base_price),
                    'toppings': pizza.toppings,
                }
                for pizza in order.pizzas
            ],

            # MUST NOT include:
            # - Methods (add_pizza, confirm_order, etc.)
            # - Events (_pending_events)
            # - Any private fields
        }

        # Save to file
        file_path = self.data_directory / f"{order.id}.json"
        with open(file_path, 'w') as f:
            json.dump(order_dict, f, indent=2)

    async def get_by_id_async(self, order_id: str) -> Order:
        """Must manually reconstruct aggregate from dict"""

        file_path = self.data_directory / f"{order_id}.json"
        with open(file_path, 'r') as f:
            order_dict = json.load(f)

        # Manually reconstruct aggregate
        order = Order(customer_id=order_dict['customer_id'])
        order.id = order_dict['id']  # Override generated ID
        order.status = OrderStatus(order_dict['status'])
        order.order_time = datetime.fromisoformat(order_dict['order_time'])
        order.confirmed_time = datetime.fromisoformat(order_dict['confirmed_time']) if order_dict.get('confirmed_time') else None
        # ... reconstruct all fields manually

        # Reconstruct pizzas
        for pizza_dict in order_dict['pizzas']:
            pizza = Pizza(
                name=pizza_dict['name'],
                base_price=Decimal(pizza_dict['base_price']),
                size=PizzaSize(pizza_dict['size'])
            )
            pizza.id = pizza_dict['id']
            for topping in pizza_dict['toppings']:
                pizza.add_topping(topping)
            order.pizzas.append(pizza)  # Add directly, skip event

        return order
```

**Problems**:

- 🔴 50+ lines of manual serialization code
- 🔴 Must update when Order changes
- 🔴 Easy to forget fields
- 🔴 Complex nested object handling
- 🔴 Type conversion everywhere

### After (With State Separation - Simple)

```python
class FileOrderRepository(FileSystemRepository[Order, str]):

    async def add_async(self, order: Order) -> None:
        """State serialization is automatic!"""

        # Option 1: Use framework's built-in serialization
        state_dict = dataclasses.asdict(order.state)  # ← That's it!

        # Option 2: Use Neuroglia's JsonSerializer (handles types automatically)
        from neuroglia.serialization import JsonSerializer
        state_json = JsonSerializer.serialize(order.state)

        # Save to file
        file_path = self.data_directory / f"{order.state.id}.json"
        with open(file_path, 'w') as f:
            f.write(state_json)

    async def get_by_id_async(self, order_id: str) -> Order:
        """State deserialization is automatic!"""

        file_path = self.data_directory / f"{order_id}.json"
        with open(file_path, 'r') as f:
            state_json = f.read()

        # Deserialize state
        from neuroglia.serialization import JsonSerializer
        order_state = JsonSerializer.deserialize(state_json, OrderState)

        # Create aggregate with restored state
        order = Order.__new__(Order)  # Create without __init__
        order.state = order_state      # Assign state
        order._pending_events = []     # Initialize events (empty on load)

        return order
```

**Benefits**:

- ✅ ~10 lines instead of 50+
- ✅ Automatic serialization via framework
- ✅ Type-safe with dataclasses
- ✅ No manual field tracking
- ✅ Works for nested objects

---

## 🔄 MongoDB Example

Let's look at MongoDB persistence specifically:

### Before (Current - Manual)

```python
from motor.motor_asyncio import AsyncIOMotorClient

class MongoOrderRepository(IOrderRepository):
    def __init__(self, mongo_client: AsyncIOMotorClient):
        self.collection = mongo_client.mario_pizzeria.orders

    async def add_async(self, order: Order) -> None:
        """Manually extract everything"""
        document = {
            '_id': order.id,
            'customer_id': order.customer_id,
            'status': order.status.value,
            'pizzas': [self._pizza_to_dict(p) for p in order.pizzas],
            'order_time': order.order_time,
            'confirmed_time': order.confirmed_time,
            'total_amount': float(order.total_amount),  # Decimal → float
            # ... must enumerate all fields

            # Version tracking?
            # 'version': ???  # ← Not tracked currently!
        }

        await self.collection.insert_one(document)

    def _pizza_to_dict(self, pizza: Pizza) -> dict:
        """Manual nested serialization"""
        return {
            'id': pizza.id,
            'name': pizza.name,
            'size': pizza.size.value,
            'base_price': float(pizza.base_price),
            'toppings': pizza.toppings
        }

    async def get_by_id_async(self, order_id: str) -> Order:
        """Manually reconstruct"""
        document = await self.collection.find_one({'_id': order_id})
        if not document:
            return None

        # Manually rebuild aggregate
        order = Order(customer_id=document['customer_id'])
        order.id = document['_id']
        order.status = OrderStatus(document['status'])
        # ... manually restore all fields

        return order
```

### After (With State Separation - Clean)

```python
from motor.motor_asyncio import AsyncIOMotorClient
from neuroglia.serialization import JsonSerializer

class MongoOrderRepository(IOrderRepository):
    def __init__(self, mongo_client: AsyncIOMotorClient):
        self.collection = mongo_client.mario_pizzeria.orders

    async def add_async(self, order: Order) -> None:
        """State → MongoDB document automatically"""

        # Serialize state to dict (framework handles types)
        document = JsonSerializer.to_dict(order.state)

        # MongoDB specific: use state.id as _id
        document['_id'] = order.state.id
        if 'id' in document:
            del document['id']  # Remove duplicate id field

        # Insert (with optimistic concurrency)
        await self.collection.insert_one(document)

    async def update_async(self, order: Order) -> None:
        """Update with optimistic locking"""

        document = JsonSerializer.to_dict(order.state)
        document['_id'] = order.state.id

        # Optimistic concurrency: check version hasn't changed
        old_version = order.state.state_version
        document['state_version'] = old_version + 1  # Increment version

        result = await self.collection.replace_one(
            {
                '_id': order.state.id,
                'state_version': old_version  # ← Only update if version matches
            },
            document
        )

        if result.modified_count == 0:
            raise ConcurrencyException(
                f"Order {order.state.id} was modified by another process"
            )

        # Update in-memory version
        order.state.state_version = old_version + 1

    async def get_by_id_async(self, order_id: str) -> Order:
        """MongoDB document → State → Aggregate automatically"""

        document = await self.collection.find_one({'_id': order_id})
        if not document:
            return None

        # Fix _id → id for deserialization
        document['id'] = document['_id']

        # Deserialize to state object
        order_state = JsonSerializer.from_dict(document, OrderState)

        # Reconstruct aggregate with state
        order = Order.__new__(Order)
        order.state = order_state
        order._pending_events = []  # Events not persisted

        return order
```

**Key MongoDB Features Enabled**:

1. ✅ **Optimistic Concurrency**: Version checking prevents lost updates
2. ✅ **Clean Documents**: State maps cleanly to MongoDB documents
3. ✅ **Type Handling**: Framework handles Decimal, datetime, enum conversions
4. ✅ **Queries**: Easy to query on state fields

---

## 📝 What Gets Persisted vs What Doesn't

### Persisted (in MongoDB/Files)

From `order.state`:

```json
{
  "_id": "order_12345",
  "customer_id": "cust_789",
  "pizzas": [
    {
      "id": "pizza_001",
      "name": "Margherita",
      "size": "large",
      "base_price": 12.99,
      "toppings": ["basil", "extra_cheese"]
    }
  ],
  "status": "CONFIRMED",
  "order_time": "2025-10-07T12:00:00Z",
  "confirmed_time": "2025-10-07T12:05:00Z",
  "state_version": 3,
  "created_at": "2025-10-07T12:00:00Z",
  "last_modified": "2025-10-07T12:05:00Z"
}
```

### NOT Persisted

From `order` (aggregate behavior):

- ❌ Methods: `add_pizza()`, `confirm_order()`, `cancel_order()`
- ❌ Events: `_pending_events` list
- ❌ Calculated properties: `total_amount` (calculated from pizzas)
- ❌ Any business logic

**Why not persist events?**

- Events are for side effects, not state
- Events are dispatched immediately after persistence
- If you need event history, use Event Sourcing (different pattern)

---

## 🔧 Framework Support

The Neuroglia framework provides tools to make this easy:

### JsonSerializer with Type Handling

```python
from neuroglia.serialization import JsonSerializer

# Automatic handling of:
# - Decimal → string (prevents float precision loss)
# - datetime → ISO 8601 string
# - Enum → value
# - UUID → string
# - Nested objects
# - Lists/dicts

# Serialize state
state_json = JsonSerializer.serialize(order.state)

# Deserialize state
order_state = JsonSerializer.deserialize(state_json, OrderState)
```

### Dataclass Integration

```python
import dataclasses

# State is a dataclass - free serialization!
state_dict = dataclasses.asdict(order.state)
order_state = OrderState(**state_dict)
```

### Type Registry (Advanced)

For complex type handling:

```python
from neuroglia.serialization import TypeRegistry

# Register custom encoders
TypeRegistry.register_encoder(Decimal, lambda d: str(d))
TypeRegistry.register_decoder(Decimal, lambda s: Decimal(s))
```

---

## 🎯 Repository Implementation Checklist

When implementing repositories with state separation:

### For Add/Create

- [ ] Extract state from aggregate: `order.state`
- [ ] Serialize state to dict/JSON
- [ ] Handle MongoDB `_id` field mapping
- [ ] Insert document to database
- [ ] DO NOT persist events or methods

### For Update

- [ ] Extract current state
- [ ] Check version for optimistic locking
- [ ] Increment version before saving
- [ ] Replace document with version check
- [ ] Throw ConcurrencyException if version mismatch

### For Get/Retrieve

- [ ] Load document from database
- [ ] Deserialize to state object
- [ ] Create new aggregate instance
- [ ] Assign state to aggregate
- [ ] Initialize empty `_pending_events`
- [ ] Return aggregate

### For Query

- [ ] Query on state fields (they're in the document)
- [ ] Deserialize all matching documents
- [ ] Reconstruct aggregates from states
- [ ] Return list of aggregates

---

## 🚀 Migration Strategy for Repositories

### Step 1: Add State Objects (Don't Break Anything)

```python
# Create OrderState but keep Order working as-is
@dataclass
class OrderState(AggregateState[str]):
    customer_id: str
    pizzas: list[Pizza] = field(default_factory=list)
    # ... all fields
```

### Step 2: Update Aggregate to Use State

```python
class Order(AggregateRoot[OrderState, str]):
    def __init__(self, customer_id: str):
        super().__init__()
        self.state.customer_id = customer_id  # ← Now via state
```

### Step 3: Update Repository Serialization

```python
async def add_async(self, order: Order) -> None:
    # OLD: order_dict = self._manual_extraction(order)
    # NEW: state_dict = JsonSerializer.to_dict(order.state)
    state_dict = JsonSerializer.to_dict(order.state)
    await self._save(state_dict)
```

### Step 4: Update Repository Deserialization

```python
async def get_by_id_async(self, order_id: str) -> Order:
    document = await self._load(order_id)

    # OLD: order = self._manual_reconstruction(document)
    # NEW: Deserialize state, create aggregate
    order_state = JsonSerializer.from_dict(document, OrderState)
    order = Order.__new__(Order)
    order.state = order_state
    order._pending_events = []

    return order
```

### Step 5: Test Thoroughly

- [ ] Save aggregates and verify MongoDB documents
- [ ] Load aggregates and verify state is correct
- [ ] Test optimistic concurrency (concurrent updates)
- [ ] Test queries still work
- [ ] Verify events are NOT persisted

---

## ✅ Summary

**Repository Impact**: The repository becomes **simpler** because:

1. **Serialization**: State is a clean data object → serialize directly
2. **Deserialization**: Deserialize to state → create aggregate with state
3. **No Method Filtering**: State has no methods to filter out
4. **Framework Support**: JsonSerializer handles type conversions
5. **Type Safety**: Dataclasses ensure all fields present
6. **Versioning**: AggregateState includes `state_version` for free

**What Repository Does NOT Handle**:

- ❌ Domain events (handled by UnitOfWork + Middleware)
- ❌ Business logic (handled by aggregate methods)
- ❌ Side effects (handled by event handlers)

**Repository Responsibility**:

- ✅ Persist state
- ✅ Retrieve state
- ✅ Query state
- ✅ Optimistic locking (version checking)

That's it! The repository layer becomes a thin adapter between aggregates and storage.
