# Repository Unification Migration Guide

## Overview

The Neuroglia framework has simplified and consolidated its repository abstractions to provide a cleaner, more maintainable approach to data persistence. This guide will help you migrate from the deprecated patterns to the new unified approach.

## What Changed?

### 🎯 Key Changes

1. **JsonSerializer Enhanced**: Now automatically handles both `Entity` and `AggregateRoot` types
2. **StateBasedRepository Deprecated**: Use `Repository` directly instead
3. **AggregateSerializer Deprecated**: `JsonSerializer` now handles all serialization
4. **Cleaner Storage Format**: Stores pure state without metadata wrappers
5. **Simplified Repository Implementation**: Less boilerplate, more straightforward

### 📦 Migration Benefits

- **Simpler Code**: Less abstraction layers to understand
- **Cleaner Storage**: JSON files/documents are pure state (queryable, readable)
- **Better Performance**: Eliminated unnecessary metadata wrapper overhead
- **Easier Testing**: Straightforward serialization behavior
- **Type Safety**: Proper handling of Entity and AggregateRoot ID access

## Migration Paths

### 1. Repository Implementation

#### ❌ Old Approach (Deprecated)

```python
from neuroglia.data.infrastructure import StateBasedRepository
from neuroglia.serialization import AggregateSerializer

class UserRepository(StateBasedRepository[User, str]):
    def __init__(self, collection):
        super().__init__(
            entity_type=User,
            serializer=AggregateSerializer()
        )
        self._collection = collection

    async def add_async(self, entity: User) -> None:
        # Serializer produces {"state": {...}, "type": "..."}
        doc = self.serializer.serialize_to_dict(entity)
        await self._collection.insert_one(doc)
```

#### ✅ New Approach (Recommended)

```python
from neuroglia.data import Repository
from neuroglia.serialization import JsonSerializer

class UserRepository(Repository[User, str]):
    def __init__(self, collection):
        self.serializer = JsonSerializer()
        self._collection = collection

    def _get_id(self, entity: User) -> Optional[str]:
        """Extract ID from Entity or AggregateRoot."""
        # Handle Entity with id() method
        if hasattr(entity, "id") and callable(entity.id):
            return entity.id()
        # Handle Entity with id property
        return getattr(entity, "id", None)

    async def add_async(self, entity: User) -> None:
        # Serializer produces clean state: {"user_id": "...", "name": "..."}
        doc = self.serializer.serialize_to_dict(entity)
        await self._collection.insert_one(doc)
```

### 2. FileSystemRepository Pattern

#### ❌ Old Approach

```python
from neuroglia.data.infrastructure import StateBasedRepository
from neuroglia.serialization import AggregateSerializer

class FileSystemUserRepository(StateBasedRepository[User, str]):
    def __init__(self, base_path: str):
        super().__init__(
            entity_type=User,
            serializer=AggregateSerializer()
        )
        self._base_path = Path(base_path)
```

#### ✅ New Approach

```python
from neuroglia.data import Repository
from neuroglia.serialization import JsonSerializer
from pathlib import Path

class FileSystemUserRepository(Repository[User, str]):
    def __init__(self, base_path: str):
        self.serializer = JsonSerializer()
        self._base_path = Path(base_path)

    def _get_id(self, entity: User) -> Optional[str]:
        if hasattr(entity, "id") and callable(entity.id):
            return entity.id()
        return getattr(entity, "id", None)

    def _is_aggregate_root(self, entity: User) -> bool:
        """Check if entity is an AggregateRoot."""
        from neuroglia.data.abstractions import AggregateRoot
        return isinstance(entity, AggregateRoot)

    async def add_async(self, entity: User) -> None:
        entity_id = self._get_id(entity)
        if entity_id is None:
            entity_id = str(uuid.uuid4())
            if self._is_aggregate_root(entity):
                entity._state.id = entity_id
            else:
                entity.id = entity_id

        # Serialize to clean JSON
        file_path = self._base_path / f"{entity_id}.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        json_text = self.serializer.serialize_to_text(entity)
        file_path.write_text(json_text, encoding="utf-8")
```

### 3. Serialization

#### ❌ Old Approach

```python
from neuroglia.serialization import AggregateSerializer

serializer = AggregateSerializer()

# Produces: {"state": {"user_id": "123", "name": "John"}, "type": "User"}
json_text = serializer.serialize_to_text(user)

# Expects wrapped format
user = serializer.deserialize_from_text(json_text, User)
```

#### ✅ New Approach

```python
from neuroglia.serialization import JsonSerializer

serializer = JsonSerializer()

# Produces: {"user_id": "123", "name": "John"}
json_text = serializer.serialize_to_text(user)

# Handles both wrapped (old) and clean (new) formats automatically
user = serializer.deserialize_from_text(json_text, User)
```

### 4. Storage Format

#### ❌ Old Format (Metadata Wrapper)

```json
{
  "state": {
    "user_id": "123",
    "name": "John Doe",
    "email": "john@example.com"
  },
  "type": "User",
  "version": 1
}
```

**Problems:**

- Cannot query by `name` directly (must query `state.name`)
- Extra nesting complicates database queries
- Metadata clutters storage
- Larger file/document size

#### ✅ New Format (Clean State)

```json
{
  "user_id": "123",
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Benefits:**

- Direct querying: `db.users.find({"name": "John Doe"})`
- Cleaner, more readable storage
- Smaller storage size (no metadata overhead)
- Standard JSON format compatible with any tool

## Implementation Patterns

### Entity vs AggregateRoot Handling

The unified approach properly handles both Entity and AggregateRoot types:

```python
def _get_id(self, entity: TEntity) -> Optional[TKey]:
    """
    Extract ID from Entity or AggregateRoot.

    - Entity: Has id property directly
    - AggregateRoot: Has id() method on _state
    """
    # Handle AggregateRoot with id() method
    if hasattr(entity, "id") and callable(entity.id):
        return entity.id()

    # Handle Entity with id property
    return getattr(entity, "id", None)

def _is_aggregate_root(self, entity: TEntity) -> bool:
    """Check if entity is an AggregateRoot."""
    from neuroglia.data.abstractions import AggregateRoot
    return isinstance(entity, AggregateRoot)
```

### ID Generation Pattern

```python
async def add_async(self, entity: TEntity) -> None:
    """Add entity with automatic ID generation if needed."""
    entity_id = self._get_id(entity)

    if entity_id is None:
        # Generate new ID
        entity_id = str(uuid.uuid4())

        # Set ID based on entity type
        if self._is_aggregate_root(entity):
            # AggregateRoot: set on _state
            entity._state.id = entity_id
        else:
            # Entity: set directly
            entity.id = entity_id

    # Continue with persistence...
```

### Serialization Pattern

```python
# Serialize (automatic state extraction for AggregateRoot)
json_text = self.serializer.serialize_to_text(entity)
file_path.write_text(json_text, encoding="utf-8")

# Deserialize (automatic reconstruction for AggregateRoot)
json_text = file_path.read_text(encoding="utf-8")
entity = self.serializer.deserialize_from_text(json_text, entity_type)
```

## Backward Compatibility

### Old Data Migration

The new JsonSerializer **automatically handles old format data**:

```python
# Old format with metadata wrapper
old_json = '''
{
  "state": {"user_id": "123", "name": "John"},
  "type": "User"
}
'''

serializer = JsonSerializer()
user = serializer.deserialize_from_text(old_json, User)
# ✅ Works! Automatically extracts from "state" field

# New format without wrapper
new_json = '{"user_id": "123", "name": "John"}'
user = serializer.deserialize_from_text(new_json, User)
# ✅ Works! Uses data directly
```

### Deprecation Warnings

The old classes remain functional but issue deprecation warnings:

```python
# Will issue DeprecationWarning
from neuroglia.data.infrastructure import StateBasedRepository
repo = StateBasedRepository(entity_type=User, serializer=AggregateSerializer())

# Warning message:
# "StateBasedRepository is deprecated. Use Repository directly with JsonSerializer.
#  See FileSystemRepository or MongoRepository for reference implementations."
```

## Testing Your Migration

### Unit Test Pattern

```python
import pytest
from neuroglia.serialization import JsonSerializer
from neuroglia.data.abstractions import AggregateRoot

class TestUserRepository:
    def setup_method(self):
        self.serializer = JsonSerializer()
        self.repository = UserRepository(collection=mock_collection)

    @pytest.mark.asyncio
    async def test_entity_storage_produces_clean_json(self):
        """Verify storage format is clean state without wrapper."""
        user = User(user_id="123", name="John")

        # Serialize
        json_text = self.serializer.serialize_to_text(user)
        data = json.loads(json_text)

        # Verify clean format (no "state" wrapper)
        assert "state" not in data
        assert data["user_id"] == "123"
        assert data["name"] == "John"

    @pytest.mark.asyncio
    async def test_aggregate_root_round_trip(self):
        """Verify AggregateRoot can be stored and retrieved."""
        order = Order.create(order_id="456", customer="Jane")

        # Serialize and deserialize
        json_text = self.serializer.serialize_to_text(order)
        restored = self.serializer.deserialize_from_text(json_text, Order)

        assert restored.id() == "456"
        assert restored.customer() == "Jane"
```

### Integration Test Pattern

```python
@pytest.mark.integration
class TestUserRepositoryIntegration:
    @pytest.fixture
    async def repository(self, temp_dir):
        """Create repository with temporary storage."""
        return FileSystemUserRepository(base_path=temp_dir)

    @pytest.mark.asyncio
    async def test_full_crud_workflow(self, repository):
        """Test complete create-read-update-delete workflow."""
        # Create
        user = User(user_id="123", name="John")
        await repository.add_async(user)

        # Read
        retrieved = await repository.get_by_id_async("123")
        assert retrieved.name == "John"

        # Update
        retrieved.name = "Jane"
        await repository.update_async(retrieved)

        # Verify update
        updated = await repository.get_by_id_async("123")
        assert updated.name == "Jane"

        # Delete
        await repository.delete_async("123")
        deleted = await repository.get_by_id_async("123")
        assert deleted is None
```

## Reference Implementations

See the following files for complete reference implementations:

- **JsonSerializer**: `src/neuroglia/serialization/json.py`
- **FileSystemRepository**: `src/neuroglia/data/infrastructure/filesystem_repository.py`
- **MongoRepository**: `src/neuroglia/data/infrastructure/mongo/mongo_repository.py`

## Test Coverage

All migration patterns are validated with comprehensive tests:

- **JsonSerializer Tests**: `tests/cases/test_json_serializer_aggregate_support.py` (13 tests)
- **FileSystemRepository Tests**: `tests/cases/test_filesystem_repository_unified.py` (8 tests)
- **MongoRepository Tests**: `tests/cases/test_mongo_repository_unified.py` (8 tests)

**Total: 29 tests covering the unified approach**

## Troubleshooting

### Issue: "Cannot access id on AggregateRoot"

**Problem**: Trying to access `entity.id` on AggregateRoot which uses `entity.id()` method.

**Solution**: Use the `_get_id()` helper pattern:

```python
def _get_id(self, entity):
    if hasattr(entity, "id") and callable(entity.id):
        return entity.id()  # AggregateRoot
    return getattr(entity, "id", None)  # Entity
```

### Issue: "Old data not deserializing"

**Problem**: Existing data has metadata wrapper format.

**Solution**: JsonSerializer handles this automatically! Both formats work:

```python
serializer = JsonSerializer()

# Old format with wrapper
old_data = '{"state": {"id": "123"}, "type": "User"}'
user = serializer.deserialize_from_text(old_data, User)  # ✅ Works

# New format without wrapper
new_data = '{"id": "123"}'
user = serializer.deserialize_from_text(new_data, User)  # ✅ Works
```

### Issue: "Storage files are too large"

**Problem**: Old format includes unnecessary metadata.

**Solution**: Migrate to new format using the new serializer - automatic size reduction:

```python
# Old format: ~150 bytes
{"state": {"id": "123", "name": "John"}, "type": "User", "version": 1}

# New format: ~30 bytes
{"id": "123", "name": "John"}
```

## Summary

The unified approach provides:

✅ **Simpler abstractions** - Use `Repository` directly, no `StateBasedRepository`
✅ **Single serializer** - `JsonSerializer` handles everything
✅ **Cleaner storage** - Pure state JSON without metadata
✅ **Better performance** - Less overhead, smaller storage
✅ **Full compatibility** - Old data still works
✅ **Comprehensive tests** - 29 tests validate the approach

**Next Steps:**

1. Update your repositories to use `Repository` directly
2. Replace `AggregateSerializer` with `JsonSerializer`
3. Implement `_get_id()` and `_is_aggregate_root()` helpers
4. Run your tests to verify everything works
5. Gradually migrate old data to new format (optional - backward compatibility maintained)

For questions or issues, see the reference implementations or test files.
