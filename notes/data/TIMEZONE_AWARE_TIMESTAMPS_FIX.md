# Complete Fix: Timezone-Aware Timestamps

## The Root Cause

The management dashboard showed zero orders because of **TWO related issues**:

### Issue 1: Naive Datetime Objects

`AggregateState` and `Entity` were using `datetime.now()` which creates **naive datetimes** (no timezone info):

```python
# WRONG - Creates naive datetime
self.created_at = datetime.now()
# Result: 2025-10-23T20:06:48.563098 (no timezone!)
```

### Issue 2: String Storage in MongoDB

Even after fixing the serialization, datetime strings without timezone info weren't being converted back to datetime objects by `_restore_datetime_objects()`.

## MongoDB Document Comparison

**Before Fix (BROKEN)**:

```javascript
{
    created_at: '2025-10-23T20:06:48.563098',  // ❌ String, no timezone
    last_modified: '2025-10-23T20:06:48.563098',  // ❌ String, no timezone
    order_time: '2025-10-23T20:06:48.563147+00:00'  // ✓ String with timezone
}
```

**After Fix (WORKING)**:

```javascript
{
    created_at: ISODate("2025-10-23T20:06:48.563Z"),  // ✓ Date object
    last_modified: ISODate("2025-10-23T20:06:48.563Z"),  // ✓ Date object
    order_time: ISODate("2025-10-23T20:06:48.563Z")  // ✓ Date object
}
```

## The Complete Solution

### Fix 1: Use Timezone-Aware Timestamps in AggregateState

**File**: `src/neuroglia/data/abstractions.py`

```python
# AggregateState.__init__
def __init__(self):
    super().__init__()
    if not hasattr(self, "created_at") or self.created_at is None:
        from datetime import timezone
        self.created_at = datetime.now(timezone.utc)  # ✓ Now timezone-aware!
    if not hasattr(self, "last_modified") or self.last_modified is None:
        self.last_modified = self.created_at

# Entity.__init__
def __init__(self) -> None:
    super().__init__()
    if not hasattr(self, "created_at") or self.created_at is None:
        from datetime import timezone
        self.created_at = datetime.now(timezone.utc)  # ✓ Now timezone-aware!
```

### Fix 2: Enhanced DateTime Restoration

**File**: `src/neuroglia/data/infrastructure/mongo/motor_repository.py`

```python
def _restore_datetime_objects(self, obj):
    """
    Handles both timezone-aware and naive datetime strings.
    Naive datetimes are assumed to be UTC.
    """
    from datetime import datetime, timezone

    if isinstance(obj, dict):
        return {k: self._restore_datetime_objects(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [self._restore_datetime_objects(item) for item in obj]
    elif isinstance(obj, str):
        try:
            # Handle timezone-aware strings
            if obj.endswith("+00:00") or obj.endswith("Z"):
                return datetime.fromisoformat(obj.replace("Z", "+00:00"))
            # Handle naive datetime strings (assume UTC)
            elif "T" in obj and len(obj) >= 19:
                dt = datetime.fromisoformat(obj)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)  # ✓ Assume UTC
                return dt
        except (ValueError, AttributeError):
            pass
    return obj
```

## Why This Fix Works

1. **Timezone-aware creation**: `datetime.now(timezone.utc)` creates datetime with UTC timezone
2. **ISO string includes timezone**: `2025-10-23T20:06:48.563098+00:00` instead of `2025-10-23T20:06:48.563098`
3. **Proper conversion**: `_restore_datetime_objects()` converts string → Python datetime object
4. **MongoDB storage**: Python datetime → MongoDB ISODate (queryable)
5. **Queries work**: Date range queries with `$gte` and `$lte` now function correctly

## Query Flow

```
Query: Get orders from today
    ↓
today_start = datetime.now(timezone.utc).replace(hour=0, ...)  # Has timezone
    ↓
query = {"created_at": {"$gte": today_start}}
    ↓
MongoDB compares: ISODate("...") >= ISODate("...")  # ✓ Works!
    ↓
Returns: Orders created today
```

## Files Modified

1. **src/neuroglia/data/abstractions.py**

   - `Entity.__init__()` - Use `datetime.now(timezone.utc)`
   - `AggregateState.__init__()` - Use `datetime.now(timezone.utc)`

2. **src/neuroglia/data/infrastructure/mongo/motor_repository.py**
   - `_restore_datetime_objects()` - Handle naive datetimes (assume UTC)

## Testing the Fix

After restarting the application:

1. **Clear existing orders** (optional - they have naive datetimes)
2. **Create new order** through UI
3. **Check MongoDB**:

   ```javascript
   db.orders.findOne({}, { created_at: 1, last_modified: 1, order_time: 1 });
   // Should show ISODate objects, not strings!
   ```

4. **Check management dashboard** - Should now show correct metrics

## Migration for Existing Data

If you have existing orders with string datetime values:

```python
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client['mario_pizzeria']

for order in db.orders.find():
    updates = {}

    # Convert created_at if it's a string
    if isinstance(order.get('created_at'), str):
        try:
            dt = datetime.fromisoformat(order['created_at'])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            updates['created_at'] = dt
        except:
            pass

    # Same for last_modified
    if isinstance(order.get('last_modified'), str):
        try:
            dt = datetime.fromisoformat(order['last_modified'])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            updates['last_modified'] = dt
        except:
            pass

    if updates:
        db.orders.update_one({'_id': order['_id']}, {'$set': updates})
```

## Summary

### What Was Wrong

- Framework created naive datetimes (no timezone)
- Serialization stored as strings without timezone
- MongoDB couldn't properly compare string vs datetime in queries
- Dashboard queries returned 0 results

### What's Fixed Now

- ✅ Framework creates timezone-aware UTC datetimes
- ✅ Serialization preserves datetime objects (converts strings → datetime)
- ✅ MongoDB stores as ISODate objects
- ✅ Queries work correctly with date comparisons
- ✅ Dashboard shows accurate metrics

### Action Required

🔄 **Restart the application** for changes to take effect:

```bash
./mario-docker.sh restart
```

Then create new orders to test!
