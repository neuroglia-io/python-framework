import asyncio
from dataclasses import dataclass
from neuroglia.data.infrastructure.event_sourcing.abstractions import EventRecord, EventStore, EventStoreOptions
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.hosting.abstractions import HostedServiceBase
from neuroglia.mediation.mediator import Mediator
from neuroglia.reactive import AsyncRx

@dataclass
class ReadModelConciliationOptions:
    ''' Represents the options used to configure the application's read model reconciliation features '''
    
    consumer_group: str
    ''' Gets the name of the group of consumers the application's read model is maintained by '''


class ReadModelReconciliator(HostedServiceBase):
    ''' Represents the service used to reconciliate the read model by streaming and handling events recorded on the application's event store '''
    
    _service_provider : ServiceProviderBase
    ''' Gets the current service provider '''

    _event_store_options: EventStoreOptions
    ''' Gets the options used to configure the event store '''

    _event_store : EventStore
    ''' Gets the service used to persist and stream domain events '''
    
    def __init__(self, service_provider: ServiceProviderBase, event_store_options: EventStoreOptions, event_store : EventStore):
        self._service_provider = service_provider
        self._event_store_options = event_store_options
        self._event_store = event_store

    async def start_async(self):
        await self.subscribe_async()

    async def subscribe_async(self):
        observable = await self._event_store.observe_async(f'$ce-{self._event_store_options.database_name}')
        AsyncRx.subscribe(observable, self.on_event_record_stream_next)
        
    def on_event_record_stream_next(self, e: EventRecord):
        mediator : Mediator = self._service_provider.get_required_service(Mediator);
        try:
            #todo: migrate event
            asyncio.run( mediator.publish_async(e.data))
            #todo: ack
        except Exception as ex:
            pass #todo: nack
    
    async def on_event_record_stream_error(self, ex: Exception):
        await self.subscribe_async()

    