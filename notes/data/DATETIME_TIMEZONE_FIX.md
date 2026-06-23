# DateTime Timezone Awareness Fix - Management Dashboard

## Issue Summary

**Error**: `"can't compare offset-naive and offset-aware datetimes"`

**Location**: `application/queries/get_overview_statistics_query.py`

**Status**: ✅ FIXED

---

## Problem Description

When accessing the management dashboard (`/management`), the application returned a 500 Internal Server Error with the message:

```
{
  "title": "Internal Server Error",
  "status": 500,
  "detail": "can't compare offset-naive and offset-aware datetimes"
}
```

### Root Cause

The `GetOverviewStatisticsHandler` was using `datetime.now()` to create time ranges for filtering orders:

```python
# BEFORE (INCORRECT)
now = datetime.now()  # Creates offset-naive datetime
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
```

However, the Order entity stores all timestamps as **timezone-aware** datetimes using `datetime.now(timezone.utc)`:

```python
# From domain/entities/order.py
order_time=datetime.now(timezone.utc)  # Creates offset-aware datetime
confirmed_time=datetime.now(timezone.utc)
delivered_time=datetime.now(timezone.utc)
```

When Python tried to compare the offset-naive `today_start` with the offset-aware `order.state.order_time`, it threw a `TypeError` because you cannot compare datetimes with different timezone awareness states.

---

## Solution

Changed `datetime.now()` to `datetime.now(timezone.utc)` in the query handler to create timezone-aware datetimes that match the order timestamps.

### Code Changes

**File**: `application/queries/get_overview_statistics_query.py`

**Import Statement**:

```python
# BEFORE
from datetime import datetime, timedelta

# AFTER
from datetime import datetime, timedelta, timezone
```

**Time Range Calculation**:

```python
# BEFORE
now = datetime.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

# AFTER
now = datetime.now(timezone.utc)  # Now timezone-aware
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
```

---

## Verification

After the fix:

1. **Management dashboard loads successfully** - `/management` endpoint returns 200 OK
2. **Statistics display correctly** - All metrics (orders, revenue, averages) are calculated
3. **Time comparisons work** - Today vs yesterday comparisons function properly
4. **SSE streaming operational** - Real-time updates work without errors

---

## Best Practice: Timezone Awareness in Python

### The Rule

**ALWAYS use timezone-aware datetimes when working with timestamps across your application.**

### Why?

1. **Consistency**: All datetime values use the same timezone reference (UTC)
2. **Comparability**: Timezone-aware datetimes can be safely compared
3. **Unambiguous**: No confusion about "local time" vs "server time" vs "UTC"
4. **Database Compatibility**: MongoDB and most databases handle timezone-aware datetimes correctly

### How to Apply

**✅ DO THIS** (Timezone-Aware):

```python
from datetime import datetime, timezone

# Create current time with UTC timezone
now = datetime.now(timezone.utc)

# Create specific time with UTC timezone
specific_time = datetime(2025, 10, 22, 12, 30, 0, tzinfo=timezone.utc)

# Parse ISO string with timezone
from datetime import datetime
dt = datetime.fromisoformat("2025-10-22T12:30:00+00:00")
```

**❌ DON'T DO THIS** (Offset-Naive):

```python
from datetime import datetime

# Creates offset-naive datetime - AVOID
now = datetime.now()

# Creates offset-naive datetime - AVOID
specific_time = datetime(2025, 10, 22, 12, 30, 0)
```

---

## Impact on Mario's Pizzeria

### Files Using Timezone-Aware Datetimes

All domain entities correctly use `datetime.now(timezone.utc)`:

- **Order Entity** (`domain/entities/order.py`):

  - `order_time`
  - `confirmed_time`
  - `actual_ready_time`
  - `delivered_time`
  - `out_for_delivery_time`

- **Pizza Entity** (`domain/entities/pizza.py`):
  - Any timestamp fields

### Files That Were Fixed

- ✅ `application/queries/get_overview_statistics_query.py`

### Files to Audit (Future)

Check these files if similar datetime comparison issues arise:

- Other query handlers that filter by date/time
- Any service that compares datetime values
- Background tasks that process time-based logic

---

## Testing

To verify the fix works:

1. **Access Management Dashboard**:

   ```bash
   # Login as manager
   http://localhost:3000/management
   ```

   - Should load without errors
   - Metrics should display

2. **Check Logs**:

   ```bash
   docker logs mario-pizzeria-mario-pizzeria-app-1 | grep "GetOverviewStatistics"
   ```

   - Should see successful query execution
   - No timezone-related errors

3. **Test Time Comparisons**:
   - Place orders as customer
   - Verify "Today's Orders" count increases
   - Check "Orders Change %" shows comparison with yesterday
   - Confirm average times calculate correctly

---

## Related Documentation

- **Python datetime documentation**: https://docs.python.org/3/library/datetime.html#aware-and-naive-objects
- **MongoDB datetime handling**: Uses BSON Date type (always UTC)
- **Framework best practices**: See `.github/copilot-instructions.md`

---

## Lessons Learned

1. **Consistent Timezone Strategy**: The codebase correctly uses UTC throughout - this was just a missed spot
2. **Type Safety**: Consider using a type alias or custom datetime wrapper to enforce timezone awareness
3. **Testing**: Add integration tests that exercise datetime comparisons
4. **Code Review**: Watch for `datetime.now()` without `timezone.utc` in code reviews

---

## Prevention

To prevent similar issues in the future:

1. **Linting Rule**: Consider adding a linter rule to flag `datetime.now()` without timezone
2. **Code Pattern**: Use a utility function for "now":

   ```python
   # utils/datetime_helpers.py
   from datetime import datetime, timezone

   def utc_now() -> datetime:
       """Get current UTC time (timezone-aware)"""
       return datetime.now(timezone.utc)

   # Usage
   from utils.datetime_helpers import utc_now
   now = utc_now()  # Always timezone-aware
   ```

3. **Documentation**: Update team guidelines to always use timezone-aware datetimes

---

## Conclusion

This was a simple but critical fix. The error message was clear and diagnostic, making the issue easy to identify and resolve. The fix ensures that all datetime comparisons throughout the management dashboard work correctly.

**Status**: ✅ Resolved - Management dashboard fully operational
