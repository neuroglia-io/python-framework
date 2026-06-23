# Missing Abstract Methods Fix - Repository Interface Implementation

## 🐛 Issues

### Issue 1: MongoCustomerRepository

**Error**: `TypeError: Can't instantiate abstract class MongoCustomerRepository without an implementation for abstract method 'get_frequent_customers_async'`

### Issue 2: MongoOrderRepository

**Error**: `TypeError: Can't instantiate abstract class MongoOrderRepository without an implementation for abstract method 'get_orders_by_date_range_async'`

**Root Cause**: When refactoring to use MotorRepository base class, we removed implementations of abstract methods that were still defined in the repository interfaces.

## 🔍 Analysis

### Interface Contract (ICustomerRepository)

```python
class ICustomerRepository(Repository[Customer, str], ABC):
    """Repository interface for managing customers"""

    @abstractmethod
    async def get_by_phone_async(self, phone: str) -> Optional[Customer]:
        """Get a customer by phone number"""
        pass

    @abstractmethod
    async def get_by_email_async(self, email: str) -> Optional[Customer]:
        """Get a customer by email address"""
        pass

    @abstractmethod
    async def get_frequent_customers_async(self, min_orders: int = 5) -> List[Customer]:
        """Get customers with at least the specified number of orders"""
        pass
```

### Implementation Gap

The `MongoCustomerRepository` was missing the implementation of `get_frequent_customers_async()`, which is required by the abstract interface.

## ✅ Solution

### Fix 1: MongoCustomerRepository - get_frequent_customers_async()

Added the implementation using MongoDB aggregation pipeline:

```python
async def get_frequent_customers_async(self, min_orders: int = 5) -> List[Customer]:
    """
    Get customers with at least the specified number of orders.

    This uses MongoDB aggregation to join with orders collection and count.

    Args:
        min_orders: Minimum number of orders required (default: 5)

    Returns:
        List of customers who have placed at least min_orders orders
    """
    # Use MongoDB aggregation pipeline to count orders per customer
    pipeline = [
        {
            "$lookup": {
                "from": "orders",
                "localField": "id",
                "foreignField": "state.customer_id",
                "as": "orders"
            }
        },
        {
            "$addFields": {
                "order_count": {"$size": "$orders"}
            }
        },
        {
            "$match": {
                "order_count": {"$gte": min_orders}
            }
        },
        {
            "$project": {
                "orders": 0,  # Don't return the orders array
                "order_count": 0
            }
        }
    ]

    # Execute aggregation
    cursor = self.collection.aggregate(pipeline)

    # Deserialize results
    customers = []
    async for doc in cursor:
        customer = self._deserialize_entity(doc)
        customers.append(customer)

    return customers
```

## 🎯 Key Points

### 1. MongoDB Aggregation Pipeline

The implementation uses a multi-stage aggregation:

1. **$lookup**: Joins customers with orders collection

   - Links `customer.id` with `order.state.customer_id`
   - Creates temporary `orders` array field

2. **$addFields**: Calculates order count

   - Adds `order_count` field with size of orders array

3. **$match**: Filters by minimum orders

   - Only includes customers with `order_count >= min_orders`

4. **$project**: Cleans up output
   - Removes temporary `orders` array
   - Removes `order_count` field

### 2. Entity Deserialization

Uses the base class's `_deserialize_entity()` method to properly reconstruct Customer aggregates from MongoDB documents, handling the state-based persistence pattern.

### 3. Async Iteration

Uses `async for` to iterate over the Motor cursor, maintaining async context throughout the operation.

---

### Fix 2: MongoOrderRepository - get_orders_by_date_range_async()

Added date range query implementation:

**File**: `samples/mario-pizzeria/integration/repositories/mongo_order_repository.py`

```python
async def get_orders_by_date_range_async(
    self, start_date: datetime, end_date: datetime
) -> List[Order]:
    """
    Get orders within a date range.

    Queries orders created between start_date and end_date (inclusive).

    Args:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of orders created within the date range
    """
    query = {
        "state.created_at": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    return await self.find_async(query)
```

**Key Points**:

1. **MongoDB Date Range Query**: Uses `$gte` (greater than or equal) and `$lte` (less than or equal) operators
2. **State-Based Querying**: Queries `state.created_at` field from AggregateRoot state
3. **Simple and Efficient**: Leverages MongoDB's native date comparison
4. **Reuses Base Method**: Uses `find_async()` from MotorRepository base class

---

## 📊 Files Modified

### MongoCustomerRepository

**File**: `samples/mario-pizzeria/integration/repositories/mongo_customer_repository.py`

**Changes**:

- Added import: `from typing import Optional, List`
- Added method: `get_frequent_customers_async(self, min_orders: int = 5)`
- Lines added: ~50

## 🧪 Testing

### Verification Steps

1. **Application Startup**: ✅

   ```bash
   docker restart mario-pizzeria-mario-pizzeria-app-1
   # Result: INFO: Application startup complete.
   ```

2. **No Abstract Method Error**: ✅

   - No more `TypeError: Can't instantiate abstract class` errors

3. **Login Flow**: Should now work
   - Keycloak authentication
   - Profile auto-creation
   - MongoDB persistence

### Test Query

To manually test the implementation:

```python
# In Python shell or handler
from domain.repositories import ICustomerRepository

# Get customers with at least 3 orders
frequent_customers = await customer_repository.get_frequent_customers_async(min_orders=3)

# Should return list of Customer aggregates
print(f"Found {len(frequent_customers)} frequent customers")
```

## 🔗 Related

This fix completes the MotorRepository migration:

1. **MotorRepository.configure()**: ✅ Implemented with scoped lifetime
2. **AggregateRoot Support**: ✅ State-based serialization
3. **Custom Query Methods**: ✅ All abstract methods implemented

## 📝 Lessons Learned

1. **Interface Contracts Must Be Satisfied**: All abstract methods in interfaces must be implemented, even after refactoring to use base classes

2. **Aggregation Pipelines**: MongoDB aggregation is powerful for cross-collection queries without loading all data into memory

3. **Testing After Refactoring**: Always verify that all interface methods are still implemented after major refactoring

4. **Python Cache**: Docker container restarts may require full stop/start (not just restart) to clear Python bytecode cache

## ✅ Status

**RESOLVED** ✅

Application now starts without errors and all ICustomerRepository interface methods are properly implemented in MongoCustomerRepository.

**Next**: Test integration with Keycloak login and profile auto-creation to verify the complete flow works end-to-end.
