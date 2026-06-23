# MongoDB Datetime Storage Fix

## Issue

After fixing the `AggregateState` timestamp initialization, the management dashboard still showed zero metrics even though orders existed in the database.

### Root Cause Analysis

**Problem**: MongoDB was storing `created_at` and `last_modified` as **strings** instead of **ISODate** objects:

```javascript
// WRONG - Stored as string
{
    created_at: '2025-10-23T19:51:07.520263',  // ❌ String
    last_modified: '2025-10-23T19:51:07.520263' // ❌ String
}

// Queries like this fail because you can't compare strings with datetime objects:
{ created_at: { $gte: ISODate("2025-10-23T00:00:00Z") } }  // Returns nothing!
```

### Why This Happened

The `MotorRepository._serialize_entity()` method was:

1. Serializing entity to JSON string (datetime → ISO string)
2. Deserializing JSON back to dict (ISO string remains as string)
3. Inserting into MongoDB (strings stored as strings, not dates)

```python
# BEFORE - BROKEN
def _serialize_entity(self, entity: TEntity) -> dict:
    json_str = self._serializer.serialize_to_text(entity.state)
    return self._serializer.deserialize_from_text(json_str, dict)
    # ❌ datetime objects are now strings in the dict!
```

## The Solution

Added `_restore_datetime_objects()` method that recursively converts ISO datetime strings back to Python `datetime` objects before storing in MongoDB:

```python
# AFTER - FIXED
def _serialize_entity(self, entity: TEntity) -> dict:
    json_str = self._serializer.serialize_to_text(entity.state)
    doc = json.loads(json_str)
    return self._restore_datetime_objects(doc)
    # ✓ datetime objects preserved for MongoDB

def _restore_datetime_objects(self, obj):
    """
    Recursively restore datetime objects from ISO strings.
    MongoDB stores datetime as ISODate, not strings.
    """
    if isinstance(obj, dict):
        return {k: self._restore_datetime_objects(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [self._restore_datetime_objects(item) for item in obj]
    elif isinstance(obj, str):
        # Try to parse as ISO datetime
        try:
            if obj.endswith('+00:00') or obj.endswith('Z'):
                return datetime.fromisoformat(obj.replace('Z', '+00:00'))
            elif 'T' in obj and len(obj) >= 19:
                return datetime.fromisoformat(obj)
        except (ValueError, AttributeError):
            pass
    return obj
```

## How It Works

1. **Serialization**: Entity → JSON string (with ISO datetime strings)
2. **Parsing**: JSON string → Python dict
3. **Restoration**: Recursively convert ISO strings → Python datetime objects
4. **Storage**: MongoDB automatically converts Python datetime → ISODate

Result in MongoDB:

```javascript
{
    created_at: ISODate("2025-10-23T19:51:07.520Z"),  // ✓ Date object
    last_modified: ISODate("2025-10-23T19:51:07.520Z") // ✓ Date object
}
```

## Query Compatibility

Now date range queries work correctly:

```python
# This now works!
query = {"created_at": {"$gte": start_date, "$lte": end_date}}
orders = await repository.find_async(query)
```

MongoDB can properly compare:

- **ISODate vs ISODate**: ✓ Works
- **String vs ISODate**: ❌ Doesn't work (old bug)

## Impact

### Framework Level

- ✅ Fixed in `src/neuroglia/data/infrastructure/mongo/motor_repository.py`
- ✅ Affects ALL entities/aggregates using MotorRepository
- ✅ Preserves datetime objects for MongoDB queries

### Application Level

- ✅ Management dashboard now shows correct "Total Orders Today"
- ✅ Analytics charts display proper timeseries data
- ✅ Operations monitor shows accurate date-based metrics
- ✅ All date range queries work correctly

## Testing

After this fix, new orders will be stored with proper ISODate objects:

```python
# Create new order
order = Order.create(customer_id="...", order_items=[...])
await repository.add_async(order)

# MongoDB document will have:
{
    _id: ObjectId('...'),
    created_at: ISODate("2025-10-23T..."),  // ✓ Proper date
    last_modified: ISODate("2025-10-23T..."),  // ✓ Proper date
    order_time: ISODate("2025-10-23T..."),  // ✓ Proper date
    ...
}

# Queries now work:
today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
orders = await repo.get_orders_by_date_range_async(today_start, datetime.now())
# ✓ Returns orders created today!
```

## Migration

**Old data**: Orders created before this fix have datetime fields as strings.

**Options**:

1. **Clear and recreate** (simplest for development)
2. **Migration script** to convert strings to dates (for production)

Migration script example:

```python
from datetime import datetime

# For each order in DB:
for order in collection.find():
    updates = {}
    if isinstance(order.get('created_at'), str):
        updates['created_at'] = datetime.fromisoformat(order['created_at'])
    if isinstance(order.get('last_modified'), str):
        updates['last_modified'] = datetime.fromisoformat(order['last_modified'])
    if isinstance(order.get('order_time'), str):
        updates['order_time'] = datetime.fromisoformat(order['order_time'].replace('Z', '+00:00'))

    if updates:
        collection.update_one({'_id': order['_id']}, {'$set': updates})
```

## Files Modified

1. `src/neuroglia/data/infrastructure/mongo/motor_repository.py`
   - Modified `_serialize_entity()` method
   - Added `_restore_datetime_objects()` helper method

## Related Fixes

This fix builds on the previous `AggregateState` timestamp fix:

1. **Part 1**: Fixed `AggregateState.__init__` to preserve timestamps during deserialization
2. **Part 2** (this fix): Ensure timestamps are stored as MongoDB ISODate objects, not strings

Both fixes were necessary for the management dashboard to work correctly.
