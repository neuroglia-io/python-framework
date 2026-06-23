from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, Optional

from neuroglia.data.abstractions import DomainEvent, TAggregate, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    Aggregator,
    DeleteMode,
    EventDescriptor,
    EventStore,
    StreamReadDirection,
)
from neuroglia.hosting.abstractions import ApplicationBuilderBase

if TYPE_CHECKING:
    from neuroglia.mediation.mediator import Mediator


@dataclass
class EventSourcingRepositoryOptions(Generic[TAggregate, TKey]):
    """
    Configuration options for EventSourcingRepository.

    Attributes:
        delete_mode: Specifies how deletion should be handled (DISABLED, SOFT, HARD)
        soft_delete_method_name: Method name to call on aggregate for soft delete

    Examples:
        ```python
        # Disable deletion (default)
        options = EventSourcingRepositoryOptions[Task, str]()

        # Enable soft delete
        options = EventSourcingRepositoryOptions[Task, str](
            delete_mode=DeleteMode.SOFT
        )

        # Enable hard delete (GDPR compliance)
        options = EventSourcingRepositoryOptions[Task, str](
            delete_mode=DeleteMode.HARD
        )
        ```
    """

    delete_mode: DeleteMode = field(default=DeleteMode.DISABLED)
    """
    Specifies how deletion should be handled:
    - DISABLED: Raises NotImplementedError (default, event sourcing best practice)
    - SOFT: Calls aggregate.mark_as_deleted() or aggregate.mark_deleted() then persists
    - HARD: Physically deletes the event stream (use with caution)
    """

    soft_delete_method_name: str = field(default="mark_as_deleted")
    """
    Method name to call on aggregate for soft delete.
    Defaults to 'mark_as_deleted'. Alternative: 'mark_deleted'.
    Only used when delete_mode is SOFT.
    """


class EventSourcingRepository(Generic[TAggregate, TKey], Repository[TAggregate, TKey]):
    """
    Event sourcing repository implementation with configurable deletion strategies.

    Supports three deletion modes:
    - DISABLED: No deletion allowed (default, follows event sourcing best practices)
    - SOFT: Delegates to aggregate's deletion method, preserving event history
    - HARD: Physical stream deletion for GDPR compliance or data cleanup

    Examples:
        ```python
        # Default configuration (deletion disabled)
        repo = EventSourcingRepository[Task, str](eventstore, aggregator)

        # With soft delete enabled
        options = EventSourcingRepositoryOptions[Task, str](
            delete_mode=DeleteMode.SOFT
        )
        repo = EventSourcingRepository[Task, str](
            eventstore, aggregator, options=options
        )

        # With hard delete for GDPR compliance
        options = EventSourcingRepositoryOptions[Task, str](
            delete_mode=DeleteMode.HARD
        )
        repo = EventSourcingRepository[Task, str](
            eventstore, aggregator, options=options
        )
        ```
    """

    def __init__(
        self,
        eventstore: EventStore,
        aggregator: Aggregator,
        mediator: Optional["Mediator"] = None,
        options: Optional[EventSourcingRepositoryOptions[TAggregate, TKey]] = None,
    ):
        """Initialize a new event sourcing repository"""
        super().__init__(mediator)  # Pass mediator to base class for event publishing
        self._eventstore = eventstore
        self._aggregator = aggregator
        self._options = options or EventSourcingRepositoryOptions[TAggregate, TKey]()

    _eventstore: EventStore
    """ Gets the underlying event store """

    _aggregator: Aggregator
    """ Gets the underlying event store """

    async def contains_async(self, id: TKey) -> bool:
        return self._eventstore.contains_stream(self._build_stream_id_for(id))

    async def get_async(self, id: TKey) -> Optional[TAggregate]:
        """
        Gets the aggregate with the specified id, if any.

        Returns None if the stream does not exist.
        """
        stream_id = self._build_stream_id_for(id)
        try:
            events = await self._eventstore.read_async(stream_id, StreamReadDirection.FORWARDS, 0)
            if not events:
                return None
            return self._aggregator.aggregate(events, self.__orig_class__.__args__[0])
        except Exception:
            # If stream doesn't exist or any other error occurs, return None
            return None

    async def _do_add_async(self, aggregate: TAggregate) -> TAggregate:
        """Adds and persists the specified aggregate"""
        stream_id = self._build_stream_id_for(aggregate.id())
        events = aggregate._pending_events
        if len(events) < 1:
            raise Exception("No pending events to persist")
        encoded_events = [self._encode_event(e) for e in events]
        await self._eventstore.append_async(stream_id, encoded_events)
        aggregate.state.state_version = events[-1].aggregate_version
        # DON'T clear pending events here - let base class do it after publishing!
        # aggregate.clear_pending_events()
        return aggregate

    async def _do_update_async(self, aggregate: TAggregate) -> TAggregate:
        """Persists the changes made to the specified aggregate"""
        stream_id = self._build_stream_id_for(aggregate.id())
        events = aggregate._pending_events
        if len(events) < 1:
            raise Exception("No pending events to persist")
        encoded_events = [self._encode_event(e) for e in events]
        await self._eventstore.append_async(stream_id, encoded_events, aggregate.state.state_version)
        aggregate.state.state_version = events[-1].aggregate_version
        # DON'T clear pending events here - let base class do it after publishing!
        # aggregate.clear_pending_events()
        return aggregate

    async def _do_remove_async(self, id: TKey) -> None:
        """
        Removes the aggregate root with the specified key based on configured delete mode.

        Behavior depends on delete_mode configuration:
        - DISABLED: Raises NotImplementedError (default)
        - SOFT: Loads aggregate, calls mark_as_deleted(), persists deletion event
        - HARD: Physically deletes the event stream (irreversible)

        Args:
            id: The identifier of the aggregate to remove

        Raises:
            NotImplementedError: When delete_mode is DISABLED
            ValueError: When SOFT delete but aggregate lacks deletion method
            Exception: When aggregate not found or deletion fails
        """
        match self._options.delete_mode:
            case DeleteMode.DISABLED:
                raise NotImplementedError("Deletion is disabled for this repository. " "Event sourcing repositories preserve immutable history by default. " "Configure delete_mode=DeleteMode.SOFT for soft delete " "or delete_mode=DeleteMode.HARD for physical stream deletion.")

            case DeleteMode.SOFT:
                await self._soft_delete_async(id)

            case DeleteMode.HARD:
                await self._hard_delete_async(id)

    async def _soft_delete_async(self, id: TKey) -> None:
        """
        Soft delete by calling aggregate's deletion method.

        The repository will:
        1. Load the aggregate via get_async()
        2. Call aggregate's deletion method (mark_as_deleted or mark_deleted)
        3. Persist the deletion event via _do_update_async()

        This preserves event history while marking the aggregate as deleted.
        The aggregate controls deletion semantics and domain events.

        Args:
            id: The identifier of the aggregate to soft delete

        Raises:
            Exception: If aggregate not found
            ValueError: If aggregate lacks required deletion method
        """
        # Load the aggregate
        aggregate = await self.get_async(id)
        if aggregate is None:
            raise Exception(f"Aggregate with id '{id}' not found")

        # Call the aggregate's deletion method (convention-based)
        method_name = self._options.soft_delete_method_name
        if hasattr(aggregate, method_name) and callable(getattr(aggregate, method_name)):
            deletion_method = getattr(aggregate, method_name)
            deletion_method()
        elif hasattr(aggregate, "mark_deleted") and callable(getattr(aggregate, "mark_deleted")):
            # Fallback to alternative method name
            aggregate.mark_deleted()
        else:
            aggregate_type = type(aggregate).__name__
            raise ValueError(f"Aggregate {aggregate_type} does not have a '{method_name}()' or 'mark_deleted()' method. " f"Soft delete requires the aggregate to implement deletion logic. " f"Add a method like: def {method_name}(self) -> None: ...")

        # Persist the deletion event via update
        await self._do_update_async(aggregate)

    async def _hard_delete_async(self, id: TKey) -> None:
        """
        Physically delete the entire event stream from the event store.

        WARNING: This is irreversible and removes all history for this aggregate.
        Use for:
        - GDPR compliance (right to be forgotten)
        - Data cleanup after retention period
        - Removing test/invalid data

        Args:
            id: The identifier of the aggregate to hard delete

        Raises:
            Exception: If stream deletion fails
        """
        stream_id = self._build_stream_id_for(id)
        await self._eventstore.delete_async(stream_id)

    async def _publish_domain_events(self, entity: TAggregate) -> None:
        """
        Override base class event publishing for event-sourced aggregates.

        Event sourcing repositories DO NOT publish events directly because:
        1. Events are already persisted to the EventStore
        2. ReadModelReconciliator subscribes to EventStore and publishes ALL events
        3. Publishing here would cause DOUBLE PUBLISHING (once here, once from ReadModelReconciliator)

        For event-sourced aggregates:
        - Events are persisted to EventStore by _do_add_async/_do_update_async
        - ReadModelReconciliator.on_event_record_stream_next_async() publishes via mediator
        - This ensures single, reliable event publishing from the source of truth (EventStore)

        State-based repositories still use the base class _publish_domain_events() correctly.
        """
        # Do nothing - ReadModelReconciliator handles event publishing from EventStore

    def _build_stream_id_for(self, aggregate_id: TKey):
        """Builds a new stream id for the specified aggregate"""
        aggregate_name = self.__orig_class__.__args__[0].__name__
        return f"{aggregate_name.lower()}-{aggregate_id}"

    def _encode_event(self, e: DomainEvent):
        """Encodes a domain event into a new event descriptor"""
        event_type = type(e).__name__.lower()
        return EventDescriptor(event_type, e)

    @staticmethod
    def configure(builder: ApplicationBuilderBase, entity_type: type, key_type: type) -> ApplicationBuilderBase:
        """Configures the specified application to use an event sourcing based repository implementation to manage the specified type of entity"""
        builder.services.try_add_singleton(
            EventSourcingRepositoryOptions[entity_type, key_type],
            singleton=EventSourcingRepositoryOptions[entity_type, key_type](),
        )
        builder.services.try_add_singleton(Repository[entity_type, key_type], EventSourcingRepository[entity_type, key_type])
        return builder
