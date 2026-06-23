import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, Optional

from neuroglia.data.abstractions import AggregateRoot, TEntity, TKey
from neuroglia.data.queryable import Queryable

if TYPE_CHECKING:
    from neuroglia.mediation.mediator import Mediator

logger = logging.getLogger(__name__)


class Repository(Generic[TEntity, TKey], ABC):
    """
    Defines the fundamentals of a Repository with automatic domain event publishing.

    This base class provides automatic domain event publishing for aggregates after
    successful persistence operations. Domain events are automatically extracted from
    AggregateRoot entities and published via the Mediator.

    The repository follows these principles:
    - Events are published AFTER successful persistence (ensuring consistency)
    - Events are only published for AggregateRoot entities
    - Failed publishing is logged but doesn't fail the operation (best-effort)
    - Publishing can be disabled by passing mediator=None (useful for testing)

    Type Parameters:
        TEntity: The type of entities managed by this repository
        TKey: The type of the entity's unique identifier

    Examples:
        ```python
        # With automatic event publishing
        class OrderRepository(MotorRepository[Order, str]):
            def __init__(self, client, serializer, mediator):
                super().__init__(client, "orders", "orders", Order, serializer, mediator)

        # Add order - events published automatically
        order = Order.create(customer_id="123")
        await repository.add_async(order)
        # OrderCreatedEvent published automatically!

        # For testing - disable event publishing
        test_repo = OrderRepository(client, serializer, mediator=None)
        await test_repo.add_async(order)  # No events published
        ```

    For detailed information about repository patterns, see:
    https://bvandewe.github.io/pyneuro/patterns/repository/
    """

    def __init__(self, mediator: Optional["Mediator"] = None):
        """
        Initialize the repository with optional mediator for event publishing.

        Args:
            mediator: Optional Mediator instance for publishing domain events.
                     If None, events will not be published (useful for testing).
        """
        self._mediator = mediator

    @abstractmethod
    async def contains_async(self, id: TKey) -> bool:
        """Determines whether or not the repository contains an entity with the specified id"""
        raise NotImplementedError()

    @abstractmethod
    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Gets the entity with the specified id, if any"""
        raise NotImplementedError()

    async def add_async(self, entity: TEntity) -> TEntity:
        """
        Adds the specified entity and automatically publishes its domain events.

        This method follows the template method pattern:
        1. Calls _do_add_async() to persist the entity (implemented by subclasses)
        2. Publishes domain events if entity is an AggregateRoot
        3. Clears pending events from the aggregate

        Args:
            entity: The entity to add

        Returns:
            The added entity

        Raises:
            Implementation-specific exceptions from _do_add_async()
        """
        result = await self._do_add_async(entity)
        await self._publish_domain_events(entity)
        return result

    async def update_async(self, entity: TEntity) -> TEntity:
        """
        Updates the specified entity and automatically publishes its domain events.

        This method follows the template method pattern:
        1. Calls _do_update_async() to persist changes (implemented by subclasses)
        2. Publishes domain events if entity is an AggregateRoot
        3. Clears pending events from the aggregate

        Args:
            entity: The entity to update

        Returns:
            The updated entity

        Raises:
            Implementation-specific exceptions from _do_update_async()
        """
        result = await self._do_update_async(entity)
        await self._publish_domain_events(entity)
        return result

    async def remove_async(self, id: TKey) -> None:
        """
        Removes the entity with the specified key.

        Note: This method does not publish events. If you need to publish events
        on deletion, consider implementing a soft-delete pattern where you update
        the entity's state instead of removing it.

        Args:
            id: The unique identifier of the entity to remove
        """
        await self._do_remove_async(id)

    @abstractmethod
    async def _do_add_async(self, entity: TEntity) -> TEntity:
        """
        Template method for adding an entity to the data store.

        Subclasses must implement this method to provide the actual persistence logic.
        Do NOT publish events here - the base class handles event publishing.

        Args:
            entity: The entity to add

        Returns:
            The added entity
        """
        raise NotImplementedError()

    @abstractmethod
    async def _do_update_async(self, entity: TEntity) -> TEntity:
        """
        Template method for updating an entity in the data store.

        Subclasses must implement this method to provide the actual persistence logic.
        Do NOT publish events here - the base class handles event publishing.

        Args:
            entity: The entity to update

        Returns:
            The updated entity
        """
        raise NotImplementedError()

    @abstractmethod
    async def _do_remove_async(self, id: TKey) -> None:
        """
        Template method for removing an entity from the data store.

        Subclasses must implement this method to provide the actual persistence logic.

        Args:
            id: The unique identifier of the entity to remove
        """
        raise NotImplementedError()

    async def _publish_domain_events(self, entity: TEntity) -> None:
        """
        Automatically publish domain events from an aggregate after successful persistence.

        This method:
        1. Checks if mediator is configured (None = no publishing for testing)
        2. Checks if entity is an AggregateRoot (only aggregates have events)
        3. Extracts uncommitted events from the aggregate
        4. Publishes each event via the mediator
        5. Clears pending events from the aggregate

        Event publishing failures are logged but do not fail the operation (best-effort).

        Args:
            entity: The entity that was persisted
        """
        if not self._mediator:
            return  # No mediator configured - skip event publishing

        if not isinstance(entity, AggregateRoot):
            return  # Not an aggregate - no events to publish

        # Extract uncommitted events
        events = []
        if hasattr(entity, "get_uncommitted_events"):
            events = entity.get_uncommitted_events()
        elif hasattr(entity, "domain_events"):
            events = entity.domain_events

        if not events:
            return  # No events to publish

        # Publish each event
        for event in events:
            try:
                await self._mediator.publish_async(event)
                logger.debug(f"Published domain event: {type(event).__name__}")
            except Exception as e:
                logger.error(f"Failed to publish domain event {type(event).__name__}: {e}", exc_info=True)

        # Clear events from aggregate
        if hasattr(entity, "clear_pending_events"):
            entity.clear_pending_events()


class QueryableRepository(Generic[TEntity, TKey], Repository[TEntity, TKey], ABC):
    """
    Defines the abstraction for repositories that support advanced querying capabilities.

    This abstraction extends the basic Repository pattern to provide LINQ-style query
    operations that can be translated to various data store query languages while
    maintaining type safety and composability.

    Type Parameters:
        TEntity: The type of entities managed by this repository
        TKey: The type of the entity's unique identifier

    Examples:
        ```python
        class UserQueryableRepository(QueryableRepository[User, UUID]):
            async def query_async(self) -> Queryable[User]:
                return MongoQueryable(self.collection, User)

        # Usage with fluent queries
        repository = UserQueryableRepository()
        active_users = await repository.query_async() \\
            .where(lambda u: u.is_active) \\
            .order_by(lambda u: u.last_login) \\
            .take(50) \\
            .to_list()
        ```

    See Also:
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
        - Repository Pattern Guide: https://bvandewe.github.io/pyneuro/patterns/
    """

    @abstractmethod
    async def query_async(self) -> Queryable[TEntity]:
        raise NotImplementedError()


class FlexibleRepository(Generic[TEntity, TKey], Repository[TEntity, TKey], ABC):
    """
    DEPRECATED: This abstraction will be removed in a future version.

    Defines the fundamentals of a flexible repository that supports dynamic collection/database operations.
    This pattern was used for multi-tenant scenarios but has been superseded by more focused abstractions.

    Type Parameters:
        TEntity: The type of entities managed by this repository
        TKey: The type of the entity's unique identifier

    Migration Note:
        Consider using Repository[TEntity, TKey] with dependency injection to provide
        tenant-specific repository instances instead of this flexible approach.

    See Also:
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
        - Migration Guide: https://bvandewe.github.io/pyneuro/patterns/
    """

    @abstractmethod
    async def set_database(self, database: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_database(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def contains_by_collection_name_async(self, collection_nam: str, id: TKey) -> bool:
        """Determines whether or not the repository contains an entity with the specified id"""
        raise NotImplementedError()

    @abstractmethod
    async def get_by_collection_name_async(self, collection_name: str, id: TKey) -> Optional[TEntity]:
        """Gets the entity with the specified id, if any"""
        raise NotImplementedError()

    @abstractmethod
    async def add_by_collection_name_async(self, collection_name: str, entity: TEntity) -> TEntity:
        """Adds the specified entity"""
        raise NotImplementedError()

    @abstractmethod
    async def update_by_collection_name_async(self, collection_name: str, entity: TEntity) -> TEntity:
        """Persists the changes that were made to the specified entity"""
        raise NotImplementedError()

    @abstractmethod
    async def remove_by_collection_name_async(self, collection_name: str, id: TKey) -> None:
        """Removes the entity with the specified key"""
        raise NotImplementedError()
