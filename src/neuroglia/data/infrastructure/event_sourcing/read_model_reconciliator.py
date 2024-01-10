from neuroglia.data.infrastructure.event_sourcing.abstractions import EventRecord, EventStore, EventStoreOptions
from neuroglia.hosting.abstractions import HostedServiceBase

class ReadModelConciliationOptions:
    ''' Represents the options used to configure the application's read model reconciliation features '''
    
    consumer_group: str
    ''' Gets the name of the group of consumers the application's read model is maintained by '''

class ReadModelReconciliator(HostedServiceBase):
    ''' Represents the service used to reconciliate the read model by streaming and handling events recorded on the application's event store '''
    
    _event_store_options: EventStoreOptions

    _event_store : EventStore
    ''' Gets the service used to persist and stream domain events '''
    
    def __init__(self, event_store_options: EventStoreOptions, event_store : EventStore):
        self._event_store_options = event_store_options
        self._event_store = event_store_options

    async def start_async(self):
        await self._event_store.observe_async(f'$ce-{self._event_store_options.database_name}').subscribe(
            self.on_event_record_stream_next,
            self.on_event_record_stream_error,
            self.on_event_record_stream_completed)
        
    def on_event_record_stream_next(e: EventRecord):
        pass
    
    def on_event_record_stream_error(ex: Exception):
        pass
    
    def on_event_record_stream_completed():
        pass
