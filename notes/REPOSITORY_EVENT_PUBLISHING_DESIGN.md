# Repository-Based Domain Event Publishing - Design Document

**Date**: November 1, 2025
**Status**: Approved for Implementation
**Author**: Architecture Review

## Executive Summary

Migrating from UnitOfWork pattern to Repository-based automatic domain event publishing to simplify the framework and reduce developer cognitive load while maintaining DDD principles.

## Problem Statement

### Current Issues with UnitOfWork Pattern

1. **Manual Registration is Error-Prone**

   ```python
   # Handler code - EASY TO FORGET!
   order = Order.create(...)
   await self.order_repository.add_async(order)
   self.unit_of_work.register_aggregate(order)  # ← Developer must remember this!
   ```

   - Risk: Forgetting `register_aggregate()` = events never dispatched = silent failure
   - Impact: 12+ command handlers in mario-pizzeria all require this manual step
   - Testing: Hard to catch in unit tests if mock doesn't verify registration

2. **UnitOfWork is a Middleman with Little Value**

   - Purpose: Collect aggregates → extract events → hand to middleware
   - Reality: Just a collection holder (`set[AggregateRoot]`)
   - Question: Why not have Repository collect events directly?

3. **Coupling to Middleware Pattern**

   - Events only dispatch if `DomainEventDispatchingMiddleware` is registered
   - Pattern works for Commands but awkward for direct repository usage
   - Forces all domain changes through command handlers

4. **Two Responsibilities Mixed**
   - Transaction coordination (should be database-specific)
   - Event collection (should be automatic)

## Proposed Solution

### Core Concept

Make **Repository responsible for publishing domain events** automatically after successful persistence.

### Implementation Pattern

```python
class Repository(Generic[TEntity, TKey], ABC):
    def __init__(self, mediator: Optional[Mediator] = None):
        self._mediator = mediator

    async def add_async(self, entity: TEntity) -> TEntity:
        # 1. Persist entity
        result = await self._do_add_async(entity)

        # 2. Automatically publish pending events
        await self._publish_domain_events(entity)

        return result

    async def _publish_domain_events(self, entity: TEntity) -> None:
        """Automatically publish pending domain events from aggregate."""
        if not self._mediator:
            return  # No mediator = no publishing (testing scenario)

        if not isinstance(entity, AggregateRoot):
            return  # Not an aggregate = no events

        events = entity.get_uncommitted_events()
        if not events:
            return

        for event in events:
            try:
                await self._mediator.publish_async(event)
            except Exception as e:
                log.error(f"Failed to publish {type(event).__name__}: {e}")

        entity.clear_pending_events()
```

### Handler Simplification

```python
# BEFORE
class PlaceOrderHandler(CommandHandler[...]):
    def __init__(self, repo: IOrderRepository,
                 unit_of_work: IUnitOfWork):
        self.repo = repo
        self.unit_of_work = unit_of_work

    async def handle_async(self, command: PlaceOrderCommand):
        order = Order.create(...)
        await self.repo.add_async(order)
        self.unit_of_work.register_aggregate(order)  # ← Remove this!
        return self.created(order_dto)

# AFTER
class PlaceOrderHandler(CommandHandler[...]):
    def __init__(self, repo: IOrderRepository):
        self.repo = repo

    async def handle_async(self, command: PlaceOrderCommand):
        order = Order.create(...)
        await self.repo.add_async(order)  # ← Events published automatically!
        return self.created(order_dto)
```

## Benefits

1. **Automatic Event Publishing**

   - ✅ Impossible to forget - happens in repository
   - ✅ Consistent behavior - all persistence operations handle events the same way
   - ✅ Less boilerplate - 12+ handlers in mario-pizzeria become simpler

2. **True Single Responsibility**

   - **Repository**: Persistence + Event publishing (cohesive)
   - **Aggregate**: Business logic + Event raising
   - **Handler**: Orchestration only

3. **Works Everywhere**

   ```python
   # In command handler
   await repo.add_async(order)  # ✅ Events published

   # In background service
   await repo.add_async(order)  # ✅ Events published

   # Direct usage (testing, scripts)
   await repo.add_async(order)  # ✅ Events published
   ```

4. **Eliminates UnitOfWork Complexity**
   - No manual registration
   - No middleware dependency
   - No request-scoped tracking
   - No clear() management

## Multi-Aggregate Consistency

### Key Question Addressed

**Q: What if multiple aggregates are modified in a single handler and one fails?**

### DDD Answer: Accept Eventual Consistency

According to DDD principles (Vaughn Vernon, Eric Evans):

> **"Aggregate boundaries are transaction boundaries"**

This means:

- **Single Aggregate = Single Transaction** ✅ Strong consistency
- **Multiple Aggregates = Eventual Consistency** ⚠️ Accept it!

### Why This Approach is Correct

1. **Design Smell**: Needing to modify multiple aggregates atomically often indicates:

   - Wrong aggregate boundaries
   - Missing domain concepts
   - Business rules in the wrong place

2. **Reality of Distributed Systems**:

   - True ACID transactions across aggregates don't scale
   - Even with database transactions, network failures can break consistency
   - Eventual consistency is the norm in real systems

3. **Business Perspective**:
   - In mario-pizzeria: order is placed (critical), customer info updated (nice to have)
   - If customer update fails, it's an edge case, not a system failure

### UnitOfWork Does NOT Solve This

The current UnitOfWork implementation **does NOT provide transactional consistency**:

```python
class UnitOfWork:
    def __init__(self):
        self._aggregates: set[AggregateRoot] = set()  # Just a collection!

    def register_aggregate(self, aggregate):
        self._aggregates.add(aggregate)  # No transaction coordination!
```

**What it does**: Collect aggregates for event dispatching
**What it does NOT do**: Coordinate database transactions

### Recommended Pattern for Multi-Aggregate Scenarios

```python
class PlaceOrderHandler:
    async def handle_async(self, command: PlaceOrderCommand):
        # Primary aggregate (critical path)
        order = Order.create(...)
        await self.order_repository.add_async(order)
        # ✅ Order saved + OrderPlacedEvent published

        # Secondary aggregate (eventual consistency)
        try:
            customer = await self._update_customer_info(command)
            # ✅ Customer updated + CustomerUpdatedEvent published (if any)
        except Exception as e:
            log.warning(f"Customer update failed, order still placed: {e}")
            # ⚠️ Order is already saved! This is OK from business perspective

        return self.created(order_dto)
```

**Better Pattern with Event Handlers**:

```python
class PlaceOrderHandler:
    async def handle_async(self, command: PlaceOrderCommand):
        order = Order.create(command.customer_phone, ...)
        await self.order_repository.add_async(order)
        # Events: OrderPlacedEvent published automatically
        return self.created(order_dto)

class OrderPlacedEventHandler:
    async def handle_async(self, event: OrderPlacedEvent):
        # Update customer asynchronously with retry
        for attempt in range(3):
            try:
                customer = await self._get_or_create_customer(event)
                customer.record_order(event.order_id)
                await self.customer_repository.update_async(customer)
                break
            except Exception as e:
                if attempt == 2:
                    log.error(f"Failed to update customer after 3 attempts: {e}")
```

## Design Considerations

### 1. Transaction Boundaries

Keep transactions at the repository implementation level:

```python
class MotorRepository(Repository[TEntity, TKey]):
    async def _do_add_async(self, entity: TEntity) -> TEntity:
        async with await self._client.start_session() as session:
            async with session.start_transaction():
                # Persist entity
                # Events published AFTER transaction commits (by base class)
```

**Key**: Events are published **after** successful persistence, maintaining consistency.

### 2. Event Publishing Failures

Make it configurable:

```python
class EventPublishingMode(Enum):
    BEST_EFFORT = "best_effort"  # Log errors, continue
    STRICT = "strict"              # Raise exception on failure
    NONE = "none"                  # Skip publishing (testing)

class RepositoryOptions:
    event_publishing_mode: EventPublishingMode = EventPublishingMode.BEST_EFFORT
```

### 3. Testing

Pass `mediator=None` to disable event publishing:

```python
def test_add_order():
    # No events published during test
    repo = MongoOrderRepository(client, serializer, mediator=None)
    order = Order.create(...)
    await repo.add_async(order)

    # Assert on pending events instead
    assert len(order.get_uncommitted_events()) == 1
```

### 4. Migration Path

1. **Add mediator parameter** to Repository constructors (optional, defaults to None)
2. **Keep UnitOfWork working** alongside new pattern
3. **Deprecate** UnitOfWork with clear migration guide
4. **Update documentation** with new pattern
5. **Remove** UnitOfWork in next major version

## Implementation Plan

### Phase 1: Extend Base Repository ✅

**File**: `src/neuroglia/data/infrastructure/abstractions.py`

1. Add optional `mediator` parameter to `Repository.__init__()`
2. Implement `_publish_domain_events()` method
3. Update `add_async()`, `update_async()` to call event publishing
4. Add protected abstract methods: `_do_add_async()`, `_do_update_async()`, `_do_remove_async()`

### Phase 2: Update Concrete Repositories ✅

**Files**:

- `src/neuroglia/data/infrastructure/mongo/motor_repository.py`
- `src/neuroglia/data/infrastructure/mongo/mongo_repository.py`
- `src/neuroglia/data/infrastructure/memory/memory_repository.py`
- `src/neuroglia/data/infrastructure/filesystem/filesystem_repository.py`

1. Add `mediator` parameter to constructors
2. Pass mediator to base class
3. Rename existing methods to `_do_*` pattern

### Phase 3: Update Mario-Pizzeria Repositories

**Files**: `samples/mario-pizzeria/integration/repositories/*.py`

1. Add mediator parameter to repository constructors
2. Update dependency injection in `main.py`

### Phase 4: Simplify Command Handlers

**Files**: `samples/mario-pizzeria/application/commands/*.py`

1. Remove `IUnitOfWork` from constructor dependencies
2. Remove `unit_of_work.register_aggregate()` calls
3. Keep repository operations only

### Phase 5: Deprecate UnitOfWork

**Files**:

- `src/neuroglia/data/unit_of_work.py`
- `src/neuroglia/mediation/behaviors/domain_event_dispatching_middleware.py`

1. Add `@deprecated` decorators with migration guidance
2. Update docstrings with deprecation notices
3. Keep implementations working for backward compatibility

### Phase 6: Update Tests

**Files**: `tests/**/*.py`

1. Update repository tests to include mediator parameter
2. Add tests for automatic event publishing
3. Update handler tests to remove UnitOfWork mocks
4. Add integration tests for event flow

### Phase 7: Documentation Updates

**Files**:

- `docs/patterns/unit-of-work.md` → Add deprecation notice
- `docs/patterns/repository.md` → Document new event publishing
- `docs/tutorials/mario-pizzeria-05-events.md` → Update event patterns
- `docs/tutorials/mario-pizzeria-06-persistence.md` → Remove UnitOfWork

## Impact Analysis

| Component            | Files                                      | Effort |
| -------------------- | ------------------------------------------ | ------ |
| **Core Repository**  | `abstractions.py`                          | Medium |
| **Concrete Repos**   | `MotorRepository`, `MongoRepository`, etc. | Low    |
| **Command Handlers** | 12+ handlers in mario-pizzeria             | Low    |
| **Registration**     | `main.py` service registration             | Low    |
| **Tests**            | Repository tests, handler tests            | Medium |
| **Documentation**    | Patterns, tutorials                        | Medium |

**Total Effort**: ~3-4 days for complete implementation and testing

## Success Criteria

1. ✅ All repositories support optional mediator injection
2. ✅ Domain events automatically published after persistence
3. ✅ All mario-pizzeria handlers simplified (no UnitOfWork)
4. ✅ All tests passing with new pattern
5. ✅ UnitOfWork marked as deprecated but still functional
6. ✅ Documentation updated with migration guide
7. ✅ No breaking changes for existing applications

## Risks and Mitigations

| Risk                       | Mitigation                                               |
| -------------------------- | -------------------------------------------------------- |
| Breaking changes for users | Keep UnitOfWork functional, provide migration guide      |
| Event publishing failures  | Implement configurable error handling modes              |
| Performance impact         | Events published in same async context, minimal overhead |
| Testing complexity         | Mediator=None for tests, clear testing patterns          |

## Conclusion

This refactoring:

- ✅ Simplifies the framework significantly
- ✅ Reduces cognitive load for developers
- ✅ Maintains DDD principles
- ✅ Provides better default behavior
- ✅ Keeps backward compatibility during migration

The UnitOfWork pattern added complexity without solving the real consistency challenges in distributed systems. Repository-based event publishing is the natural evolution that aligns with DDD aggregate boundaries and modern event-driven architecture.
