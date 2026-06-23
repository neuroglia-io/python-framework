import asyncio
import inspect
import logging
import sys
from typing import Any, Dict, Optional

import rx
from kurrentdbclient import AsyncKurrentDBClient as AsyncClientFactory
from kurrentdbclient import NewEvent, RecordedEvent, StreamState
from kurrentdbclient.exceptions import AlreadyExistsError as AlreadyExists
from rx.core.observable.observable import Observable
from rx.disposable.disposable import Disposable
from rx.subject.subject import Subject

from neuroglia.data.abstractions import DomainEvent
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    AckableEventRecord,
    Aggregator,
    EventDescriptor,
    EventRecord,
    EventStore,
    EventStoreOptions,
    StreamDescriptor,
    StreamReadDirection,
)
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.serialization.json import JsonSerializer


class ESEventStore(EventStore):
    """Represents the EventStore.com implementation of the EventStore abstract class"""

    _metadata_type = "type"
    """ Gets the name of the metadata attribute used to store the qualified name of the recorded event's type ('{module_name}.{type_name}')  """

    _eventstore_options: EventStoreOptions
    """ Gets the options used to configure the EventStore """

    _connection_string: str
    """ Gets the connection string for EventStoreDB """

    _eventstore_client: Optional[Any]  # _AsyncioEventStoreDBClient
    """ Gets the service used to interact with the EventStore DB"""

    _serializer: JsonSerializer
    """ Gets the service used to serialize/deserialize objects to/from JSON"""

    def __init__(
        self,
        options: EventStoreOptions,
        connection_string_or_client: str | Any,  # Can be connection string or pre-initialized client (for testing)
        serializer: JsonSerializer,
    ):
        self._eventstore_options = options
        self._serializer = serializer

        # Check if we got a connection string or an already-initialized client
        if isinstance(connection_string_or_client, str):
            self._connection_string = connection_string_or_client
            self._eventstore_client = None  # Will be lazily initialized
        else:
            # Pre-initialized client (typically for testing)
            self._connection_string = None
            self._eventstore_client = connection_string_or_client

    async def _ensure_client(self) -> Any:
        """Lazily initialize the async KurrentDB client on first use"""
        if self._eventstore_client is None:
            if self._connection_string is None:
                raise RuntimeError("Neither connection string nor client provided")
            # AsyncKurrentDBClient constructor is NOT awaitable - returns client directly
            client = AsyncClientFactory(uri=self._connection_string)
            # Must call connect() to establish the connection
            await client.connect()
            self._eventstore_client = client
        return self._eventstore_client

    async def contains_async(self, stream_id: str) -> bool:
        return await self.get_async(stream_id) is not None

    async def append_async(self, stream_id: str, events: list[EventDescriptor], expected_version: Optional[int] = None):
        client = await self._ensure_client()
        if expected_version is not None:
            expected_version = expected_version - 1
        stream_name = self._get_stream_name(stream_id)
        stream_state = StreamState.NO_STREAM if expected_version is None else expected_version
        formatted_events = []
        for e in events:
            if e.data is None:
                raise ValueError(f"Event of type '{e.type}' has no data. Events must contain a DomainEvent.")
            formatted_events.append(
                NewEvent(
                    type=e.type,
                    data=bytes(self._serializer.serialize(e.data)),
                    metadata=bytes(self._serializer.serialize(self._build_event_metadata(e.data, e.metadata))),
                )
            )
        await client.append_to_stream(stream_name=stream_name, current_version=stream_state, events=formatted_events)

    async def get_async(self, stream_id: str) -> Optional[StreamDescriptor]:
        client = await self._ensure_client()
        stream_name = self._get_stream_name(stream_id)
        metadata, metadata_version = await client.get_stream_metadata(stream_name)
        if metadata_version == StreamState.NO_STREAM:
            return None
        truncate_before = metadata.get("$tb")
        offset = 0 if truncate_before is None else truncate_before
        read_response = await client.read_stream(
            stream_name=stream_name,
            stream_position=offset,
            backwards=False,
            resolve_links=True,
            limit=1,
        )
        recorded_events = [event async for event in read_response]
        read_response = await client.read_stream(
            stream_name=stream_name,
            stream_position=offset,
            backwards=True,
            resolve_links=True,
            limit=1,
        )
        recorded_events = [event async for event in read_response]
        if not recorded_events:
            return None
        last_event = recorded_events[0]
        return StreamDescriptor(stream_id, last_event.stream_position, None, None)  # todo: esdbclient does not provide timestamps

    async def read_async(
        self,
        stream_id: str,
        read_direction: StreamReadDirection,
        offset: int,
        length: Optional[int] = None,
    ) -> list[EventRecord]:
        client = await self._ensure_client()
        stream_name = self._get_stream_name(stream_id)
        read_response = await client.read_stream(
            stream_name=stream_name,
            stream_position=offset,
            backwards=True if read_direction == StreamReadDirection.BACKWARDS else False,
            resolve_links=True,
            limit=sys.maxsize if length is None else length,
        )
        recorded_events = [event async for event in read_response]
        return [self._decode_recorded_event(stream_id, recorded_event) for recorded_event in recorded_events]

    async def observe_async(
        self,
        stream_id: Optional[str],
        consumer_group: Optional[str] = None,
        offset: Optional[int] = None,
    ) -> Observable:
        client = await self._ensure_client()
        if stream_id is None:
            raise ValueError("stream_id cannot be None")
        stream_name = self._get_stream_name(stream_id)
        subscription = None
        if consumer_group is None:
            stream_position = offset if offset is not None else 0
            subscription = await client.subscribe_to_stream(stream_name=stream_name, resolve_links=True, stream_position=stream_position)
        else:
            try:
                await client.create_subscription_to_stream(
                    group_name=consumer_group,
                    stream_name=stream_name,
                    resolve_links=True,
                    consumer_strategy="RoundRobin",
                    # Checkpoint configuration for reliable ACK delivery
                    min_checkpoint_count=1,
                    max_checkpoint_count=1,
                    # Set message timeout to 60s (default is 30s)
                    message_timeout=60.0,
                )
            except AlreadyExists:
                pass
            subscription = await client.read_subscription_to_stream(
                group_name=consumer_group,
                stream_name=stream_name,
            )
        subject = Subject()
        # Start async task to consume events
        asyncio.create_task(self._consume_events_async(stream_id, subject, subscription))

        async def stop_subscription():
            if subscription is not None:
                await subscription.stop()

        return rx.using(lambda: Disposable(lambda: asyncio.create_task(stop_subscription())), lambda s: subject)

    def _build_event_metadata(self, e: DomainEvent, additional_metadata: Optional[Any]) -> dict[str, Any]:
        module = inspect.getmodule(e)
        if module is None:
            raise ValueError(f"Cannot determine module for event type {type(e).__name__}")
        module_name = module.__name__
        type_name = type(e).__name__
        metadata = {self._metadata_type: f"{module_name}.{type_name}"}
        if additional_metadata is not None:
            if isinstance(additional_metadata, dict):
                metadata.update(additional_metadata)
            elif hasattr(additional_metadata, "__dict__"):
                metadata.update(additional_metadata.__dict__)
            else:
                raise Exception()
        return metadata

    def _decode_recorded_event(self, stream_id: str, e: RecordedEvent) -> EventRecord:
        text = e.metadata.decode()
        metadata = self._serializer.deserialize_from_text(text)
        type_qualified_name_parts = metadata[self._metadata_type].split(".")
        module_name = ".".join(type_qualified_name_parts[:-1])
        type_name = type_qualified_name_parts[-1]
        module = __import__(module_name, fromlist=[type_name])
        expected_type = getattr(module, type_name)
        text = e.data.decode()
        data = None if text is None or text.isspace() else self._serializer.deserialize_from_text(text, expected_type)
        if isinstance(data, Dict) and not isinstance(data, expected_type):
            typed_data = expected_type.__new__(expected_type)
            typed_data.__dict__ = data
            data = typed_data
        from datetime import datetime, timezone

        return EventRecord(
            stream_id=stream_id,
            id=str(e.id),
            offset=e.stream_position,
            position=e.commit_position if e.commit_position is not None else 0,
            timestamp=e.recorded_at if e.recorded_at is not None else datetime.now(timezone.utc),
            type=e.type,
            data=data,
            metadata=metadata,
        )

    def _get_stream_name(self, stream_id: str) -> str:
        """Converts the specified stream id to a qualified stream id, which is prefixed with the current database name, if any"""
        return stream_id if self._eventstore_options.database_name is None or stream_id.startswith("$ce-") else f"{self._eventstore_options.database_name}-{stream_id}"

    async def _consume_events_async(self, stream_id: str, subject: Subject, subscription):
        """
        Asynchronously enumerate events returned by a subscription using native async iteration.

        With AsyncioEventStoreDBClient, subscriptions are async generators that properly handle
        gRPC bidirectional streaming. ACKs are sent immediately without queuing issues.

        For persistent subscriptions, events are wrapped in AckableEventRecord with async
        ack/nack delegates that directly call the subscription's async methods.
        """
        # Check if this is a persistent subscription (has ack/nack methods)
        is_persistent = hasattr(subscription, "ack") and hasattr(subscription, "nack")

        try:
            e: RecordedEvent
            async for e in subscription:
                # Skip tombstone events (streams prefixed with $$)
                # Tombstones are created by EventStoreDB when streams are hard-deleted
                if e.stream_name.startswith("$$"):
                    logging.debug(f"Skipping tombstone event from stream: {e.stream_name}")
                    # Acknowledge tombstone to continue processing
                    if is_persistent:
                        # Use ack_id for resolved link events, fall back to id
                        ack_id = getattr(e, "ack_id", e.id)
                        await subscription.ack(ack_id)
                    continue

                # Skip system event types (prefixed with $)
                # System events are internal EventStoreDB metadata events
                if e.type.startswith("$"):
                    logging.debug(f"Skipping system event type '{e.type}' from stream: {e.stream_name}")
                    # Acknowledge system event to continue processing
                    if is_persistent:
                        # Use ack_id for resolved link events, fall back to id
                        ack_id = getattr(e, "ack_id", e.id)
                        await subscription.ack(ack_id)
                    continue

                try:
                    decoded_event = self._decode_recorded_event(stream_id, e)
                except Exception as ex:
                    logging.warning(f"Could not decode event with offset '{e.stream_position}' from stream '{e.stream_name}': {ex}")
                    # Acknowledge failed decode to continue processing (don't park/retry invalid events)
                    if is_persistent:
                        # Use ack_id for resolved link events, fall back to id
                        ack_id = getattr(e, "ack_id", e.id)
                        await subscription.ack(ack_id)
                    continue

                # Convert to AckableEventRecord if subscription supports ack/nack
                if is_persistent:
                    # Use ack_id for resolved link events (resolveLinktos=true), fall back to id
                    # This is critical for persistent subscriptions to category streams ($ce-*)
                    event_id = getattr(e, "ack_id", e.id)

                    async def ack_delegate(eid=event_id, sub=subscription):
                        """
                        Acknowledge event to EventStoreDB persistent subscription.

                        With async API, ACKs are sent immediately through the gRPC stream.
                        """
                        await sub.ack(eid)
                        logging.debug(f"ACK sent for event: {eid}")

                    async def nack_delegate(eid=event_id, sub=subscription, action="retry"):
                        """
                        Negative acknowledge event with specified action.

                        Actions:
                        - "retry": Retry event delivery (default)
                        - "park": Move event to parked messages
                        - "skip": Skip event without retry
                        """
                        await sub.nack(eid, action=action)
                        logging.debug(f"NACK sent for event: {eid} with action: {action}")

                    ackable_event = AckableEventRecord(
                        stream_id=decoded_event.stream_id,
                        id=decoded_event.id,
                        offset=decoded_event.offset,
                        position=decoded_event.position,
                        timestamp=decoded_event.timestamp,
                        type=decoded_event.type,
                        data=decoded_event.data,
                        metadata=decoded_event.metadata,
                        replayed=decoded_event.replayed,
                        _ack_delegate=ack_delegate,
                        _nack_delegate=nack_delegate,
                    )
                    subject.on_next(ackable_event)
                else:
                    # No ack/nack support (catchup subscription), send regular EventRecord
                    subject.on_next(decoded_event)

            subject.on_completed()
        except Exception as ex:
            logging.error(f"An exception occurred while consuming events from stream '{stream_id}': {ex}")
            await subscription.stop()

    async def delete_async(self, stream_id: str) -> None:
        """
        Delete the stream from EventStoreDB.

        Uses EventStoreDB's stream deletion which physically removes the stream.
        This operation is irreversible and should be used with caution.

        Args:
            stream_id: The identifier of the stream to delete

        Raises:
            Exception: If the stream does not exist or deletion fails
        """
        client = await self._ensure_client()
        stream_name = self._get_stream_name(stream_id)
        try:
            # Delete the stream from EventStoreDB
            await client.delete_stream(stream_name=stream_name, current_version=StreamState.ANY)
        except Exception as ex:
            raise Exception(f"Failed to delete stream '{stream_name}': {ex}") from ex

    @staticmethod
    def configure(builder: ApplicationBuilderBase, options: EventStoreOptions) -> ApplicationBuilderBase:
        """Registers and configures an EventStore implementation of the EventStore class.

        Args:
            builder: The application builder to configure
            options: EventStore configuration options
        """
        connection_string_name = "eventstore"
        connection_string = builder.settings.connection_strings.get(connection_string_name, None)
        if connection_string is None:
            raise Exception(f"Missing '{connection_string_name}' connection string")

        # Register dependencies
        builder.services.try_add_singleton(Aggregator)
        builder.services.try_add_singleton(EventStoreOptions, singleton=options)

        # Factory function to create ESEventStore with connection string
        def create_event_store(service_provider) -> ESEventStore:
            from neuroglia.serialization.json import JsonSerializer

            serializer = service_provider.get_service(JsonSerializer)
            return ESEventStore(options, connection_string, serializer)

        builder.services.try_add_singleton(EventStore, implementation_factory=create_event_store)
        return builder
