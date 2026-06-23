# 🔍 MotorRepository Queryable Support

Learn how to use LINQ-style queries with async MotorRepository for powerful data filtering, sorting, and pagination in FastAPI applications.

## 🎯 Overview

Starting with **v0.7.2**, `MotorRepository` extends `QueryableRepository`, providing the same fluent query API available in the synchronous `MongoRepository`. This enables LINQ-style queries for async applications using FastAPI.

**Key Features:**

- ✅ **Fluent API**: Chain `.where()`, `.order_by()`, `.skip()`, `.take()` methods
- ✅ **Type-Safe**: Full IDE autocomplete and type checking
- ✅ **Async Native**: True async/await support with Motor driver
- ✅ **JavaScript Translation**: Lambda expressions translated to MongoDB queries
- ✅ **Pagination**: Built-in skip/take for efficient data loading

## 🏗️ Basic Queryable Usage

### Simple Query Example

```python
from neuroglia.data.infrastructure.mongo import MotorRepository
from integration.models import ProductDto

class GetProductsQueryHandler(QueryHandler[GetProductsQuery, OperationResult]):
    def __init__(self, repository: Repository[ProductDto, str]):
        self.repository = repository

    async def handle_async(self, query: GetProductsQuery) -> OperationResult:
        # Use queryable support for complex filtering
        products = await self.repository.query_async() \
            .where(lambda p: p.price > 10) \
            .where(lambda p: p.in_stock) \
            .order_by(lambda p: p.name) \
            .to_list_async()

        return self.ok(products)
```

### Pagination Example

```python
class ListProductsHandler(QueryHandler[ListProductsQuery, OperationResult]):
    async def handle_async(self, query: ListProductsQuery) -> OperationResult:
        # Paginated query with skip/take
        page = query.page or 1
        page_size = query.page_size or 10
        skip_count = (page - 1) * page_size

        products = await self.repository.query_async() \
            .where(lambda p: p.category == query.category) \
            .order_by(lambda p: p.created_at) \
            .skip(skip_count) \
            .take(page_size) \
            .to_list_async()

        return self.ok({
            "items": products,
            "page": page,
            "page_size": page_size,
            "total": len(products)
        })
```

## 🚀 Advanced Query Patterns

### Complex Filtering

```python
class SearchProductsHandler(QueryHandler[SearchProductsQuery, OperationResult]):
    async def handle_async(self, query: SearchProductsQuery) -> OperationResult:
        # Multiple filters with complex conditions
        results = await self.repository.query_async() \
            .where(lambda p: p.price >= query.min_price) \
            .where(lambda p: p.price <= query.max_price) \
            .where(lambda p: p.category == query.category) \
            .where(lambda p: p.in_stock) \
            .order_by_descending(lambda p: p.rating) \
            .take(20) \
            .to_list_async()

        return self.ok(results)
```

### Sorting and Ordering

```python
# Ascending order
products = await repo.query_async() \
    .order_by(lambda p: p.price) \
    .to_list_async()

# Descending order
products = await repo.query_async() \
    .order_by_descending(lambda p: p.created_at) \
    .to_list_async()

# Multiple sort criteria
products = await repo.query_async() \
    .order_by(lambda p: p.category) \
    .order_by(lambda p: p.name) \
    .to_list_async()
```

### Field Projection (Select)

```python
# Select specific fields (projection)
names = await repo.query_async() \
    .select(lambda p: [p.name, p.price]) \
    .to_list_async()
```

### Single Result Queries

```python
# Get first matching result
first_product = await repo.query_async() \
    .where(lambda p: p.category == "electronics") \
    .order_by(lambda p: p.price) \
    .first_or_default_async()

# Get last matching result
last_order = await repo.query_async() \
    .where(lambda p: p.status == "completed") \
    .order_by_descending(lambda p: p.created_at) \
    .first_or_default_async()
```

## 🔧 Configuration

### Enable Queryable Support

The `MotorRepository` automatically supports queryable operations. Just ensure entities are marked with `@queryable` decorator:

```python
from neuroglia.data.abstractions import queryable

@queryable
class ProductDto:
    """Product read model - marked as queryable"""
    id: str
    name: str
    price: float
    category: str
    in_stock: bool
    created_at: datetime
```

### DataAccessLayer Configuration

Configure read models with Motor for automatic queryable support:

```python
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer

builder = WebApplicationBuilder()

# Motor repositories are automatically queryable
DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type="motor"  # Async Motor driver
).configure(builder, ["integration.models"])

# This registers:
# - Repository[ProductDto, str]
# - QueryableRepository[ProductDto, str]  ← Queryable support!
# - GetByIdQueryHandler[ProductDto, str]
# - ListQueryHandler[ProductDto, str]
```

## 💡 Queryable API Reference

### Available Methods

| Method                         | Description                 | Example                                        |
| ------------------------------ | --------------------------- | ---------------------------------------------- |
| `.where(lambda)`               | Filter results by condition | `.where(lambda p: p.price > 10)`               |
| `.order_by(lambda)`            | Sort ascending              | `.order_by(lambda p: p.name)`                  |
| `.order_by_descending(lambda)` | Sort descending             | `.order_by_descending(lambda p: p.created_at)` |
| `.skip(int)`                   | Skip N results              | `.skip(10)`                                    |
| `.take(int)`                   | Take N results              | `.take(20)`                                    |
| `.select(lambda)`              | Project fields              | `.select(lambda p: [p.name, p.price])`         |
| `.first_or_default_async()`    | Get first result or None    | `.first_or_default_async()`                    |
| `.to_list_async()`             | Execute and return list     | `.to_list_async()`                             |

### Lambda Expression Support

Queryable translates Python lambda expressions to MongoDB `$where` JavaScript:

```python
# Python expression
.where(lambda p: p.price > 10 and p.in_stock)

# Translates to MongoDB
{"$where": "this.price > 10 && this.in_stock"}
```

**Supported Operators:**

- Comparison: `>`, `<`, `>=`, `<=`, `==`, `!=`
- Logical: `and`, `or`
- Property access: `p.price`, `p.category`

## 🧪 Testing Queryable Repositories

```python
import pytest
from neuroglia.data.infrastructure.mongo import MotorRepository
from neuroglia.serialization.json import JsonSerializer

@pytest.fixture
async def repository(motor_client):
    """Create test repository with queryable support"""
    repo = MotorRepository[ProductDto, str](
        client=motor_client,
        database_name="test_db",
        collection_name="products",
        serializer=JsonSerializer(),
        entity_type=ProductDto,
        mediator=None
    )
    return repo

@pytest.mark.asyncio
async def test_queryable_filtering(repository):
    """Test queryable where clause"""
    # Seed test data
    await repository.add_async(ProductDto(id="1", name="Widget", price=15.0, in_stock=True))
    await repository.add_async(ProductDto(id="2", name="Gadget", price=5.0, in_stock=True))

    # Query with filter
    results = await repository.query_async() \
        .where(lambda p: p.price > 10) \
        .to_list_async()

    assert len(results) == 1
    assert results[0].name == "Widget"

@pytest.mark.asyncio
async def test_queryable_pagination(repository):
    """Test queryable skip/take"""
    # Seed test data
    for i in range(15):
        await repository.add_async(
            ProductDto(id=str(i), name=f"Product{i}", price=10.0, in_stock=True)
        )

    # Get page 2 (items 10-14)
    page_2 = await repository.query_async() \
        .order_by(lambda p: p.name) \
        .skip(10) \
        .take(5) \
        .to_list_async()

    assert len(page_2) == 5
    assert page_2[0].name == "Product10"
```

## 🔄 Migration from Non-Queryable

If you're upgrading from pre-v0.7.2 where `MotorRepository` wasn't queryable:

### Before (v0.7.1 and earlier)

```python
# Had to use find_async with raw MongoDB filters
products = await repository.find_async({
    "price": {"$gt": 10},
    "in_stock": True
})

# Manual sorting and pagination
products = await repository.find_async({"category": "electronics"})
products.sort(key=lambda p: p.price)
products = products[10:20]
```

### After (v0.7.2+)

```python
# Clean, type-safe queryable API
products = await repository.query_async() \
    .where(lambda p: p.price > 10) \
    .where(lambda p: p.in_stock) \
    .order_by(lambda p: p.price) \
    .skip(10) \
    .take(10) \
    .to_list_async()
```

## 🎯 Best Practices

### 1. **Use Queryable for Complex Queries**

```python
# ✅ Good: Use queryable for complex filtering
results = await repo.query_async() \
    .where(lambda p: p.price > 10) \
    .where(lambda p: p.in_stock) \
    .to_list_async()

# ❌ Avoid: Manual filtering after fetch
all_items = await repo.get_all_async()
results = [p for p in all_items if p.price > 10 and p.in_stock]
```

### 2. **Always Use Pagination for Large Datasets**

```python
# ✅ Good: Paginate large result sets
page_items = await repo.query_async() \
    .skip((page - 1) * page_size) \
    .take(page_size) \
    .to_list_async()

# ❌ Avoid: Loading all records
all_items = await repo.query_async().to_list_async()
```

### 3. **Combine with Direct Methods When Appropriate**

```python
# For simple ID lookup, use direct method
product = await repo.get_async("product123")

# For complex queries, use queryable
products = await repo.query_async() \
    .where(lambda p: p.category == "electronics") \
    .where(lambda p: p.price > 100) \
    .to_list_async()
```

### 4. **Order Before Skip/Take**

```python
# ✅ Good: Order first for consistent pagination
results = await repo.query_async() \
    .where(lambda p: p.in_stock) \
    .order_by(lambda p: p.created_at) \
    .skip(10) \
    .take(10) \
    .to_list_async()

# ❌ Avoid: Unordered pagination (non-deterministic)
results = await repo.query_async() \
    .skip(10) \
    .take(10) \
    .to_list_async()
```

## 🔗 Related Documentation

- [Data Access Layer Configuration](../features/data-access.md)
- [Repository Pattern](../patterns/repository.md)
- [Custom Repository Mappings](./custom-repository-mappings.md)
- [MongoDB Integration](../features/data-access.md#mongodb-repositories)

## 🐛 Troubleshooting

### Query Not Filtering Correctly

**Issue**: Query returns all results instead of filtering

**Solution**: Check lambda expression syntax. Only simple comparisons are supported:

```python
# ✅ Supported
.where(lambda p: p.price > 10)
.where(lambda p: p.category == "electronics")

# ❌ Not supported (complex Python logic)
.where(lambda p: p.name.startswith("Product") and len(p.name) > 5)
```

### TypeScript/JavaScript Translation Issues

**Issue**: Lambda doesn't translate correctly to MongoDB query

**Solution**: Use simple property comparisons. Complex Python functions won't translate:

```python
# ✅ Good: Simple comparison
.where(lambda p: p.price > 10)

# ❌ Avoid: Python-specific functions
.where(lambda p: p.name.lower().startswith("prod"))
```

For complex queries, use `find_async()` with raw MongoDB filters:

```python
# Use raw MongoDB query for complex patterns
results = await repo.find_async({
    "name": {"$regex": "^Prod", "$options": "i"}
})
```

## 📈 Performance Considerations

1. **Indexes**: Ensure MongoDB indexes exist for queried fields
2. **Projection**: Use `.select()` to reduce data transfer
3. **Pagination**: Always use `.skip()` and `.take()` for large datasets
4. **Sorting**: Add indexes for fields used in `.order_by()`

```python
# Efficient query with projection and pagination
results = await repo.query_async() \
    .where(lambda p: p.category == "electronics") \
    .select(lambda p: [p.id, p.name, p.price]) \
    .order_by(lambda p: p.price) \
    .skip(page * page_size) \
    .take(page_size) \
    .to_list_async()
```

---

**Next Steps:**

- Learn about [Custom Repository Mappings](./custom-repository-mappings.md)
- Explore [CQRS Query Handlers](../features/simple-cqrs.md)
- Read about [MongoDB Best Practices](../features/data-access.md)
