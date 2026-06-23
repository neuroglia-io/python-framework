# MotorRepository Serialization Pattern - Flat State Storage

## Issue Identified

The MongoDB queries were incorrectly using `"state."` prefix (e.g., `{"state.email": email}`) but the actual serialization stores AggregateRoot state fields **directly at the root level**, not nested under a "state" property.

## Actual MotorRepository Serialization Behavior

### How It Works

When serializing an `AggregateRoot`, the `MotorRepository._serialize_entity()` method:

```python
def _serialize_entity(self, entity: TEntity) -> dict:
    if self._is_aggregate_root(entity):
        # For AggregateRoot, serialize only the state
        json_str = self._serializer.serialize_to_text(entity.state)
    else:
        # For Entity, serialize the whole object
        json_str = self._serializer.serialize_to_text(entity)

    return self._serializer.deserialize_from_text(json_str, dict)
```

**Key Point:** `entity.state` is serialized **directly**, not wrapped in a "state" property.

### Actual MongoDB Document Structure

For a `Customer` aggregate with `CustomerState`:

```python
@dataclass
class CustomerState(AggregateState[str]):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: str = ""
    address: str = ""
    user_id: Optional[str] = None
```

**MongoDB stores it as:**

```json
{
    "_id": ObjectId("68f8287a3f16fb80a9db4acc"),
    "id": "f2577218-6b50-412e-92d5-302ffc48865e",
    "name": "Mario Customer",
    "email": "customer@mario-pizzeria.com",
    "phone": "",
    "address": "",
    "user_id": "8a90e724-0b65-4d9d-9648-6c41062d6050"
}
```

**NOT nested:**

```json
{
    "_id": ObjectId("..."),
    "id": "...",
    "state": {              // ❌ WRONG - This is NOT how it's stored
        "name": "...",
        "email": "..."
    }
}
```

## The Bug: Incorrect "state." Prefix Usage

### What Was Wrong

Repository queries were using:

```python
# ❌ INCORRECT
async def get_by_email_async(self, email: str):
    return await self.find_one_async({"state.email": email})

async def get_by_phone_async(self, phone: str):
    return await self.find_one_async({"state.phone": phone})
```

These queries would **never find any documents** because:

- MongoDB looks for `state.email` (nested field)
- But the data is stored as `email` (root level field)

### The Fix

Queries must use **flat field names** without "state." prefix:

```python
# ✅ CORRECT
async def get_by_email_async(self, email: str):
    return await self.find_one_async({"email": email})

async def get_by_phone_async(self, phone: str):
    return await self.find_one_async({"phone": phone})
```

## Fixed Repository Queries

### MongoCustomerRepository

**Before (Broken):**

```python
async def get_by_phone_async(self, phone: str):
    return await self.find_one_async({"state.phone": phone})

async def get_by_email_async(self, email: str):
    return await self.find_one_async({"state.email": email})

async def get_by_user_id_async(self, user_id: str):
    return await self.find_one_async({"state.user_id": user_id})

# Aggregation lookup
"foreignField": "state.customer_id"
```

**After (Fixed):**

```python
async def get_by_phone_async(self, phone: str):
    return await self.find_one_async({"phone": phone})

async def get_by_email_async(self, email: str):
    return await self.find_one_async({"email": email})

async def get_by_user_id_async(self, user_id: str):
    return await self.find_one_async({"user_id": user_id})

# Aggregation lookup
"foreignField": "customer_id"
```

### MongoOrderRepository

**Before (Broken):**

```python
async def get_by_customer_id_async(self, customer_id: str):
    return await self.find_async({"state.customer_id": customer_id})

async def get_by_status_async(self, status: OrderStatus):
    return await self.find_async({"state.status": status.value})

async def get_orders_by_date_range_async(self, start_date, end_date):
    query = {"state.created_at": {"$gte": start_date, "$lte": end_date}}
    return await self.find_async(query)

async def get_active_orders_async(self):
    query = {"state.status": {"$nin": [...]}}
    return await self.find_async(query)
```

**After (Fixed):**

```python
async def get_by_customer_id_async(self, customer_id: str):
    return await self.find_async({"customer_id": customer_id})

async def get_by_status_async(self, status: OrderStatus):
    return await self.find_async({"status": status.value})

async def get_orders_by_date_range_async(self, start_date, end_date):
    query = {"created_at": {"$gte": start_date, "$lte": end_date}}
    return await self.find_async(query)

async def get_active_orders_async(self):
    query = {"status": {"$nin": [...]}}
    return await self.find_async(query)
```

## Why This Design Makes Sense

### 1. **Simpler Document Structure**

- No unnecessary nesting
- Cleaner MongoDB queries
- Direct field access in aggregation pipelines

### 2. **Better MongoDB Performance**

- Indexes work directly on root-level fields
- No need to navigate nested structures
- Simpler explain plans

### 3. **Clear Separation in Code**

- **In Python:** Clear separation between aggregate wrapper and state
- **In MongoDB:** Just the data fields (no framework artifacts)

### 4. **Framework Abstraction**

- The "state separation" pattern is a Python/framework concern
- MongoDB doesn't need to know about AggregateRoot vs Entity distinction
- Serialization handles the mapping transparently

## Correct Query Patterns

### Simple Equality Queries

```python
# ✅ Correct
{"email": "user@example.com"}
{"status": "pending"}
{"customer_id": "customer-123"}
```

### Comparison Operators

```python
# ✅ Correct
{"created_at": {"$gte": start_date, "$lte": end_date}}
{"price": {"$gt": 10.00}}
```

### Logical Operators

```python
# ✅ Correct
{"status": {"$nin": ["delivered", "cancelled"]}}
{"$or": [{"status": "pending"}, {"status": "cooking"}]}
```

### Aggregation Pipelines

```python
# ✅ Correct
{
    "$lookup": {
        "from": "orders",
        "localField": "id",           # Customer.id
        "foreignField": "customer_id",  # Order.customer_id
        "as": "orders"
    }
}
```

## Index Creation

Indexes should be created on **root-level fields**:

```python
# ✅ Correct index creation
await customers_collection.create_index([("email", 1)], unique=True)
await customers_collection.create_index([("user_id", 1)])
await customers_collection.create_index([("phone", 1)])

await orders_collection.create_index([("customer_id", 1)])
await orders_collection.create_index([("status", 1)])
await orders_collection.create_index([("created_at", -1)])
```

**Not:**

```python
# ❌ WRONG
await customers_collection.create_index([("state.email", 1)])
```

## Testing the Fix

### Before Fix (Queries Returning Nothing)

```python
# This would find nothing because "state.email" doesn't exist
customer = await repository.get_by_email_async("customer@mario-pizzeria.com")
assert customer is None  # ❌ Bug!
```

### After Fix (Queries Work Correctly)

```python
# This correctly finds the customer by root-level "email" field
customer = await repository.get_by_email_async("customer@mario-pizzeria.com")
assert customer is not None  # ✅ Works!
assert customer.state.email == "customer@mario-pizzeria.com"
```

## Key Takeaways

1. **MotorRepository serializes state fields at root level** - No "state." nesting in MongoDB
2. **Queries must use flat field names** - `{"email": ...}` not `{"state.email": ...}`
3. **The "state" concept is Python-only** - MongoDB documents don't reflect this pattern
4. **Indexes must be on root fields** - `("email", 1)` not `("state.email", 1)`
5. **Aggregation pipelines use root fields** - `"foreignField": "customer_id"` not `"state.customer_id"`

## Related Files

- **Repository Implementation**: `src/neuroglia/data/infrastructure/mongo/motor_repository.py`
- **Customer Repository**: `samples/mario-pizzeria/integration/repositories/mongo_customer_repository.py`
- **Order Repository**: `samples/mario-pizzeria/integration/repositories/mongo_order_repository.py`
- **MotorRepository Setup**: `notes/MOTOR_REPOSITORY_CONFIGURE_AND_SCOPED.md`

## Conclusion

The MotorRepository **flattens** AggregateRoot state into root-level MongoDB fields, making queries simpler and more performant. The "state" separation is purely a Python/framework pattern and doesn't appear in the MongoDB schema.

All queries have been corrected to use flat field names without the incorrect "state." prefix.
