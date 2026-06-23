"""
Neuroglia CQRS Mediation Module
================================

This module provides a complete implementation of the CQRS (Command Query Responsibility
Segregation) and Mediator patterns for building maintainable, scalable applications with
clear separation between read and write operations.

Quick Start
-----------

**1. Define a Command (Write Operation):**
```python
from dataclasses import dataclass
from neuroglia.mediation import Command, CommandHandler
from neuroglia.core import OperationResult

@dataclass
class CreateUserCommand(Command[OperationResult[UserDto]]):
    email: str
    name: str
    password: str

class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
    async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
        # Validation
        if not command.email:
            return self.bad_request("Email is required")

        # Business logic
        user = User.create(command.email, command.name)
        await self.repository.save_async(user)

        # Success response
        return self.created(UserDto.from_entity(user))
```

**2. Define a Query (Read Operation):**
```python
@dataclass
class GetUserByIdQuery(Query[OperationResult[UserDto]]):
    user_id: str

class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, OperationResult[UserDto]]):
    async def handle_async(self, query: GetUserByIdQuery) -> OperationResult[UserDto]:
        user = await self.repository.get_by_id_async(query.user_id)

        if not user:
            return self.not_found(User, query.user_id)

        return self.ok(UserDto.from_entity(user))
```

**3. Execute via Mediator:**
```python
# In controller or service
from neuroglia.mediation import Mediator

# Command execution
command = CreateUserCommand(email="user@example.com", name="John Doe", password="secret")
result = await mediator.execute_async(command)

if result.is_success:
    created_user = result.data  # UserDto
else:
    error_message = result.error_message
```

Core Components
---------------

**Request Types:**
    • Command[TResult]      - Represents write operations that modify state
    • Query[TResult]        - Represents read operations without side effects
    • Request[TResult]      - Base abstraction for all requests

**Handler Types:**
    • CommandHandler[TCommand, TResult]  - Processes commands (write operations)
    • QueryHandler[TQuery, TResult]      - Processes queries (read operations)
    • RequestHandler[TRequest, TResult]  - Base abstraction for all handlers

**Orchestration:**
    • Mediator              - Central dispatcher for all requests
    • PipelineBehavior      - Cross-cutting concerns (validation, logging, etc.)

**Events:**
    • DomainEventHandler    - Handles domain events from aggregates
    • NotificationHandler   - Handles notifications to multiple subscribers
    • IntegrationEventHandler - Handles events from external systems

Available Helper Methods (RequestHandler)
------------------------------------------

All command and query handlers inherit 12 helper methods for creating standardized responses:

**SUCCESS (2xx):**
    ✓ ok(data)                      → 200 OK             Standard success
    ✓ created(data)                 → 201 Created        Resource created
    ✓ accepted(data)                → 202 Accepted       Async operation queued
    ✓ no_content()                  → 204 No Content     Success, no data

**CLIENT ERRORS (4xx):**
    ✗ bad_request(detail)           → 400 Bad Request    Validation error
    ✗ unauthorized(detail)          → 401 Unauthorized   Auth required
    ✗ forbidden(detail)             → 403 Forbidden      Access denied
    ✗ not_found(type, key, name)    → 404 Not Found      Resource not found
    ✗ conflict(message)             → 409 Conflict       State conflict
    ✗ unprocessable_entity(detail)  → 422 Unprocessable  Semantic error

**SERVER ERRORS (5xx):**
    ✗ internal_server_error(detail) → 500 Internal       Unexpected error
    ✗ service_unavailable(detail)   → 503 Unavailable    Service down

Usage Patterns
--------------

**Pattern 1: Simple Command Handler**
```python
class UpdateOrderHandler(CommandHandler[UpdateOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: UpdateOrderCommand) -> OperationResult[OrderDto]:
        order = await self.repository.get_by_id_async(command.order_id)

        if not order:
            return self.not_found(Order, command.order_id)

        order.update_status(command.status)
        await self.repository.save_async(order)

        return self.ok(OrderDto.from_entity(order))
```

**Pattern 2: Query with Pagination**
```python
class ListUsersQuery(Query[OperationResult[List[UserDto]]]):
    page: int = 1
    page_size: int = 20

class ListUsersHandler(QueryHandler[ListUsersQuery, OperationResult[List[UserDto]]]):
    async def handle_async(self, query: ListUsersQuery) -> OperationResult[List[UserDto]]:
        users = await self.repository.list_async(
            skip=(query.page - 1) * query.page_size,
            limit=query.page_size
        )

        dtos = [UserDto.from_entity(u) for u in users]
        return self.ok(dtos)
```

**Pattern 3: Command with Complex Validation**
```python
class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
        # Input validation
        if not command.items:
            return self.bad_request("Order must contain at least one item")

        # Business validation
        if command.total_amount <= 0:
            return self.bad_request("Order total must be positive")

        # Authorization
        if not await self.can_place_order(command.customer_id):
            return self.forbidden("Customer account suspended")

        # Check inventory
        for item in command.items:
            if not await self.has_stock(item.product_id, item.quantity):
                return self.conflict(f"Insufficient stock for {item.product_id}")

        # Create order
        order = Order.create(command.customer_id, command.items)
        await self.repository.save_async(order)

        return self.created(OrderDto.from_entity(order))
```

**Pattern 4: Background Processing**
```python
class ProcessBulkImportHandler(CommandHandler[ProcessBulkImportCommand, OperationResult[str]]):
    async def handle_async(self, command: ProcessBulkImportCommand) -> OperationResult[str]:
        # Enqueue background job
        job_id = await self.task_scheduler.enqueue(
            self.process_import_job,
            command.file_path
        )

        return self.accepted(f"Import job {job_id} queued for processing")
```

**Pattern 5: Exception Handling**
```python
class TransferFundsHandler(CommandHandler[TransferFundsCommand, OperationResult[TransactionDto]]):
    async def handle_async(self, command: TransferFundsCommand) -> OperationResult[TransactionDto]:
        try:
            transaction = await self.banking_service.transfer(
                from_account=command.from_account_id,
                to_account=command.to_account_id,
                amount=command.amount
            )
            return self.created(TransactionDto.from_entity(transaction))

        except InsufficientFundsException as e:
            return self.bad_request(f"Insufficient funds: {e}")

        except AccountNotFoundException as e:
            return self.not_found(Account, e.account_id)

        except Exception as e:
            log.error(f"Transfer failed: {e}")
            return self.internal_server_error("Failed to process transfer")
```

Setup & Configuration
---------------------

**Basic Setup:**
```python
from neuroglia.hosting.web import WebApplicationBuilder

builder = WebApplicationBuilder()

# Register mediator with automatic handler discovery
builder.services.add_mediator(["application.commands", "application.queries"])

app = builder.build()
```

**With Pipeline Behaviors (Cross-Cutting Concerns):**
```python
# Add validation
builder.services.add_pipeline_behavior(ValidationBehavior)

# Add logging
builder.services.add_pipeline_behavior(LoggingBehavior)

# Add metrics
builder.services.add_cqrs_metrics()
```

Type Hints Best Practices
--------------------------

**Use specific generic types for IDE support:**
```python
# Command returning a DTO
class CreateUserCommand(Command[OperationResult[UserDto]]):
    pass

# Query returning a list of DTOs
class ListUsersQuery(Query[OperationResult[List[UserDto]]]):
    pass

# Query returning optional data
class GetUserQuery(Query[OperationResult[Optional[UserDto]]]):
    pass

# Command with no return data
class DeleteUserCommand(Command[OperationResult[None]]):
    pass

# Query returning primitive type
class GetUserCountQuery(Query[OperationResult[int]]):
    pass
```

Common Mistakes to Avoid
-------------------------

**❌ DON'T construct OperationResult manually:**
```python
# WRONG
result = OperationResult("OK", 200)
result.data = user
return result
```

**✅ DO use helper methods:**
```python
# CORRECT
return self.ok(user)
```

**❌ DON'T use static methods on OperationResult:**
```python
# WRONG - These methods don't exist
return OperationResult.success(user)
return OperationResult.fail("error")
```

**✅ DO use instance methods from RequestHandler:**
```python
# CORRECT
return self.ok(user)
return self.bad_request("error")
```

**❌ DON'T pass cancellation_token:**
```python
# WRONG - Parameter doesn't exist
async def handle_async(self, request: TRequest, cancellation_token) -> TResult:
    pass
```

**✅ DO use correct signature:**
```python
# CORRECT
async def handle_async(self, request: TRequest) -> TResult:
    pass
```

See Also
--------
- Documentation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
- Source Code: neuroglia.mediation.mediator
- Related: neuroglia.core.OperationResult, neuroglia.mvc.ControllerBase
"""

# Import mediator extensions to register the add_mediator method
from neuroglia.extensions.mediator_extensions import add_mediator

from .mediator import *
from .metrics_middleware import MetricsPipelineBehavior, add_cqrs_metrics
from .simple import (
    InMemoryRepository,
    SimpleApplicationSettings,
    SimpleCommandHandler,
    SimpleQueryHandler,
    add_simple_mediator,
    create_simple_app,
    register_simple_handler,
    register_simple_handlers,
)

# Explicit exports for IDE autocomplete and discoverability
__all__ = [
    # ============================================================================
    # CORE REQUEST TYPES - Define your commands and queries with these
    # ============================================================================
    "Request",  # Base abstraction for all CQRS requests
    "Command",  # Write operations that modify state
    "Query",  # Read operations without side effects
    # ============================================================================
    # HANDLER TYPES - Inherit from these to process requests
    # ============================================================================
    "RequestHandler",  # Base handler (provides 12 helper methods: ok, created, bad_request, etc.)
    "CommandHandler",  # Processes commands (write operations)
    "QueryHandler",  # Processes queries (read operations)
    # ============================================================================
    # EVENT HANDLERS - Handle domain and integration events
    # ============================================================================
    "DomainEventHandler",  # Handles domain events from aggregates
    "NotificationHandler",  # Handles notifications to multiple subscribers
    "IntegrationEventHandler",  # Handles events from external systems
    # ============================================================================
    # ORCHESTRATION - Central dispatcher and pipeline behaviors
    # ============================================================================
    "Mediator",  # Central request dispatcher - use mediator.execute_async(request)
    "PipelineBehavior",  # Cross-cutting concerns (validation, logging, metrics)
    # ============================================================================
    # SETUP UTILITIES - Configuration and registration
    # ============================================================================
    "add_mediator",  # ServiceCollection extension: services.add_mediator()
    "add_cqrs_metrics",  # Add OpenTelemetry metrics for CQRS operations
    "MetricsPipelineBehavior",  # Pipeline behavior for automatic metrics collection
    # ============================================================================
    # SIMPLIFIED PATTERNS (Optional) - For basic applications without full DI
    # ============================================================================
    "SimpleCommandHandler",  # Simplified command handler without dependency injection
    "SimpleQueryHandler",  # Simplified query handler without dependency injection
    "SimpleApplicationSettings",  # Basic settings for simple applications
    "InMemoryRepository",  # In-memory repository for testing/prototyping
    "add_simple_mediator",  # Register simplified mediator
    "create_simple_app",  # Quick app setup for simple scenarios
    "register_simple_handler",  # Register single handler
    "register_simple_handlers",  # Register multiple handlers
]
