# Mario's Pizzeria - Upgrade Notes for Neuroglia v0.4.6

**Date**: October 19, 2025
**Framework Version**: neuroglia-python v0.4.6
**Sample App Status**: ✅ **Compatible - No Changes Required**

## Summary

The Mario's Pizzeria sample application is **fully compatible** with Neuroglia v0.4.6 without requiring any code changes. The app was already following best practices that align with the new scoped service resolution improvements.

## What Changed in v0.4.6

### Critical Framework Fixes

1. **Transient Service Resolution in Scoped Contexts**

   - Transient services (like notification handlers) can now properly access scoped dependencies
   - `ServiceScope.get_services()` now builds transient services within scope context
   - Enables event-driven architecture with scoped repositories

2. **Async Scope Disposal**

   - Added `ServiceScope.dispose_async()` for proper async resource cleanup
   - Automatic disposal of scoped services after event processing
   - Proper cleanup even in error scenarios

3. **Mediator Scoped Event Processing**
   - `Mediator.publish_async()` now creates isolated async scope per notification
   - All notification handlers execute within same scope
   - Scoped services (repositories, UnitOfWork) shared across handlers for same event

## Why Mario's Pizzeria Already Works

### ✅ Correct Service Registrations

The app already uses appropriate service lifetimes:

```python
# main.py - Already correct!

# Scoped repositories (one instance per request)
builder.services.add_scoped(
    IPizzaRepository,
    implementation_factory=lambda _: FilePizzaRepository(data_dir_str),
)
builder.services.add_scoped(
    ICustomerRepository,
    implementation_factory=lambda _: FileCustomerRepository(data_dir_str),
)
builder.services.add_scoped(
    IOrderRepository,
    implementation_factory=lambda _: FileOrderRepository(data_dir_str),
)

# Scoped UnitOfWork (one instance per request)
builder.services.add_scoped(
    IUnitOfWork,
    implementation_factory=lambda _: UnitOfWork(),
)

# Singleton services (one instance for app lifetime)
builder.services.add_singleton(Mediator, Mediator)
builder.services.add_singleton(Mapper)
```

### ✅ Correct Handler Dependencies

Command and query handlers already use scoped dependencies properly:

```python
# application/commands/place_order_command.py - Already correct!

class PlaceOrderCommandHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    """Handler for placing new pizza orders"""

    def __init__(
        self,
        order_repository: IOrderRepository,      # Scoped - one per request
        customer_repository: ICustomerRepository,  # Scoped - one per request
        mapper: Mapper,                           # Singleton - shared
        unit_of_work: IUnitOfWork,               # Scoped - one per request
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper
        self.unit_of_work = unit_of_work
```

### ✅ Correct Event Handler Pattern

Domain event handlers don't depend on scoped services:

```python
# application/event_handlers.py - Already correct!

class OrderConfirmedEventHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Handles order confirmation events"""

    async def handle_async(self, event: OrderConfirmedEvent) -> Any:
        """Process order confirmed event"""
        logger.info(f"🍕 Order {event.aggregate_id} confirmed!")
        # Event handlers are stateless - no repository dependencies
        return None
```

**Why this works**: Domain event handlers in Mario's Pizzeria are used for side effects like logging and notifications, not for data access. If you needed to access repositories in event handlers, you would register them as transient handlers with scoped dependencies (which now works in v0.4.6!).

## Service Lifetime Decision Guide

When adding new services to Mario's Pizzeria, follow these guidelines:

### Use **Singleton** for:

- ✅ `Mediator` - One command/event dispatcher for entire app
- ✅ `Mapper` - One object mapper for entire app
- ✅ Configuration objects - Shared app configuration
- ✅ Caching services - Shared cache across all requests

### Use **Scoped** for:

- ✅ Repositories (`IOrderRepository`, `ICustomerRepository`, etc.)
- ✅ `IUnitOfWork` - Tracks domain events per request
- ✅ Database contexts - One per request
- ✅ Services with request-specific state

### Use **Transient** for:

- ✅ Command/Query handlers - New instance per command
- ✅ Validators - Stateless validation logic
- ✅ Calculators - Stateless computation services
- ✅ Event handlers with scoped dependencies (NEW in v0.4.6!)

## Example: Adding Event Handler with Repository Access (NEW in v0.4.6)

If you wanted to add an event handler that accesses repositories, here's the pattern:

```python
# application/event_handlers.py - NEW PATTERN

class OrderConfirmedWithRepositoryHandler(NotificationHandler[OrderConfirmedEvent]):
    """
    Example: Event handler that needs repository access.
    Now works correctly with v0.4.6!
    """

    def __init__(
        self,
        order_repository: IOrderRepository,  # Scoped dependency
        customer_repository: ICustomerRepository,  # Scoped dependency
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository

    async def handle_async(self, notification: OrderConfirmedEvent) -> Any:
        """Process order confirmed event with repository access"""
        # Can now access scoped repositories!
        order = await self.order_repository.get_by_id_async(notification.aggregate_id)
        customer = await self.customer_repository.get_by_id_async(order.customer_id)

        # Update read model, send notification, etc.
        logger.info(f"Order {order.id()} for customer {customer.name} confirmed!")
        return None
```

**How to register** (already automatic via Mediator.configure):

```python
# The handler is automatically discovered and registered as transient
Mediator.configure(builder, ["application.event_handlers"])
```

**What happens when event fires**:

1. Mediator creates async scope
2. Handler resolved from scoped provider (can access scoped repos)
3. Handler executes with scoped dependencies
4. Scope automatically disposed (repos cleaned up)

## Testing Recommendations

### Existing Tests Still Work ✅

All existing tests in `tests/test_integration.py` continue to work because:

- Each test gets its own `test_data_dir` fixture
- Each test creates a fresh app with `create_pizzeria_app(data_dir=test_data_dir)`
- Repository scoping ensures test isolation

### Testing Event Handlers with Scoped Dependencies (NEW)

If you add event handlers with repository dependencies:

```python
# tests/test_event_handler_with_repos.py - NEW PATTERN

@pytest.mark.asyncio
async def test_event_handler_accesses_repository(test_app):
    """Test that event handlers can access scoped repositories"""
    # Get services from app
    services = test_app.state.services
    mediator = services.get_service(Mediator)

    # Create test event
    event = OrderConfirmedEvent(aggregate_id="test-order-123", ...)

    # Publish event - handler gets scoped repositories automatically
    await mediator.publish_async(event)

    # Verify handler accessed repository correctly
    # (would need to check side effects or use mock repositories)
```

## Performance Improvements

The v0.4.6 fixes improve performance for event-driven scenarios:

1. **Scoped Repository Sharing**

   - Multiple handlers for same event share repository instances
   - Reduces memory allocations
   - Improves cache hit rates

2. **Automatic Resource Cleanup**

   - `dispose_async()` ensures proper cleanup
   - Prevents memory leaks in long-running services
   - File handles, connections properly closed

3. **Isolated Event Processing**
   - Each event processed in isolated scope
   - No cross-contamination between events
   - Thread-safe event processing

## Migration Checklist

Even though no changes are required, verify your app follows best practices:

- [ ] ✅ Repositories registered as **scoped**
- [ ] ✅ UnitOfWork registered as **scoped**
- [ ] ✅ Mediator registered as **singleton**
- [ ] ✅ Mapper registered as **singleton**
- [ ] ✅ Command/Query handlers use constructor injection
- [ ] ✅ Event handlers are stateless OR use constructor injection for dependencies
- [ ] ✅ No manual service resolution in handlers (use constructor injection)
- [ ] ✅ Tests use isolated data directories per test

**Mario's Pizzeria Status**: ✅ All best practices already followed!

## Conclusion

The Mario's Pizzeria sample app is a **reference implementation** of Neuroglia best practices and requires **no changes** for v0.4.6. The app already demonstrates:

- ✅ Proper service lifetime management
- ✅ Clean architecture with dependency injection
- ✅ Event-driven architecture with domain events
- ✅ CQRS pattern with mediator
- ✅ Repository pattern with scoped lifetimes
- ✅ Unit of Work pattern for transaction management

The v0.4.6 improvements enhance the framework's capabilities while maintaining backward compatibility with well-structured applications like Mario's Pizzeria.

## Next Steps

1. **Update dependencies**: `pip install neuroglia-python==0.4.6`
2. **Run existing tests**: All should pass without modification
3. **Optional**: Add event handlers with repository access to demonstrate new v0.4.6 capabilities
4. **Optional**: Add integration tests for event-driven scenarios

## Additional Resources

- [Framework CHANGELOG](../../CHANGELOG.md) - Complete v0.4.6 changes
- [Scoped Service Tests](../../tests/cases/test_mediator_scoped_notification_handlers.py) - Test examples
- [Dependency Injection Guide](../../docs/features/dependency-injection.md) - Service lifetime patterns
- [CQRS Documentation](../../docs/features/simple-cqrs.md) - Mediator and handler patterns
