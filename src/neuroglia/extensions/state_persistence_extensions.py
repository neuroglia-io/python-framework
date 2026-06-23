"""
Extensions for registering Unit of Work and Domain Event Dispatching services.

This module provides convenient extension methods for configuring state-based persistence
and automatic domain event dispatching in the dependency injection container.
"""

from neuroglia.data.unit_of_work import IUnitOfWork, UnitOfWork
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation.behaviors.domain_event_dispatching_middleware import (
    DomainEventDispatchingMiddleware,
    TransactionBehavior,
)
from neuroglia.mediation.pipeline_behavior import PipelineBehavior


def add_unit_of_work(services: ServiceCollection) -> ServiceCollection:
    """
    Registers the Unit of Work services for state-based persistence.

    NOTE: The UnitOfWork pattern is deprecated in favor of repository-based event publishing.
    For new projects, use the repository event publishing pattern instead.

    This method configures the dependency injection container with the necessary
    services for collecting and managing domain events from aggregate roots.

    Services Registered:
        - IUnitOfWork -> UnitOfWork (Scoped): Tracks aggregates during request lifecycle

    Args:
        services: The service collection to configure

    Returns:
        The configured service collection for fluent chaining

    Recommended Pattern (Repository-Based Event Publishing):
        ```python
        from neuroglia.hosting.web import WebApplicationBuilder
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()
        Mediator.configure(builder, ["application.commands", "application.queries"])

        # Repositories automatically publish events on save
        builder.services.add_scoped(UserRepository)

        app = builder.build()
        ```

    Legacy Pattern (UnitOfWork):
        ```python
        # Basic setup (deprecated)
        services = ServiceCollection()
        services.add_unit_of_work()

        # Full CQRS setup with domain events (deprecated)
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()
        Mediator.configure(builder, ["application.commands"])
        builder.services.add_unit_of_work()
        builder.services.add_domain_event_dispatching()
        ```

    See Also:
        - Repository Pattern: https://bvandewe.github.io/pyneuro/patterns/repository/
        - State-Based Persistence: https://bvandewe.github.io/pyneuro/features/data-access/
    """
    services.add_scoped(IUnitOfWork, UnitOfWork)
    return services


def add_domain_event_dispatching(services: ServiceCollection) -> ServiceCollection:
    """
    Registers the domain event dispatching middleware for automatic event processing.

    NOTE: This is typically used with the deprecated UnitOfWork pattern. For new projects,
    prefer repository-based event publishing where repositories automatically dispatch
    events when aggregates are saved.

    This method configures pipeline behaviors that automatically collect and dispatch
    domain events after successful command execution, providing the outbox pattern
    for eventual consistency.

    Services Registered:
        - PipelineBehavior -> DomainEventDispatchingMiddleware (Scoped)

    Prerequisites:
        - Mediator must be registered (via Mediator.configure() or services.add_mediator())
        - Unit of Work must be registered (services.add_unit_of_work())

    Args:
        services: The service collection to configure

    Returns:
        The configured service collection for fluent chaining

    Recommended Pattern (Repository-Based):
        ```python
        from neuroglia.hosting.web import WebApplicationBuilder
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()
        Mediator.configure(builder, ["application.commands", "application.queries"])

        # Repositories automatically handle event publishing
        builder.services.add_scoped(UserRepository)

        app = builder.build()
        ```

    Legacy Pattern (UnitOfWork with Middleware):
        ```python
        # Complete setup for state-based persistence with domain events
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()
        Mediator.configure(builder, ["application.commands"])
        builder.services.add_unit_of_work()
        builder.services.add_domain_event_dispatching()

        # Usage in handlers
        class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult]):
            def __init__(self, unit_of_work: IUnitOfWork, user_repo: UserRepository):
                self.unit_of_work = unit_of_work
                self.user_repo = user_repo

            async def handle_async(self, command):
                user = User.create(command.email)  # Raises UserCreatedEvent
                await self.user_repo.save_async(user)
                self.unit_of_work.register_aggregate(user)  # Auto-dispatching
                return self.created(user)
        ```

    Event Processing Flow:
        ```
        1. Command handler executes and modifies aggregates
        2. Handler registers modified aggregates with UnitOfWork
        3. DomainEventDispatchingMiddleware collects events after success
        4. Events are automatically dispatched through mediator
        5. UnitOfWork is cleared for next request
        ```

    See Also:
        - Repository Pattern: https://bvandewe.github.io/pyneuro/patterns/repository/
        - Domain Events: https://bvandewe.github.io/pyneuro/patterns/cqrs/
    """
    services.add_scoped(PipelineBehavior, DomainEventDispatchingMiddleware)
    return services


def add_transaction_behavior(services: ServiceCollection) -> ServiceCollection:
    """
    Registers the transaction behavior for database transaction management.

    This method adds a pipeline behavior that can wrap command execution in
    database transactions, providing atomicity and proper rollback on failures.

    Note: This is a placeholder implementation. Actual transaction management
    would require integration with your specific database and ORM.

    Services Registered:
        - PipelineBehavior -> TransactionBehavior (Scoped)

    Args:
        services: The service collection to configure

    Returns:
        The configured service collection for fluent chaining

    Usage:
        ```python
        from neuroglia.hosting.web import WebApplicationBuilder
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()
        Mediator.configure(builder, ["application.commands"])

        # Should be registered before event dispatching
        builder.services.add_transaction_behavior()
        builder.services.add_unit_of_work()
        builder.services.add_domain_event_dispatching()

        app = builder.build()
        ```

    Behavior Order:
        ```
        1. TransactionBehavior (begins/commits/rolls back transaction)
        2. DomainEventDispatchingMiddleware (dispatches events after commit)
        3. Command Handler (executes business logic)
        ```

    See Also:
        - Pipeline Behaviors: https://bvandewe.github.io/pyneuro/patterns/cqrs/
    """
    services.add_scoped(PipelineBehavior, TransactionBehavior)
    return services


def add_state_based_persistence(services: ServiceCollection) -> ServiceCollection:
    """
    Registers all services required for complete state-based persistence support.

    NOTE: This pattern is deprecated. For new projects, use repository-based event publishing
    where repositories automatically dispatch events when aggregates are saved.

    This is a convenience method that registers all the components needed for
    state-based persistence with automatic domain event dispatching:
    - Unit of Work for aggregate tracking
    - Domain Event Dispatching middleware
    - Transaction behavior (optional, placeholder implementation)

    Prerequisites:
        - Mediator must be registered first (via Mediator.configure())

    Services Registered:
        - IUnitOfWork -> UnitOfWork (Scoped)
        - PipelineBehavior -> TransactionBehavior (Scoped)
        - PipelineBehavior -> DomainEventDispatchingMiddleware (Scoped)

    Args:
        services: The service collection to configure

    Returns:
        The configured service collection for fluent chaining

    Recommended Pattern (Repository-Based):
        ```python
        from neuroglia.hosting.web import WebApplicationBuilder
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()
        Mediator.configure(builder, ["application.commands", "application.queries"])

        # Repositories automatically publish events
        builder.services.add_scoped(UserRepository)

        app = builder.build()
        ```

    Legacy Pattern (Complete UnitOfWork Setup):
        ```python
        # Complete setup in one call (deprecated)
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()
        Mediator.configure(builder, ["application.commands"])
        builder.services.add_state_based_persistence()

        # Equivalent to:
        Mediator.configure(builder, ["application.commands"])
        builder.services.add_unit_of_work()
        builder.services.add_transaction_behavior()
        builder.services.add_domain_event_dispatching()
        ```

    Architecture:
        ```
        Request -> Pipeline:
                   1. TransactionBehavior (transaction management)
                   2. DomainEventDispatchingMiddleware (event processing)
                   3. CommandHandler (business logic)

        Flow:
        1. Begin transaction
        2. Execute command handler
        3. Commit transaction (on success)
        4. Collect domain events from UnitOfWork
        5. Dispatch events through mediator
        6. Clear UnitOfWork
        ```

    See Also:
        - Repository Pattern: https://bvandewe.github.io/pyneuro/patterns/repository/
        - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
    """
    services.add_unit_of_work()
    services.add_transaction_behavior()
    services.add_domain_event_dispatching()
    return services


# Extend ServiceCollection with extension methods
ServiceCollection.add_unit_of_work = add_unit_of_work
ServiceCollection.add_domain_event_dispatching = add_domain_event_dispatching
ServiceCollection.add_transaction_behavior = add_transaction_behavior
ServiceCollection.add_state_based_persistence = add_state_based_persistence
