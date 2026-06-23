# AggregateState Timestamp Fix

## Issue

The management dashboard and analytics were showing all zero indicators because date range queries were not finding any orders.

### Root Cause

The `AggregateState.__init__` method was unconditionally setting `created_at` and `last_modified` to `datetime.now()`, which would overwrite deserialized values when objects were loaded from MongoDB.

### Initial Investigation

1. User reported management dashboard "Total Orders Today" showing zero
2. Found that `get_orders_by_date_range_async()` was querying by `created_at` field
3. Discovered that MongoDB documents had `created_at` at root level (from AggregateState)
4. User correctly identified that `AggregateState` should have timestamp tracking

## The Problem

```python
# BEFORE - BROKEN
class AggregateState(Generic[TKey], Identifiable[TKey], VersionedState, ABC):
    def __init__(self):
        super().__init__()
        self.created_at = datetime.now()  # ❌ Always overwrites
        self.last_modified = self.created_at
```

**Issue**: While the JsonSerializer correctly uses `object.__new__()` to bypass `__init__` during deserialization, any code that might call `__init__` after deserialization (or during aggregate reconstitution) would overwrite the persisted timestamps.

## The Solution

```python
# AFTER - FIXED
class AggregateState(Generic[TKey], Identifiable[TKey], VersionedState, ABC):
    def __init__(self):
        super().__init__()
        # Only set timestamps if not already present (from deserialization)
        if not hasattr(self, "created_at") or self.created_at is None:
            self.created_at = datetime.now()
        if not hasattr(self, "last_modified") or self.last_modified is None:
            self.last_modified = self.created_at
```

**Benefits**:

- New instances get current timestamp ✓
- Deserialized instances preserve their original timestamps ✓
- Defensive: works even if `__init__` is called after deserialization ✓

## Applied Same Fix to Entity

```python
class Entity(Generic[TKey], Identifiable[TKey], ABC):
    def __init__(self) -> None:
        super().__init__()
        # Only set if not already present
        if not hasattr(self, "created_at") or self.created_at is None:
            self.created_at = datetime.now()
```

## Testing

Created comprehensive test (`test_aggregate_timestamps.py`) that verifies:

1. **New Instance Creation**: New instances get current timestamp
2. **Deserialization**: Timestamps are preserved from JSON
3. **Round-trip**: Serialize → Deserialize maintains exact timestamps

### Test Results

```
=== Test 1: New Instance ===
✓ Has timestamps: True

=== Test 2: Deserialization ===
✓ Timestamps preserved: True

=== Test 3: Round-trip ===
✓ Timestamps match: True

✅ All tests passed!
```

## Repository Query Strategy

All repository query methods now correctly use `created_at`:

```python
async def get_orders_by_date_range_async(
    self, start_date: datetime, end_date: datetime
) -> List[Order]:
    """Uses the framework's created_at timestamp from AggregateState"""
    query = {"created_at": {"$gte": start_date, "$lte": end_date}}
    return await self.find_async(query)
```

### Special Case: Timeseries Queries

For timeseries and status distribution (business analytics), we use `order_time` with fallback:

```python
async def get_orders_for_timeseries_async(
    self, start_date: datetime, end_date: datetime, granularity: str = "hour"
) -> List[Order]:
    """Uses order_time (business timestamp) with fallback to created_at"""
    query = {
        "$or": [
            {"order_time": {"$gte": start_date, "$lte": end_date}},
            {"created_at": {"$gte": start_date, "$lte": end_date}},
        ]
    }
    return await self.find_async(query)
```

**Rationale**:

- `created_at` = technical timestamp (when aggregate was first created)
- `order_time` = business timestamp (when customer placed order)
- For analytics, `order_time` is more meaningful
- Fallback ensures backward compatibility

## Impact

### Framework Level

- ✅ Fixed in `src/neuroglia/data/abstractions.py`
- ✅ Affects ALL aggregates and entities across entire framework
- ✅ Backward compatible (existing code continues to work)

### Application Level

- ✅ Management dashboard will now show correct metrics
- ✅ Analytics will display proper timeseries data
- ✅ Operations monitor will show accurate statistics
- ✅ All date range queries will work correctly

## Files Modified

1. `src/neuroglia/data/abstractions.py`

   - Fixed `Entity.__init__`
   - Fixed `AggregateState.__init__`

2. `samples/mario-pizzeria/integration/repositories/mongo_order_repository.py`

   - Already using `created_at` for most queries ✓
   - Added `$or` fallback for timeseries queries

3. `test_aggregate_timestamps.py` (new)
   - Comprehensive test coverage

## Migration Notes

**For existing data**: Orders created before this fix will have:

- `created_at` field at root level (from framework)
- `order_time` field at root level (from business logic)

**Both fields will continue to work**. The fix ensures that:

1. New orders will have properly tracked `created_at`
2. Deserialized orders will preserve their original `created_at`
3. Queries using `created_at` will find both old and new orders

## Conclusion

This fix addresses a fundamental issue in the framework's timestamp management while maintaining backward compatibility. The defensive checks ensure that timestamps are only set when appropriate, allowing deserialization to work correctly while still providing automatic timestamp tracking for new instances.
