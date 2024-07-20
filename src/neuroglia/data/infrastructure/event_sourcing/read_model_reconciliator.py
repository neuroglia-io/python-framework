import asyncio
from dataclasses import dataclass
import logging
from rx.core.typing import Disposable
from neuroglia.data.infrastructure.event_sourcing.abstractions import AckableEventRecord, EventRecord, EventStore, EventStoreOptions
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.hosting.abstractions import HostedService
from neuroglia.mediation.mediator import Mediator
from neuroglia.reactive import AsyncRx


@dataclass
class ReadModelConciliationOptions:
    ''' Represents the options used to configure the application's read model reconciliation features '''

    consumer_group: str
    ''' Gets the name of the group of consumers the application's read model is maintained by '''


class ReadModelReconciliator(HostedService):
    ''' Represents the service used to reconciliate the read model by streaming and handling events recorded on the application's event store '''

    _service_provider: ServiceProviderBase
    ''' Gets the current service provider '''

    _mediator: Mediator

    _event_store_options: EventStoreOptions
    ''' Gets the options used to configure the event store '''

    _event_store: EventStore
    ''' Gets the service used to persist and stream domain events '''

    _subscription: Disposable

    def __init__(self, service_provider: ServiceProviderBase, mediator: Mediator, event_store_options: EventStoreOptions, event_store: EventStore):
        self._service_provider = service_provider
        self._mediator = mediator
        self._event_store_options = event_store_options
        self._event_store = event_store

    async def start_async(self):
        await self.subscribe_async()

    async def stop_async(self):
        self._subscription.dispose()

    async def subscribe_async(self):
        observable = await self._event_store.observe_async(f'$ce-{self._event_store_options.database_name}', self._event_store_options.consumer_group)
        self._subscription = AsyncRx.subscribe(observable, lambda e: asyncio.run(self.on_event_record_stream_next_async(e)))

    async def on_event_record_stream_next_async(self, e: EventRecord):
        try:
            # todo: migrate event
            await self._mediator.publish_async(e.data)
            # todo: ack
        except Exception as ex:
            logging.error(f"An exception occured while publishing an event of type '{type(e.data).__name__}': {ex}")
            pass  # todo: nack

    async def on_event_record_stream_error(self, ex: Exception):
        await self.subscribe_async()
