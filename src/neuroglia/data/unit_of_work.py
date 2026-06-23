from abc import ABC, abstractmethod

from neuroglia.data.abstractions import AggregateRoot, DomainEvent
from neuroglia.hosting.abstractions import ApplicationBuilderBase


class IUnitOfWork(ABC):
    """
    Represents the abstraction for the Unit of Work pattern in domain-driven design.

    The Unit of Work pattern maintains a list of objects affected by a business transaction
    and coordinates writing out changes and resolving concurrency problems. It provides
    automatic domain event collection and dispatching after successful transactions.

    Key Features:
        - Tracks aggregate changes during request lifecycle
        - Collects domain events from modified aggregates
        - Coordinates transactional boundaries
        - Enables automatic domain event dispatching
        - Maintains consistency between state changes and events

    Usage Patterns:
        ```python
        # In command handlers
        class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
            def __init__(self,
                       user_repository: UserRepository,
                       unit_of_work: IUnitOfWork):
                self.user_repository = user_repository
                self.unit_of_work = unit_of_work

            async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
                # Create and modify aggregate
                user = User.create(command.email, command.name)
                await self.user_repository.save_async(user)

                # Register aggregate for event collection
                self.unit_of_work.register_aggregate(user)

                # Domain events will be automatically dispatched after successful command
                return self.created(self.mapper.map(user, UserDto))
        ```

    Integration with Middleware:
        ```python
        # DomainEventDispatchingMiddleware automatically:
        # 1. Collects events from registered aggregates
        # 2. Dispatches events after successful command execution
        # 3. Clears the unit of work for the next request
        ```

    See Also:
        - Unit of Work Pattern: https://martinfowler.com/eaaCatalog/unitOfWork.html
        - Domain Events: https://bvandewe.github.io/pyneuro/patterns/domain-events/
        - Aggregate Root: https://bvandewe.github.io/pyneuro/patterns/aggregate-root/
    """

    @abstractmethod
    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """
        Registers an aggregate root for event collection and tracking.

        This method should be called whenever an aggregate is created or modified
        during a business transaction. The UnitOfWork will collect domain events
        from the aggregate for later dispatching.

        Args:
            aggregate: The aggregate root to register for tracking

        Examples:
            ```python
            # After creating or modifying an aggregate
            user = User.create("john@example.com", "John Doe")
            await self.user_repository.save_async(user)
            self.unit_of_work.register_aggregate(user)  # Events will be collected

            # After updating an aggregate
            user = await self.user_repository.get_by_id_async(user_id)
            user.activate()  # Raises UserActivatedEvent
            await self.user_repository.save_async(user)
            self.unit_of_work.register_aggregate(user)  # Events will be collected
            ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_domain_events(self) -> list[DomainEvent]:
        """
        Gets all domain events from registered aggregates.

        This method collects all pending domain events from aggregates that have
        been registered during the current unit of work. Events are collected
        in the order they were raised.

        Returns:
            List of domain events from all registered aggregates

        Examples:
            ```python
            # Typically called by middleware after successful command execution
            events = unit_of_work.get_domain_events()
            for event in events:
                await mediator.publish_async(event)
            ```
        """
        raise NotImplementedError()

    @abstractmethod
    def clear(self) -> None:
        """
        Clears all registered aggregates and collected events.

        This method resets the unit of work state, removing all tracked aggregates
        and their associated events. Should be called at the end of each request
        or after domain event dispatching.

        Examples:
            ```python
            # Typically called by middleware after processing
            try:
                # Process command and dispatch events
                result = await handler.handle_async(command)
                events = unit_of_work.get_domain_events()
                await dispatch_events(events)
                return result
            finally:
                unit_of_work.clear()  # Reset for next request
            ```
        """
        raise NotImplementedError()

    @abstractmethod
    def has_changes(self) -> bool:
        """
        Determines if any aggregates have been registered with pending changes.

        Returns:
            True if there are registered aggregates with domain events, False otherwise

        Examples:
            ```python
            # Check if there are changes to process
            if unit_of_work.has_changes():
                events = unit_of_work.get_domain_events()
                await self.event_dispatcher.dispatch_all(events)
            ```
        """
        raise NotImplementedError()


class UnitOfWork(IUnitOfWork):
    """
    Default implementation of the Unit of Work pattern for collecting and managing domain events.

    This implementation provides a simple, in-memory tracking of aggregate roots and their
    domain events within a single request scope. It's designed to work seamlessly with
    the DomainEventDispatchingMiddleware for automatic event processing.

    Attributes:
        _aggregates: Set of registered aggregate roots

    Thread Safety:
        This implementation is NOT thread-safe. Each request should have its own
        UnitOfWork instance (typically registered as Scoped in DI container).

    Examples:
        ```python
        # Dependency injection registration
        services.add_scoped(IUnitOfWork, UnitOfWork)

        # Usage in handlers
        class OrderHandler(CommandHandler[CreateOrderCommand, OperationResult[OrderDto]]):
            def __init__(self,
                       order_repository: OrderRepository,
                       unit_of_work: IUnitOfWork):
                self.order_repository = order_repository
                self.unit_of_work = unit_of_work

            async def handle_async(self, command: CreateOrderCommand) -> OperationResult[OrderDto]:
                order = Order.create(command.customer_id, command.items)
                await self.order_repository.save_async(order)
                self.unit_of_work.register_aggregate(order)  # Automatic event collection

                return self.created(self.mapper.map(order, OrderDto))
        ```
    """

    def __init__(self):
        """Initializes a new UnitOfWork instance with empty aggregate tracking."""
        self._aggregates: set[AggregateRoot] = set()

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """Registers an aggregate root for event collection and tracking."""
        if aggregate is not None:
            self._aggregates.add(aggregate)

    def get_domain_events(self) -> list[DomainEvent]:
        """Gets all domain events from registered aggregates."""
        events: list[DomainEvent] = []

        for aggregate in self._aggregates:
            if hasattr(aggregate, "get_uncommitted_events"):
                # Use existing method if available (for event-sourced aggregates)
                aggregate_events = aggregate.get_uncommitted_events()
            elif hasattr(aggregate, "domain_events"):
                # Use new property for state-based aggregates
                aggregate_events = aggregate.domain_events
            elif hasattr(aggregate, "_pending_events"):
                # Fallback to internal field
                aggregate_events = aggregate._pending_events.copy()
            else:
                continue

            if aggregate_events:
                events.extend(aggregate_events)

        return events

    def clear(self) -> None:
        """Clears all registered aggregates and their events."""
        # Clear events from all registered aggregates
        for aggregate in self._aggregates:
            if hasattr(aggregate, "clear_pending_events"):
                aggregate.clear_pending_events()

        # Clear the aggregate tracking
        self._aggregates.clear()

    def has_changes(self) -> bool:
        """Determines if any aggregates have been registered with pending changes."""
        if not self._aggregates:
            return False

        for aggregate in self._aggregates:
            if hasattr(aggregate, "get_uncommitted_events"):
                if aggregate.get_uncommitted_events():
                    return True
            elif hasattr(aggregate, "domain_events"):
                if aggregate.domain_events:
                    return True
            elif hasattr(aggregate, "_pending_events"):
                if aggregate._pending_events:
                    return True

        return False

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> ApplicationBuilderBase:
        """Registers and configures UnitOfWork services to the specified service collection.

        Args:
            services (ServiceCollection): the service collection to configure

        """
        builder.services.add_scoped(IUnitOfWork, implementation_factory=lambda _: UnitOfWork())
        return builder
