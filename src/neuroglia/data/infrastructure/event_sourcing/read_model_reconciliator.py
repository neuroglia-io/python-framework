import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Optional

from rx.core.typing import Disposable

from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    EventRecord,
    EventStore,
    EventStoreOptions,
)
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.hosting.abstractions import HostedService
from neuroglia.mediation.mediator import Mediator
from neuroglia.reactive import AsyncRx

log = logging.getLogger(__name__)


@dataclass
class ReadModelConciliationOptions:
    """Represents the options used to configure the application's read model reconciliation features.

    Attributes:
        consumer_group: The name of the group of consumers the application's read model is maintained by
        sequential_processing: If True, events are processed sequentially per aggregate to maintain
            causal ordering. Events from different aggregates can still be processed in parallel.
            Default is True to prevent race conditions in projections.

    Examples:
        ```python
        # Default: Sequential processing per aggregate (recommended)
        options = ReadModelConciliationOptions(
            consumer_group="my-read-model"
        )

        # Parallel processing (for independent handlers only)
        options = ReadModelConciliationOptions(
            consumer_group="my-read-model",
            sequential_processing=False
        )
        ```
    """

    consumer_group: str
    """ Gets the name of the group of consumers the application's read model is maintained by """

    sequential_processing: bool = field(default=True)
    """
    If True (default), events from the same aggregate are processed sequentially to maintain
    causal ordering. This prevents race conditions where a projection handler for a subsequent
    event runs before the handler for a preceding event has completed.

    When False, events are processed concurrently which may improve throughput but can cause
    race conditions if projection handlers have dependencies on prior events being processed.
    """


class AggregateEventQueue:
    """
    Manages sequential event processing per aggregate.

    This class ensures that events from the same aggregate are processed in order,
    while allowing events from different aggregates to be processed concurrently.

    This solves the race condition where:
    1. Aggregate emits EventA followed by EventB
    2. EventA handler creates a document in MongoDB
    3. EventB handler updates that document
    4. Without ordering, EventB handler may run before EventA completes

    Attributes:
        _queues: Maps aggregate_id to its event queue
        _processors: Maps aggregate_id to its processing task
        _lock: Protects concurrent access to queues and processors
    """

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._processors: dict[str, Optional[asyncio.Task]] = {}
        self._lock = asyncio.Lock()

    async def enqueue(self, aggregate_id: str, event_record: Any, process_func: Callable[[Any], Coroutine[Any, Any, None]]) -> None:
        """
        Enqueue an event for sequential processing.

        Args:
            aggregate_id: The aggregate identifier to group events by
            event_record: The event record to process (must have 'data' attribute)
            process_func: Async function to call for processing the event
        """
        async with self._lock:
            await self._queues[aggregate_id].put((event_record, process_func))

            # Start processor for this aggregate if not already running
            if aggregate_id not in self._processors or self._processors[aggregate_id] is None:
                self._processors[aggregate_id] = asyncio.create_task(self._process_queue(aggregate_id))

    async def _process_queue(self, aggregate_id: str) -> None:
        """
        Process events from an aggregate's queue sequentially.

        This ensures causal ordering: each event completes before the next begins.
        """
        queue = self._queues[aggregate_id]

        while True:
            try:
                # Wait for next event with timeout to allow cleanup
                try:
                    event_record, process_func = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # No events for this aggregate in 30 seconds, clean up
                    async with self._lock:
                        if queue.empty():
                            self._processors[aggregate_id] = None
                            return
                    continue

                # Process the event sequentially (await completion)
                try:
                    await process_func(event_record)
                except Exception as ex:
                    log.error(f"Error processing event for aggregate {aggregate_id}: {ex}", exc_info=True)

                queue.task_done()

            except asyncio.CancelledError:
                log.debug(f"Event processor for aggregate {aggregate_id} cancelled")
                break
            except Exception as ex:
                log.error(f"Unexpected error in event processor: {ex}", exc_info=True)

    async def shutdown(self) -> None:
        """Cancel all processing tasks during shutdown."""
        async with self._lock:
            for task in self._processors.values():
                if task is not None:
                    task.cancel()
            self._processors.clear()


class ReadModelReconciliator(HostedService):
    """
    Reconciles the read model by streaming and handling events from the event store.

    This service subscribes to the event store's category stream and processes events
    to update read model projections. It supports two processing modes:

    **Sequential Processing (Default - Recommended)**:
        Events from the same aggregate are processed sequentially to maintain causal
        ordering. This prevents race conditions where projection handlers for subsequent
        events run before handlers for preceding events complete.

        Example scenario protected against:
        1. ToolGroupCreatedEvent → Creates ToolGroupDto in MongoDB
        2. SelectorAddedEvent → Updates the ToolGroupDto with new selector
        Without sequential processing, step 2 might run before step 1 completes,
        causing "document not found" errors.

    **Parallel Processing**:
        Events are processed concurrently for higher throughput. Only use this mode
        if your projection handlers are independent and don't rely on prior events
        being processed.

    Attributes:
        _service_provider: The current service provider for dependency resolution
        _mediator: The mediator for publishing events to handlers
        _event_store_options: Configuration options for the event store
        _event_store: The event store service for reading events
        _options: Configuration options for read model reconciliation
        _event_queue: Queue for sequential event processing per aggregate
        _subscription: The event store subscription handle

    Examples:
        ```python
        # Configure with sequential processing (default)
        options = ReadModelConciliationOptions(
            consumer_group="my-projections"
        )
        reconciliator = ReadModelReconciliator(
            service_provider, mediator, event_store_options, event_store, options
        )
        await reconciliator.start_async()
        ```

    See Also:
        - Event Sourcing: https://bvandewe.github.io/pyneuro/patterns/event-sourcing/
        - Read Model Projections: https://bvandewe.github.io/pyneuro/patterns/cqrs/
    """

    _service_provider: ServiceProviderBase
    """ Gets the current service provider """

    _mediator: Mediator

    _event_store_options: EventStoreOptions
    """ Gets the options used to configure the event store """

    _event_store: EventStore
    """ Gets the service used to persist and stream domain events """

    _options: ReadModelConciliationOptions
    """ Gets the options used to configure read model reconciliation """

    _event_queue: Optional[AggregateEventQueue]
    """ Queue for sequential event processing per aggregate """

    _subscription: Optional[Disposable]

    def __init__(self, service_provider: ServiceProviderBase, mediator: Mediator, event_store_options: EventStoreOptions, event_store: EventStore, options: Optional[ReadModelConciliationOptions] = None):
        self._service_provider = service_provider
        self._mediator = mediator
        self._event_store_options = event_store_options
        self._event_store = event_store
        self._options = options or ReadModelConciliationOptions(consumer_group=event_store_options.consumer_group if hasattr(event_store_options, "consumer_group") else "default")
        self._event_queue = AggregateEventQueue() if self._options.sequential_processing else None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._subscription = None

    async def start_async(self):
        """Start the read model reconciliator and begin processing events."""
        self._loop = asyncio.get_event_loop()
        await self.subscribe_async()
        log.info(f"ReadModelReconciliator started with " f"{'sequential' if self._options.sequential_processing else 'parallel'} processing")

    async def stop_async(self):
        """Stop the read model reconciliator and clean up resources."""
        if self._subscription is not None:
            self._subscription.dispose()
        if self._event_queue:
            await self._event_queue.shutdown()
        log.info("ReadModelReconciliator stopped")

    async def subscribe_async(self):
        """Subscribe to the event store's category stream."""
        observable = await self._event_store.observe_async(f"$ce-{self._event_store_options.database_name}", self._event_store_options.consumer_group)

        def on_next(e: EventRecord):
            """Schedule the async handler on the main event loop without closing it."""
            try:
                if self._loop is None:
                    log.warning("Event loop not initialized, skipping event")
                    return

                # Use call_soon_threadsafe to schedule the coroutine on the main loop
                # This prevents creating/closing new event loops which breaks Motor
                self._loop.call_soon_threadsafe(lambda: asyncio.create_task(self._handle_event_async(e)))
            except RuntimeError as ex:
                log.warning(f"Event loop closed, skipping event: " f"{type(e.data).__name__ if hasattr(e, 'data') else 'unknown'} - {ex}")

        self._subscription = AsyncRx.subscribe(observable, on_next)

    async def _handle_event_async(self, e: EventRecord) -> None:
        """
        Handle an incoming event record.

        Routes to either sequential or parallel processing based on configuration.
        """
        if self._options.sequential_processing and self._event_queue:
            # Extract aggregate ID from the event for grouping
            aggregate_id = self._extract_aggregate_id(e)
            await self._event_queue.enqueue(aggregate_id, e, self.on_event_record_stream_next_async)
        else:
            # Parallel processing (legacy behavior)
            await self.on_event_record_stream_next_async(e)

    def _extract_aggregate_id(self, e: EventRecord) -> str:
        """
        Extract the aggregate ID from an event record for sequential processing grouping.

        Tries multiple strategies to find the aggregate ID:
        1. From event data's aggregate_id attribute
        2. From event record's stream_id (format: aggregatetype-aggregateid)
        3. Falls back to "unknown" if not found
        """
        # Try to get from event data
        if hasattr(e, "data") and e.data is not None and hasattr(e.data, "aggregate_id"):
            agg_id = getattr(e.data, "aggregate_id", None)
            if agg_id is not None:
                return str(agg_id)

        # Try to get from stream ID (format: aggregatetype-aggregateid)
        if hasattr(e, "stream_id") and e.stream_id:
            parts = str(e.stream_id).split("-", 1)
            if len(parts) > 1:
                return parts[1]

        # Fallback - all events go to same queue (fully sequential)
        log.debug(f"Could not extract aggregate_id from event {type(e.data).__name__}")
        return "unknown"

    async def on_event_record_stream_next_async(self, e: EventRecord):
        """
        Process a single event record by publishing it through the mediator.

        This method is called either directly (parallel mode) or from the
        aggregate event queue (sequential mode).

        Args:
            e: The event record to process
        """
        try:
            # Publish the event through the mediator
            await self._mediator.publish_async(e.data)

            # Acknowledge successful processing
            # Use duck typing to support both AckableEventRecord and mock objects
            if hasattr(e, "ack_async") and callable(getattr(e, "ack_async", None)):
                await e.ack_async()

            log.debug(f"Successfully processed event: {type(e.data).__name__}")

        except Exception as ex:
            log.error(f"An exception occurred while publishing an event of type " f"'{type(e.data).__name__}': {ex}", exc_info=True)

            # Negative acknowledge on processing failure
            # Use duck typing to support both AckableEventRecord and mock objects
            if hasattr(e, "nack_async") and callable(getattr(e, "nack_async", None)):
                await e.nack_async()

    async def on_event_record_stream_error(self, ex: Exception):
        """Handle errors from the event record stream by resubscribing."""
        log.error(f"Event stream error, resubscribing: {ex}")
        await self.subscribe_async()
