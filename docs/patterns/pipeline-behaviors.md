# 🔧 Pipeline Behaviors

_Estimated reading time: 20 minutes_

Pipeline behaviors provide a powerful way to implement cross-cutting concerns in the Neuroglia mediation pipeline. They enable you to add functionality like validation, logging, caching, transactions, and domain event dispatching around command and query execution.

## 💡 What & Why

### ❌ The Problem: Cross-Cutting Concerns Scattered Across Handlers

When cross-cutting concerns are implemented in every handler, code becomes duplicated and inconsistent:

```python
# ❌ PROBLEM: Logging, validation, and error handling duplicated in every handler
class CreateOrderHandler(CommandHandler[CreateOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: CreateOrderCommand):
        # Logging duplicated in EVERY handler
        self.logger.info(f"Creating order for customer {command.customer_id}")
        start_time = time.time()

        try:
            # Validation duplicated in EVERY handler
            if not command.customer_id:
                return self.validation_error("Customer ID required")
            if not command.items:
                return self.validation_error("At least one item required")

            # Business logic (the ONLY thing that should be here!)
            order = Order.create(command.customer_id, command.items)
            await self.repository.save_async(order)

            # Logging duplicated in EVERY handler
            duration = time.time() - start_time
            self.logger.info(f"Order created in {duration:.2f}s")

            return self.created(order)

        except Exception as ex:
            # Error handling duplicated in EVERY handler
            self.logger.error(f"Failed to create order: {ex}")
            return self.internal_server_error("Failed to create order")

class ConfirmOrderHandler(CommandHandler[ConfirmOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: ConfirmOrderCommand):
        # SAME logging code copy-pasted!
        self.logger.info(f"Confirming order {command.order_id}")
        start_time = time.time()

        try:
            # SAME validation code copy-pasted!
            if not command.order_id:
                return self.validation_error("Order ID required")

            # Business logic
            order = await self.repository.get_by_id_async(command.order_id)
            order.confirm()
            await self.repository.save_async(order)

            # SAME logging code copy-pasted!
            duration = time.time() - start_time
            self.logger.info(f"Order confirmed in {duration:.2f}s")

            return self.ok(order)

        except Exception as ex:
            # SAME error handling copy-pasted!
            self.logger.error(f"Failed to confirm order: {ex}")
            return self.internal_server_error("Failed to confirm order")

# Problems:
# ❌ Logging code duplicated in 50+ handlers
# ❌ Validation logic scattered everywhere
# ❌ Error handling inconsistent across handlers
# ❌ Hard to change logging format or validation rules
# ❌ Handlers doing TOO MUCH (violates Single Responsibility)
# ❌ Difficult to add new cross-cutting concerns
```

**Problems with Scattered Cross-Cutting Concerns:**

- ❌ **Code Duplication**: Same logging/validation/error handling code in every handler
- ❌ **Inconsistency**: Each handler implements concerns slightly differently
- ❌ **Violates SRP**: Handlers mix business logic with infrastructure concerns
- ❌ **Hard to Change**: Updating logging format requires changing 50+ handlers
- ❌ **Difficult to Test**: Must test logging/validation in every handler
- ❌ **Hard to Add Concerns**: Adding caching requires modifying all handlers

### ✅ The Solution: Pipeline Behaviors for Centralized Cross-Cutting Concerns

Pipeline behaviors wrap handlers to provide cross-cutting functionality in one place:

```python
# ✅ SOLUTION: Pipeline behaviors centralize cross-cutting concerns
from neuroglia.mediation.pipeline_behavior import PipelineBehavior

# Logging Behavior - ONE place for all logging!
class LoggingBehavior(PipelineBehavior[Any, Any]):
    def __init__(self, logger: ILogger):
        self.logger = logger

    async def handle_async(self, request, next_handler):
        request_name = type(request).__name__
        self.logger.info(f"Executing {request_name}")
        start_time = time.time()

        try:
            result = await next_handler()  # Execute handler

            duration = time.time() - start_time
            self.logger.info(f"Completed {request_name} in {duration:.2f}s")
            return result

        except Exception as ex:
            self.logger.error(f"Failed {request_name}: {ex}")
            raise

# Validation Behavior - ONE place for all validation!
class ValidationBehavior(PipelineBehavior[Command, OperationResult]):
    async def handle_async(self, request, next_handler):
        # Validate request (using validator for this command type)
        validator = self._get_validator(type(request))
        if validator:
            validation_result = await validator.validate_async(request)
            if not validation_result.is_valid:
                return OperationResult.validation_error(validation_result.errors)

        # Continue if valid
        return await next_handler()

# Error Handling Behavior - ONE place for all error handling!
class ErrorHandlingBehavior(PipelineBehavior[Any, OperationResult]):
    async def handle_async(self, request, next_handler):
        try:
            return await next_handler()
        except ValidationException as ex:
            return OperationResult.validation_error(ex.message)
        except NotFoundException as ex:
            return OperationResult.not_found(ex.message)
        except Exception as ex:
            self.logger.exception(f"Unhandled error: {ex}")
            return OperationResult.internal_error("An unexpected error occurred")

# Now handlers are CLEAN and focused!
class CreateOrderHandler(CommandHandler[CreateOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: CreateOrderCommand):
        # ONLY business logic - no logging, validation, or error handling!
        order = Order.create(command.customer_id, command.items)
        await self.repository.save_async(order)
        return self.created(order)

class ConfirmOrderHandler(CommandHandler[ConfirmOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: ConfirmOrderCommand):
        # ONLY business logic!
        order = await self.repository.get_by_id_async(command.order_id)
        order.confirm()
        await self.repository.save_async(order)
        return self.ok(order)

# Register pipeline behaviors once
services = ServiceCollection()
services.add_scoped(PipelineBehavior, LoggingBehavior)
services.add_scoped(PipelineBehavior, ValidationBehavior)
services.add_scoped(PipelineBehavior, ErrorHandlingBehavior)

# Pipeline wraps EVERY handler automatically:
# Request → LoggingBehavior → ValidationBehavior → ErrorHandlingBehavior → Handler
```

**Benefits of Pipeline Behaviors:**

- ✅ **No Duplication**: Cross-cutting concerns in one place
- ✅ **Consistency**: All handlers get same logging/validation/error handling
- ✅ **Single Responsibility**: Handlers focus only on business logic
- ✅ **Easy to Change**: Update logging format in one behavior
- ✅ **Easy to Test**: Test behaviors once, not in every handler
- ✅ **Composable**: Chain multiple behaviors together
- ✅ **Easy to Add Concerns**: Add caching by adding one behavior

## 🎯 Overview

Pipeline behaviors implement the decorator pattern, wrapping around command and query handlers to provide additional functionality without modifying the core business logic.

### Key Benefits

- **🔄 Cross-Cutting Concerns**: Implement validation, logging, caching consistently
- **📦 Composable**: Chain multiple behaviors together
- **🎯 Single Responsibility**: Keep handlers focused on business logic
- **🔧 Reusable**: Apply same behavior across multiple handlers
- **⚡ Performance**: Add caching, monitoring, optimization layers

## 🏗️ Basic Implementation

### Creating a Pipeline Behavior

```python
from neuroglia.mediation.pipeline_behavior import PipelineBehavior
from neuroglia.core import OperationResult

class LoggingBehavior(PipelineBehavior[Any, Any]):
    async def handle_async(self, request, next_handler):
        request_name = type(request).__name__

        # Pre-processing
        logger.info(f"Executing {request_name}")
        start_time = time.time()

        try:
            # Continue pipeline
            result = await next_handler()

            # Post-processing
            duration = time.time() - start_time
            logger.info(f"Completed {request_name} in {duration:.2f}s")

            return result

        except Exception as ex:
            logger.error(f"Failed {request_name}: {ex}")
            raise
```

### Registration

```python
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator
from neuroglia.mediation.pipeline_behavior import PipelineBehavior

builder = WebApplicationBuilder()
Mediator.configure(builder, ["application.commands", "application.queries"])
builder.services.add_scoped(PipelineBehavior, LoggingBehavior)
```

## 🚀 Common Patterns

### Validation Behavior

```python
class ValidationBehavior(PipelineBehavior[Command, OperationResult]):
    async def handle_async(self, request, next_handler):
        # Validate request
        validation_result = await self._validate_request(request)
        if not validation_result.is_valid:
            return OperationResult.validation_error(validation_result.errors)

        # Continue if valid
        return await next_handler()

    async def _validate_request(self, request):
        # Implement validation logic
        return ValidationResult(is_valid=True)
```

### Caching Behavior

```python
class CachingBehavior(PipelineBehavior[Query, Any]):
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service

    async def handle_async(self, request, next_handler):
        # Generate cache key
        cache_key = self._generate_cache_key(request)

        # Check cache first
        cached_result = await self.cache.get_async(cache_key)
        if cached_result:
            return cached_result

        # Execute query
        result = await next_handler()

        # Cache result
        await self.cache.set_async(cache_key, result, ttl=300)

        return result
```

### Performance Monitoring

```python
class PerformanceBehavior(PipelineBehavior[Any, Any]):
    async def handle_async(self, request, next_handler):
        request_name = type(request).__name__

        with self.metrics.timer(f"request.{request_name}.duration"):
            try:
                result = await next_handler()
                self.metrics.increment(f"request.{request_name}.success")
                return result

            except Exception:
                self.metrics.increment(f"request.{request_name}.error")
                raise
```

## 🔗 Behavior Chaining

Behaviors execute in registration order, forming a pipeline:

```python
# Registration order determines execution order
services.add_scoped(PipelineBehavior, ValidationBehavior)      # 1st
services.add_scoped(PipelineBehavior, CachingBehavior)         # 2nd
services.add_scoped(PipelineBehavior, PerformanceBehavior)     # 3rd
services.add_scoped(PipelineBehavior, LoggingBehavior)         # 4th

# Execution flow:
# ValidationBehavior -> CachingBehavior -> PerformanceBehavior -> LoggingBehavior -> Handler
```

### Conditional Behavior

```python
class ConditionalBehavior(PipelineBehavior[Command, OperationResult]):
    async def handle_async(self, request, next_handler):
        # Only apply to specific command types
        if isinstance(request, CriticalCommand):
            # Add extra processing for critical commands
            await self._notify_administrators(request)

        return await next_handler()
```

## 🧪 Testing Pipeline Behaviors

### Unit Testing

```python
@pytest.mark.asyncio
async def test_logging_behavior_logs_execution():
    behavior = LoggingBehavior()
    request = TestCommand("test")

    async def mock_next_handler():
        return OperationResult("OK", 200)

    result = await behavior.handle_async(request, mock_next_handler)

    assert result.status_code == 200
    # Verify logging occurred
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_full_pipeline_execution():
    # Setup complete pipeline
    builder = WebApplicationBuilder()
    Mediator.configure(builder, ["application.commands"])
    builder.services.add_scoped(PipelineBehavior, ValidationBehavior)
    builder.services.add_scoped(PipelineBehavior, LoggingBehavior)

    provider = builder.services.build_provider()
    mediator = provider.get_service(Mediator)

    # Execute through full pipeline
    command = CreateUserCommand("test@example.com")
    result = await mediator.execute_async(command)

    assert result.is_success
```

## 🔧 Advanced Scenarios

### Type-Specific Behaviors

```python
class CommandValidationBehavior(PipelineBehavior[Command, OperationResult]):
    """Only applies to commands, not queries"""

    async def handle_async(self, request: Command, next_handler):
        # Command-specific validation
        if not hasattr(request, 'user_id'):
            return self.bad_request("user_id is required for all commands")

        return await next_handler()

class QueryCachingBehavior(PipelineBehavior[Query, Any]):
    """Only applies to queries, not commands"""

    async def handle_async(self, request: Query, next_handler):
        # Query-specific caching logic
        return await self._cache_query_result(request, next_handler)
```

### Error Handling Behavior

```python
class ErrorHandlingBehavior(PipelineBehavior[Any, OperationResult]):
    async def handle_async(self, request, next_handler):
        try:
            return await next_handler()

        except ValidationException as ex:
            return OperationResult.validation_error(ex.message)

        except BusinessRuleException as ex:
            return OperationResult.business_error(ex.message)

        except Exception as ex:
            logger.exception(f"Unhandled error in {type(request).__name__}")
            return OperationResult.internal_error("An unexpected error occurred")
```

## ⚠️ Common Mistakes

### 1. **Modifying Request in Pipeline (Side Effects)**

```python
# ❌ WRONG: Modifying request object (side effects!)
class NormalizationBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        # Don't modify the request!
        request.email = request.email.lower().strip()
        return await next_handler()

# ✅ CORRECT: Handler normalizes data, or use separate validation step
class CreateUserHandler:
    async def handle_async(self, command: CreateUserCommand):
        # Normalize in handler
        email = command.email.lower().strip()
        user = User(email=email)
        return self.created(user)
```

### 2. **Forgetting to Call next_handler()**

```python
# ❌ WRONG: Not calling next_handler (pipeline stops!)
class BrokenBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        self.logger.info("Executing...")
        # FORGOT to call next_handler()!
        return None  # Handler never executes!

# ✅ CORRECT: Always call next_handler()
class WorkingBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        self.logger.info("Executing...")
        return await next_handler()  # Handler executes!
```

### 3. **Order-Dependent Behaviors Without Explicit Ordering**

```python
# ❌ WRONG: Assuming behavior order (undefined!)
services.add_scoped(PipelineBehavior, AuthenticationBehavior)
services.add_scoped(PipelineBehavior, AuthorizationBehavior)
# Order is NOT guaranteed! Authorization might run before authentication!

# ✅ CORRECT: Use explicit ordering or numbered behaviors
class AuthenticationBehavior(PipelineBehavior):
    order = 1  # Run first

class AuthorizationBehavior(PipelineBehavior):
    order = 2  # Run after authentication

# Or chain explicitly in one behavior
class SecurityBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        # Authenticate first
        user = await self.authenticate(request)
        if not user:
            return self.unauthorized()

        # Then authorize
        if not await self.authorize(user, request):
            return self.forbidden()

        return await next_handler()
```

### 4. **Expensive Operations in Every Request**

```python
# ❌ WRONG: Database queries in every pipeline invocation
class AuditBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        # Database query for EVERY request!
        audit_settings = await self.db.settings.find_one({"type": "audit"})

        if audit_settings["enabled"]:
            await self.log_audit(request)

        return await next_handler()

# ✅ CORRECT: Cache expensive lookups
class AuditBehavior(PipelineBehavior):
    def __init__(self, cache_service: ICacheService):
        self.cache = cache_service
        self._audit_enabled = None

    async def handle_async(self, request, next_handler):
        # Cache the setting
        if self._audit_enabled is None:
            settings = await self.db.settings.find_one({"type": "audit"})
            self._audit_enabled = settings["enabled"]

        if self._audit_enabled:
            await self.log_audit(request)

        return await next_handler()
```

### 5. **Catching All Exceptions Without Re-Raising**

```python
# ❌ WRONG: Swallowing exceptions (hides errors!)
class SilentErrorBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        try:
            return await next_handler()
        except Exception as ex:
            self.logger.error(f"Error: {ex}")
            return None  # Swallowed! Caller doesn't know about error!

# ✅ CORRECT: Handle specific exceptions or re-raise
class ErrorHandlingBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        try:
            return await next_handler()
        except ValidationException as ex:
            # Handle specific exception
            return OperationResult.validation_error(ex.message)
        except Exception as ex:
            # Log and re-raise unknown exceptions
            self.logger.exception(f"Unhandled error: {ex}")
            raise  # Re-raise so caller knows!
```

### 6. **Not Using Scoped Lifetime**

```python
# ❌ WRONG: Singleton lifetime (shared state across requests!)
services.add_singleton(PipelineBehavior, RequestContextBehavior)
# Same behavior instance for ALL requests - shared state!

# ✅ CORRECT: Scoped lifetime (one per request)
services.add_scoped(PipelineBehavior, RequestContextBehavior)
# Each request gets fresh behavior instance
```

## 🚫 When NOT to Use

### 1. **Business Logic (Belongs in Handlers)**

```python
# ❌ WRONG: Business logic in pipeline behavior
class InventoryCheckBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        if isinstance(request, CreateOrderCommand):
            # This is business logic, not cross-cutting!
            for item in request.items:
                if not await self.inventory.has_stock(item.product_id):
                    return OperationResult.validation_error("Out of stock")

        return await next_handler()

# ✅ CORRECT: Business logic in handler
class CreateOrderHandler:
    async def handle_async(self, command: CreateOrderCommand):
        # Check inventory as part of business logic
        for item in command.items:
            if not await self.inventory.has_stock(item.product_id):
                return self.validation_error("Out of stock")

        order = Order.create(command.items)
        return self.created(order)
```

### 2. **Request-Specific Logic**

```python
# Pipeline behaviors should be generic across ALL requests
# Don't create behaviors for specific commands/queries

# ❌ WRONG: Behavior for ONE specific command
class CreateOrderSpecificBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        if isinstance(request, CreateOrderCommand):
            # Logic specific to CreateOrderCommand
            pass
        return await next_handler()

# ✅ CORRECT: Put command-specific logic in handler
```

### 3. **Simple Applications Without Cross-Cutting Concerns**

```python
# For very simple apps, pipeline behaviors add unnecessary complexity
class SimpleTodoApp:
    """Simple todo app with 3 commands"""
    # Just implement handlers directly, no need for pipeline
    async def create_todo(self, title: str):
        todo = Todo(title=title)
        await self.db.todos.insert_one(todo)
        return todo
```

### 4. **One-Off Requirements**

```python
# Don't create a behavior for something used only once
# Put it in the handler instead

# ❌ WRONG: Behavior used by only ONE handler
class SendWelcomeEmailBehavior(PipelineBehavior):
    async def handle_async(self, request, next_handler):
        result = await next_handler()
        if isinstance(request, CreateUserCommand):
            await self.email.send_welcome(request.email)
        return result

# ✅ CORRECT: Put in handler
class CreateUserHandler:
    async def handle_async(self, command: CreateUserCommand):
        user = User(command.email)
        await self.repository.save_async(user)
        await self.email.send_welcome(user.email)  # Specific to this handler
        return self.created(user)
```

### 5. **Performance-Critical Tight Loops**

```python
# Pipeline behaviors add overhead - avoid for very high-throughput scenarios
class HighFrequencyMetricHandler:
    """Processes thousands of metrics per second"""
    async def handle_async(self, command: RecordMetricCommand):
        # Direct implementation without pipeline overhead
        await self.metrics.record(command.metric_name, command.value)
```

## 📝 Key Takeaways

- **Pipeline behaviors implement cross-cutting concerns** centrally
- **Wrap handlers using decorator pattern** for composable functionality
- **Keep handlers focused on business logic** by extracting infrastructure concerns
- **Common behaviors**: Logging, validation, error handling, caching, transactions
- **Always call next_handler()** to continue the pipeline
- **Use scoped lifetime** for request-specific state
- **Order matters** for dependent behaviors (auth before authorization)
- **Don't put business logic in behaviors** - keep them generic
- **Avoid modifying requests** - behaviors should be side-effect free
- **Framework provides PipelineBehavior base class** for easy implementation

## 📚 Related Documentation

- [State-Based Persistence](state-based-persistence.md) - Domain event dispatching
- [CQRS Mediation](../features/simple-cqrs.md) - Core command/query patterns
- [Dependency Injection](dependency-injection.md) - Service registration

Pipeline behaviors provide a clean, composable way to add cross-cutting functionality to your CQRS application while keeping your handlers focused on business logic.
