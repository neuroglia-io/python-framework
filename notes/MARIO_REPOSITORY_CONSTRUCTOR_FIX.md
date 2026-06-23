# Mario Pizzeria Repository Constructor Fix

## Issue Summary

**Problem**: TypeError during mario-pizzeria startup when `MotorRepository.configure()` tried to instantiate custom repositories:

```
TypeError: MongoPizzaRepository.__init__() got an unexpected keyword argument 'client'
```

**Root Cause**: Constructor signature mismatch between what `MotorRepository.configure()` passes and what custom repositories expected.

## Analysis

### What MotorRepository.configure() Passes

From `src/neuroglia/data/infrastructure/mongo/motor_repository.py` lines 690-693:

```python
repository = implementation_type(
    client=client,
    database_name=database_name,
    collection_name=collection_name,
    serializer=serializer,
    entity_type=entity_type,
    mediator=mediator,
)
```

**Parameters passed**:

1. `client: AsyncIOMotorClient`
2. `database_name: str`
3. `collection_name: str`
4. `serializer: JsonSerializer`
5. `entity_type: type[TEntity]`
6. `mediator: Optional[Mediator]`

### What Custom Repositories Expected (Before Fix)

Old constructor signature:

```python
def __init__(
    self,
    mongo_client: AsyncIOMotorClient,
    serializer: JsonSerializer,
    mediator: Optional["Mediator"] = None,
):
    super().__init__(
        client=mongo_client,
        database_name="mario_pizzeria",  # Hardcoded
        collection_name="pizzas",         # Hardcoded
        serializer=serializer,
        entity_type=Pizza,
        mediator=mediator,
    )
```

**Issues**:

- Parameter name mismatch: `mongo_client` vs `client`
- Missing required parameters: `database_name`, `collection_name`, `entity_type`
- Hardcoded values passed to parent class instead of using factory-provided values

## Solution

Update all four custom repository constructors to match `MotorRepository.configure()` signature:

### Fixed Constructor Pattern

```python
def __init__(
    self,
    client: AsyncIOMotorClient,
    database_name: str,
    collection_name: str,
    serializer: JsonSerializer,
    entity_type: type[Pizza],  # Specific entity type per repository
    mediator: Optional["Mediator"] = None,
):
    """
    Initialize the Pizza repository.

    Args:
        client: Motor async MongoDB client
        database_name: Name of the database
        collection_name: Name of the collection
        serializer: JSON serializer for entity conversion
        entity_type: Type of entity stored in this repository
        mediator: Optional Mediator for automatic domain event publishing
    """
    super().__init__(
        client=client,
        database_name=database_name,
        collection_name=collection_name,
        serializer=serializer,
        entity_type=entity_type,
        mediator=mediator,
    )
```

## Files Modified

All four custom repositories updated with identical pattern:

1. ✅ `samples/mario-pizzeria/integration/repositories/mongo_pizza_repository.py`

   - Changed constructor signature to accept 6 parameters
   - Updated super().**init**() to use passed parameters

2. ✅ `samples/mario-pizzeria/integration/repositories/mongo_customer_repository.py`

   - Applied same fix
   - Entity type: `type[Customer]`

3. ✅ `samples/mario-pizzeria/integration/repositories/mongo_order_repository.py`

   - Applied same fix
   - Entity type: `type[Order]`

4. ✅ `samples/mario-pizzeria/integration/repositories/mongo_kitchen_repository.py`
   - Applied same fix
   - Entity type: `type[Kitchen]`

## Verification

All repository files compile successfully:

```bash
poetry run python -m py_compile \
  samples/mario-pizzeria/integration/repositories/mongo_customer_repository.py \
  samples/mario-pizzeria/integration/repositories/mongo_order_repository.py \
  samples/mario-pizzeria/integration/repositories/mongo_kitchen_repository.py \
  samples/mario-pizzeria/integration/repositories/mongo_pizza_repository.py
```

**Result**: ✅ All files compile without errors

## Key Learnings

### When Using MotorRepository.configure()

Custom repository constructors **MUST** accept all parameters that `configure()` passes:

```python
# Required constructor signature for custom repositories
def __init__(
    self,
    client: AsyncIOMotorClient,       # MongoDB client
    database_name: str,                # Database name from factory
    collection_name: str,              # Collection name from factory
    serializer: JsonSerializer,        # Serializer from DI container
    entity_type: type[TEntity],        # Entity type from factory
    mediator: Optional[Mediator] = None  # Optional mediator
):
```

### Benefits of Factory Pattern

1. **Centralized Configuration**: Database and collection names configured once in `main.py`
2. **Testability**: Easy to inject test database names during testing
3. **Flexibility**: Can create multiple repository instances with different configurations
4. **Type Safety**: Entity type passed explicitly ensures type correctness

### Registration Pattern in main.py

```python
# Domain repository interface -> Implementation type with configuration
MotorRepository.configure(
    services=builder.services,
    domain_repository_type=IPizzaRepository,
    implementation_type=MongoPizzaRepository,
    database_name="mario_pizzeria",
    collection_name="pizzas",
    entity_type=Pizza,
)
```

The factory creates instances dynamically using the constructor signature, so implementations must match expectations.

## Pre-Existing Type Warnings

All repositories show type compatibility warnings from `TracedRepositoryMixin`:

```
Base classes for class "MongoPizzaRepository" define method "get_async" in incompatible way
```

**Status**: These are pre-existing issues unrelated to this fix. They do not prevent compilation or runtime execution.

## Testing Status

- ✅ **Compilation**: All four repositories compile successfully
- ⏳ **Runtime**: Requires infrastructure (MongoDB, Redis) to be running
- ⏳ **Integration**: Full startup test pending infrastructure availability

## Related Context

This fix completes the authentication unification work that included:

- DualAuthService Redis integration
- JWT authentication with FastAPI dependencies
- Session authentication with Redis backend
- Migration from old oauth.py to new auth.py pattern

The repository registration issue was discovered during mario-pizzeria startup after completing the auth unification.

## Date

2024-12-28
