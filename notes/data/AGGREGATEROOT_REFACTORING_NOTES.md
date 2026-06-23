# AggregateRoot Refactoring Notes

## Overview

Refactoring all samples to use Neuroglia's `AggregateRoot[TState, TKey]` with state separation pattern and multipledispatch event handlers.

## Pattern Being Implemented

### Key Principles

1. **Use Neuroglia's AggregateRoot** - `from neuroglia.data.abstractions import AggregateRoot`
2. **State in same file as aggregate** - Easier to understand and maintain
3. **Use `register_event()` not `raise_event()`** - More logical naming
4. **State handles events with `@dispatch`** - From `multipledispatch` library
5. **Pattern: `self.state.on(self.register_event(Event(...)))`** - Explicit flow

### File Structure

```python
# domain/entities/customer.py (example)

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState, DomainEvent

# State class first (in same file)
@dataclass
class CustomerState(AggregateState[str]):
    name: Optional[str] = None
    email: Optional[str] = None

    @dispatch(CustomerCreatedEvent)
    def on(self, event: CustomerCreatedEvent) -> None:
        self.id = event.aggregate_id
        self.name = event.name
        self.email = event.email

# Aggregate class second (in same file)
class Customer(AggregateRoot[CustomerState, str]):
    def __init__(self, name: str, email: str):
        super().__init__()
        self.state.on(
            self.register_event(
                CustomerCreatedEvent(str(uuid4()), name, email)
            )
        )
```

## Documentation Updates Needed

### 1. MkDocs Site Updates (./docs/)

#### Files to Update:

- **`docs/getting-started.md`**

  - Update AggregateRoot usage examples
  - Show multipledispatch pattern
  - Update imports to use Neuroglia's AggregateRoot

- **`docs/features/data-access.md`**

  - Document state separation pattern
  - Show @dispatch event handlers
  - Explain register_event vs raise_event
  - Document state.on() pattern

- **`docs/patterns/domain-driven-design.md`** (if exists)

  - Update aggregate root pattern
  - Show event sourcing ready pattern
  - Document state reconstruction through events

- **`docs/samples/openbank.md`**

  - Already uses correct pattern (BankAccount)
  - Reference as canonical example

- **`docs/mario-pizzeria.md`** (if exists)
  - Update with new Pizza pattern
  - Show simplified aggregate with state handlers

#### New Documentation Needed:

- **`docs/features/event-driven-aggregates.md`**

  - Explain multipledispatch for domain events
  - Show state separation benefits
  - Provide migration guide from custom AggregateRoot
  - Document type checker limitations

- **`docs/guides/aggregate-state-pattern.md`**
  - Complete guide on state separation
  - When to use it vs event sourcing
  - Performance considerations
  - Testing strategies

### 2. API Documentation

- Update docstrings in `neuroglia.data.abstractions.AggregateRoot`
- Add examples showing multipledispatch pattern
- Document `register_event()` return value usage

### 3. Sample Documentation

#### Mario's Pizzeria (`samples/mario-pizzeria/README.md`)

Update to show:

- New AggregateRoot pattern
- Event handlers in state
- State separation benefits

#### OpenBank (`samples/openbank/README.md`)

- Already correct - reference as example
- Add notes about why this pattern was chosen

## Migration Guide Content

### For Custom AggregateRoot Users

````markdown
## Migrating from Custom AggregateRoot

### Before (Custom Implementation)

```python
from ..aggregate_root import AggregateRoot  # Custom

class Pizza(AggregateRoot[PizzaState]):
    def __init__(self, name: str, base_price: Decimal, size: PizzaSize):
        super().__init__()
        self.state.name = name
        self.state.base_price = base_price
        self.state.size = size
        self.raise_event(PizzaCreatedEvent(...))
```
````

### After (Neuroglia's AggregateRoot)

```python
from neuroglia.data.abstractions import AggregateRoot
from multipledispatch import dispatch

@dataclass
class PizzaState(AggregateState[str]):
    name: Optional[str] = None
    base_price: Optional[Decimal] = None
    size: Optional[PizzaSize] = None

    @dispatch(PizzaCreatedEvent)
    def on(self, event: PizzaCreatedEvent) -> None:
        self.id = event.aggregate_id
        self.name = event.name
        self.base_price = event.base_price
        self.size = PizzaSize(event.size)

class Pizza(AggregateRoot[PizzaState, str]):
    def __init__(self, name: str, base_price: Decimal, size: PizzaSize):
        super().__init__()
        self.state.on(
            self.register_event(
                PizzaCreatedEvent(str(uuid4()), name, size.value, base_price)
            )
        )
```

### Key Changes

1. Import from `neuroglia.data.abstractions`
2. Add second type parameter (TKey) - usually `str`
3. Use `register_event()` instead of `raise_event()`
4. Add `@dispatch` event handlers to state
5. Use `self.state.on()` to apply events
6. Use `self.id()` method not property
7. Keep state and aggregate in same file

````

## Type Checker Notes

### Expected Warnings (Safe to Ignore)

When using multipledispatch with type checkers (Pylance/Pyright):

1. **"Method declaration 'on' is obscured by a declaration of the same name"**
   - This is expected - multipledispatch creates multiple methods with same name
   - Runtime dispatch works correctly

2. **"Argument of type 'Event1' cannot be assigned to parameter of type 'Event2'"**
   - Type checker sees first @dispatch signature only
   - Runtime dispatch routes to correct handler

### Solution

Add type: ignore comments where needed:

```python
self.state.on(  # type: ignore[arg-type]
    self.register_event(PizzaCreatedEvent(...))
)
````

Or configure Pylance to allow multipledispatch patterns.

## Dependency Changes

### pyproject.toml

Added to core dependencies:

```toml
multipledispatch = "^1.0.0"
```

This is now a **required** dependency for the framework as it's used in the recommended aggregate pattern.

## Testing Implications

### State Handler Testing

Can now test event handlers independently:

```python
def test_pizza_state_handles_created_event():
    state = PizzaState()
    event = PizzaCreatedEvent(
        aggregate_id="test-id",
        name="Margherita",
        base_price=Decimal("12.99"),
        size="large"
    )

    state.on(event)

    assert state.id == "test-id"
    assert state.name == "Margherita"
    assert state.base_price == Decimal("12.99")
```

### Event Sourcing Tests

Can reconstruct state by replaying events:

```python
def test_pizza_state_reconstruction_from_events():
    state = PizzaState()

    events = [
        PizzaCreatedEvent(...),
        ToppingsUpdatedEvent(...),
        ToppingsUpdatedEvent(...),
    ]

    for event in events:
        state.on(event)

    # State should match final state from event stream
    assert state.toppings == ["cheese", "basil"]
```

## Refactoring Checklist

For each aggregate being refactored:

- [ ] Move state class into same file as aggregate
- [ ] Add `@dispatch` decorators to state event handlers
- [ ] Change aggregate to use `AggregateRoot[TState, str]`
- [ ] Replace `self.raise_event()` with `self.register_event()`
- [ ] Wrap event registration with `self.state.on()`
- [ ] Update all `self.id` to `self.id()`
- [ ] Ensure events contain all data needed for state mutation
- [ ] Update tests to use `aggregate.id()` method
- [ ] Add state handler unit tests
- [ ] Verify serialization works correctly

## Sample Status

### Completed

- ✅ **OpenBank** - Already using correct pattern
- ✅ **Mario's Pizzeria - Pizza** - Refactored to new pattern

### In Progress

- 🔄 **Mario's Pizzeria - Customer** - Next
- ⏳ **Mario's Pizzeria - Order** - Pending
- ⏳ **Mario's Pizzeria - Kitchen** - Pending

### To Review

- [ ] Other samples in /samples directory

## Breaking Changes

### For Existing Users

1. **Custom AggregateRoot removed** - Must migrate to Neuroglia's
2. **`raise_event()` method** - Use `register_event()` instead
3. **`id` property** - Now `id()` method in Neuroglia's implementation
4. **Type parameters** - Must specify both TState and TKey

### Migration Path

1. Install `multipledispatch` dependency
2. Add `@dispatch` handlers to state classes
3. Change aggregate base class
4. Update event registration pattern
5. Update id access from property to method
6. Run tests to verify

## Questions/Decisions

### Q: Should register_event() auto-apply to state?

**Decision**: No - keep explicit `self.state.on()` call

**Reasoning**:

- More explicit and easier to understand
- Clear flow: register then apply
- Matches OpenBank pattern
- Avoids "magic" behavior

### Q: State and Aggregate in same file?

**Decision**: Yes - keep together

**Reasoning**:

- Easier to understand relationship
- Reduced imports
- Similar to OpenBank BankAccount example
- State is tightly coupled to aggregate

### Q: What about event versioning?

**Decision**: Support multiple event versions via @dispatch

**Example**:

```python
@dispatch(CustomerCreatedEventV1)
def on(self, event: CustomerCreatedEventV1) -> None:
    # Handle V1 event

@dispatch(CustomerCreatedEventV2)
def on(self, event: CustomerCreatedEventV2) -> None:
    # Handle V2 event with new fields
```

---

**Last Updated**: 2025-10-07
**Status**: In Progress - Customer aggregate refactoring
**Owner**: bvandewe
