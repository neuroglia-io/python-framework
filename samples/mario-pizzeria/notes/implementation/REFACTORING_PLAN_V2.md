# Mario's Pizzeria - Refactoring Plan V2

## User Feedback & Improvements

### Issues with Current Implementation (V1)

1. ❌ **Using custom AggregateRoot** instead of Neuroglia's framework implementation
2. ❌ **Using `raise_event`** instead of more logical `register_event`
3. ❌ **State doesn't handle domain events** - missing state mutation logic through events

### Proposed Improvements (V2)

1. ✅ **Switch to Neuroglia's `AggregateRoot[TState, TKey]`**
2. ✅ **Use `register_event()` method** (already in framework)
3. ✅ **Implement state event handlers** with multidispatch pattern: `self.state.on(self.register_event(MyEvent()))`

---

## Architecture Pattern: State Event Handlers

### Concept

Instead of directly mutating state in aggregate methods, we use a pattern where:

1. **Aggregate registers events** that describe what happened
2. **State has event handlers** (using `@singledispatchmethod`) that apply the event
3. **State mutation is centralized** in the state's `on()` method

### Benefits

✅ **Single Source of Truth**: State mutation logic is in the state class
✅ **Event Replay**: Can reconstruct state by replaying events (event sourcing ready)
✅ **Testability**: State handlers can be tested independently
✅ **Clarity**: Clear separation between "what happened" (event) vs "how to apply it" (state handler)
✅ **Type Safety**: Multidispatch ensures correct handler is called for each event type

### Pattern Example

```python
from functools import singledispatchmethod
from dataclasses import dataclass
from neuroglia.data.abstractions import AggregateState, DomainEvent, AggregateRoot

# 1. Events describe what happened
@dataclass
class PizzaCreatedEvent(DomainEvent):
    name: str
    base_price: Decimal
    size: str

@dataclass
class ToppingAddedEvent(DomainEvent):
    topping: str

# 2. State has event handlers
@dataclass
class PizzaState(AggregateState[str]):
    name: Optional[str] = None
    base_price: Optional[Decimal] = None
    size: Optional[PizzaSize] = None
    toppings: list[str] = field(default_factory=list)

    @singledispatchmethod
    def on(self, event: DomainEvent) -> None:
        """Apply domain event to state (default handler)"""
        raise NotImplementedError(f"No handler for event type: {type(event).__name__}")

    @on.register
    def _(self, event: PizzaCreatedEvent) -> None:
        """Handle PizzaCreatedEvent"""
        self.name = event.name
        self.base_price = event.base_price
        self.size = PizzaSize(event.size)
        self.toppings = []

    @on.register
    def _(self, event: ToppingAddedEvent) -> None:
        """Handle ToppingAddedEvent"""
        if event.topping not in self.toppings:
            self.toppings.append(event.topping)

# 3. Aggregate uses state event handlers
class Pizza(AggregateRoot[PizzaState, str]):
    def __init__(self, name: str, base_price: Decimal, size: PizzaSize):
        super().__init__()

        # Register event and apply it to state in one line
        self.state.on(self.register_event(PizzaCreatedEvent(
            aggregate_id=self.id,
            name=name,
            base_price=base_price,
            size=size.value
        )))

    def add_topping(self, topping: str) -> None:
        """Add topping through event"""
        self.state.on(self.register_event(ToppingAddedEvent(
            aggregate_id=self.id,
            topping=topping
        )))
```

### Flow

1. Aggregate method is called: `pizza.add_topping("extra cheese")`
2. Event is created and registered: `self.register_event(ToppingAddedEvent(...))`
3. Registered event is applied to state: `self.state.on(event)`
4. State handler mutates state: `self.toppings.append(event.topping)`
5. Event is collected by UnitOfWork for dispatching

---

## Refactoring Steps

### Step 1: Update Base Classes

#### Remove Custom AggregateRoot

- Delete `domain/aggregate_root.py`
- Import directly from `neuroglia.data.abstractions`

#### Update Imports

```python
# Before
from ..aggregate_root import AggregateRoot

# After
from neuroglia.data.abstractions import AggregateRoot
```

### Step 2: Add Event Handlers to PizzaState

```python
from functools import singledispatchmethod
from neuroglia.data.abstractions import AggregateState, DomainEvent

@dataclass
class PizzaState(AggregateState[str]):
    # ... fields ...

    @singledispatchmethod
    def on(self, event: DomainEvent) -> None:
        """Apply domain event to mutate state"""
        # Default: do nothing for unknown events
        pass

    @on.register
    def _(self, event: PizzaCreatedEvent) -> None:
        self.name = event.name
        self.base_price = event.base_price
        self.size = PizzaSize(event.size)
        self.description = event.description or ""
        self.toppings = []

    @on.register
    def _(self, event: ToppingsUpdatedEvent) -> None:
        self.toppings = event.toppings.copy()
```

### Step 3: Update Pizza Aggregate

```python
from neuroglia.data.abstractions import AggregateRoot

class Pizza(AggregateRoot[PizzaState, str]):
    def __init__(self, name: str, base_price: Decimal, size: PizzaSize, description: Optional[str] = None):
        super().__init__()

        # Register event and apply to state
        self.state.on(self.register_event(PizzaCreatedEvent(
            aggregate_id=self.id,
            name=name,
            base_price=base_price,
            size=size.value,
            description=description,
            toppings=[]
        )))

    def add_topping(self, topping: str) -> None:
        """Add topping via event"""
        new_toppings = self.state.toppings.copy()
        new_toppings.append(topping)

        self.state.on(self.register_event(ToppingsUpdatedEvent(
            aggregate_id=self.id,
            toppings=new_toppings
        )))

    def remove_topping(self, topping: str) -> None:
        """Remove topping via event"""
        new_toppings = [t for t in self.state.toppings if t != topping]

        self.state.on(self.register_event(ToppingsUpdatedEvent(
            aggregate_id=self.id,
            toppings=new_toppings
        )))
```

### Step 4: Update Events

Ensure events have all data needed for state mutation:

```python
@dataclass
class PizzaCreatedEvent(DomainEvent):
    name: str
    base_price: Decimal
    size: str
    description: str
    toppings: list[str]

@dataclass
class ToppingsUpdatedEvent(DomainEvent):
    toppings: list[str]
```

---

## Migration Checklist

### Phase 1: Pizza Aggregate (Current)

- [ ] Remove custom `domain/aggregate_root.py`
- [ ] Import Neuroglia's `AggregateRoot[TState, TKey]`
- [ ] Add `@singledispatchmethod on()` to `PizzaState`
- [ ] Implement event handlers in `PizzaState.on()`
- [ ] Update `Pizza` to use `register_event` instead of `raise_event`
- [ ] Update `Pizza` methods to use `self.state.on(self.register_event(...))`
- [ ] Update tests to verify event handlers work
- [ ] Update tests to use `register_event` naming

### Phase 2: Remaining Aggregates

- [ ] Customer aggregate
- [ ] Order aggregate
- [ ] Kitchen aggregate

### Phase 3: Handlers & Tests

- [ ] Update command handlers
- [ ] Update integration tests
- [ ] Verify UnitOfWork collects events correctly

---

## Key Design Decisions

### Why `self.state.on(self.register_event(...))`?

1. **Event is registered first**: `self.register_event(event)` adds to `_pending_events`
2. **Then applied to state**: `self.state.on(event)` mutates state
3. **Returns event**: Can chain or capture event if needed
4. **Explicit flow**: Clear that event causes state change

### Alternative: `register_event` could call `state.on()` internally

```python
# In Neuroglia's AggregateRoot
def register_event(self, e: TEvent) -> TEvent:
    if not hasattr(self, "_pending_events"):
        self._pending_events = list[DomainEvent]()
    self._pending_events.append(e)
    e.aggregate_version = self.state.state_version + len(self._pending_events)

    # Apply event to state if state has `on` method
    if hasattr(self.state, 'on'):
        self.state.on(e)

    return e
```

Then aggregate code becomes:

```python
self.register_event(PizzaCreatedEvent(...))  # Automatically applies to state
```

**Trade-offs**:

- ✅ More concise
- ✅ Less repetition
- ❌ Less explicit
- ❌ Magic behavior in framework
- ❌ Harder to understand flow

**Recommendation**: Use explicit `self.state.on(self.register_event(...))` for clarity, unless framework wants to adopt automatic application.

---

## Testing Strategy

### Unit Tests for State Event Handlers

```python
def test_pizza_state_handles_created_event():
    state = PizzaState()
    event = PizzaCreatedEvent(
        aggregate_id="test-id",
        name="Margherita",
        base_price=Decimal("12.99"),
        size="large",
        description="Classic",
        toppings=[]
    )

    state.on(event)

    assert state.name == "Margherita"
    assert state.base_price == Decimal("12.99")
    assert state.size == PizzaSize.LARGE
    assert state.toppings == []

def test_pizza_state_handles_toppings_updated():
    state = PizzaState()
    # ... initialize state ...

    event = ToppingsUpdatedEvent(
        aggregate_id="test-id",
        toppings=["cheese", "basil"]
    )

    state.on(event)

    assert state.toppings == ["cheese", "basil"]
```

### Integration Tests for Aggregate

```python
def test_pizza_aggregate_creates_and_applies_event():
    pizza = Pizza(
        name="Margherita",
        base_price=Decimal("12.99"),
        size=PizzaSize.LARGE
    )

    # Verify state was mutated
    assert pizza.state.name == "Margherita"

    # Verify event was registered
    events = pizza.domain_events
    assert len(events) == 1
    assert isinstance(events[0], PizzaCreatedEvent)
```

---

## Questions for Discussion

1. **Should `register_event()` auto-apply events?** Or keep explicit `self.state.on()`?
2. **Should all aggregates use this pattern?** Or only event-sourced ones?
3. **How to handle validation?** Before or after event registration?
4. **Event handler errors?** Should `state.on()` raise or log?

---

**Status**: Ready to implement V2 refactoring
**Next Step**: Implement Pizza aggregate with new pattern
