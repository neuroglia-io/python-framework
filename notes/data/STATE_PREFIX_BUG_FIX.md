# Critical Bug Fix: Incorrect "state." Prefix in MongoDB Queries

## Issue Discovered

The repository queries were using an incorrect `"state."` prefix (e.g., `{"state.email": email}`) based on a misunderstanding of how `MotorRepository` serializes AggregateRoot entities.

### Root Cause

The `MotorRepository._serialize_entity()` method serializes `entity.state` **directly** to the MongoDB document root, not nested under a "state" property:

```python
def _serialize_entity(self, entity: TEntity) -> dict:
    if self._is_aggregate_root(entity):
        # Serializes entity.state fields directly - NOT wrapped in "state"
        json_str = self._serializer.serialize_to_text(entity.state)
    else:
        json_str = self._serializer.serialize_to_text(entity)

    return self._serializer.deserialize_from_text(json_str, dict)
```

### Actual MongoDB Structure

**What's actually in MongoDB:**

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

**What I incorrectly documented:**

```json
{
    "_id": ObjectId("..."),
    "id": "...",
    "state": {              // ❌ WRONG - Not how it's stored!
        "name": "...",
        "email": "..."
    }
}
```

### Impact

All custom repository queries were **broken** and would return no results:

- `get_by_email_async()` - Would never find customers
- `get_by_phone_async()` - Would never find customers
- `get_by_user_id_async()` - Would never find customers (broke login!)
- `get_by_customer_id_async()` - Would never find orders
- `get_by_status_async()` - Would never find orders
- `get_orders_by_date_range_async()` - Would never find orders
- `get_active_orders_async()` - Would never find orders
- `get_frequent_customers_async()` - Aggregation join would fail

## Fixes Applied

### 1. MongoCustomerRepository

**Changed all queries from:**

```python
{"state.email": email}
{"state.phone": phone}
{"state.user_id": user_id}
"foreignField": "state.customer_id"  # In aggregation
```

**To:**

```python
{"email": email}
{"phone": phone}
{"user_id": user_id}
"foreignField": "customer_id"  # In aggregation
```

### 2. MongoOrderRepository

**Changed all queries from:**

```python
{"state.customer_id": customer_id}
{"state.status": status.value}
{"state.created_at": {"$gte": start_date, "$lte": end_date}}
{"state.customer_phone": phone}
{"state.status": {"$nin": [...]}}
```

**To:**

```python
{"customer_id": customer_id}
{"status": status.value}
{"created_at": {"$gte": start_date, "$lte": end_date}}
{"customer_phone": phone}
{"status": {"$nin": [...]}}
```

## Files Changed

### Repository Implementations

- ✅ `samples/mario-pizzeria/integration/repositories/mongo_customer_repository.py`

  - Fixed: `get_by_phone_async()`, `get_by_email_async()`, `get_by_user_id_async()`
  - Fixed: `get_frequent_customers_async()` aggregation pipeline

- ✅ `samples/mario-pizzeria/integration/repositories/mongo_order_repository.py`
  - Fixed: `get_by_customer_id_async()`, `get_by_customer_phone_async()`
  - Fixed: `get_by_status_async()`, `get_orders_by_date_range_async()`
  - Fixed: `get_active_orders_async()`

### Documentation

- ❌ Removed: `notes/STATE_PREFIX_DESIGN_DECISION.md` (completely incorrect analysis)
- ✅ Created: `notes/FLAT_STATE_STORAGE_PATTERN.md` (correct explanation)
- ✅ Created: `notes/STATE_PREFIX_BUG_FIX.md` (this document)

## Testing

### Application Startup

```
✅ Mediator configured with automatic handler discovery and proper DI
INFO: Successfully registered 10 handlers from package: application.events
INFO: Handler discovery completed: 23 total handlers registered
INFO: Application startup complete.
```

### Expected Behavior Now

1. **Login should work** - `get_by_user_id_async()` will find customers by Keycloak user_id
2. **Profile queries work** - `get_by_email_async()` will find customers
3. **Order history works** - `get_by_customer_id_async()` will find orders
4. **Kitchen display works** - `get_by_status_async()` will find orders
5. **Analytics work** - `get_frequent_customers_async()` aggregation will join correctly

## Key Lessons

### 1. **Always Verify Actual Data Structure**

Don't assume - check what's actually in MongoDB using `mongo` shell or Compass.

### 2. **Test Repository Queries**

The queries were broken from the start but went unnoticed. Need integration tests.

### 3. **Understand Framework Behavior**

The "state separation" pattern is Python-only - MongoDB doesn't reflect this.

### 4. **Serialization Details Matter**

The difference between:

```python
serialize(entity)        # Whole object
serialize(entity.state)  # Just state fields
```

Is critical and changes the entire document structure.

## Correct Pattern Going Forward

### Query Pattern

```python
# ✅ Always use flat field names for AggregateRoot queries
await repository.find_one_async({"email": email})
await repository.find_async({"status": status})
await repository.find_async({"created_at": {"$gte": date}})
```

### Index Creation

```python
# ✅ Create indexes on root-level fields
await collection.create_index([("email", 1)], unique=True)
await collection.create_index([("user_id", 1)])
await collection.create_index([("status", 1)])
await collection.create_index([("created_at", -1)])
```

### Aggregation Pipelines

```python
# ✅ Use root-level field names
{
    "$lookup": {
        "from": "orders",
        "localField": "id",
        "foreignField": "customer_id",  # Not "state.customer_id"
        "as": "orders"
    }
}
```

## Next Steps

### 1. Integration Testing

Create integration tests to verify:

- Customer queries return correct results
- Order queries return correct results
- Aggregation pipelines work correctly
- Login flow works end-to-end

### 2. Index Creation

Create proper indexes in MongoDB:

```python
# customers collection
await customers.create_index([("email", 1)], unique=True)
await customers.create_index([("user_id", 1)])
await customers.create_index([("phone", 1)])

# orders collection
await orders.create_index([("customer_id", 1)])
await orders.create_index([("status", 1)])
await orders.create_index([("created_at", -1)])
```

### 3. Test Coverage

Add unit tests for repository queries:

```python
@pytest.mark.asyncio
async def test_get_customer_by_email():
    customer = await repository.get_by_email_async("test@example.com")
    assert customer is not None
    assert customer.state.email == "test@example.com"
```

## Related Documentation

- **Correct Pattern**: `notes/FLAT_STATE_STORAGE_PATTERN.md`
- **MotorRepository**: `src/neuroglia/data/infrastructure/mongo/motor_repository.py`
- **Repository Setup**: `notes/MOTOR_REPOSITORY_CONFIGURE_AND_SCOPED.md`

## Status

✅ **Fixed** - All repository queries corrected to use flat field names
✅ **Verified** - Application starts successfully
⏳ **Pending** - Integration testing to verify queries work correctly
⏳ **Pending** - Index creation for performance
⏳ **Pending** - Unit test coverage for repositories
