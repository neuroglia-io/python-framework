import asyncio
import importlib
import inspect
from typing import List, Type
from neuroglia.core import TypeFinder, ModuleLoader
from neuroglia.eventing.cloud_events import CloudEvent
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.hosting.abstractions import ApplicationBuilderBase, HostedServiceBase
from neuroglia.mediation.mediator import Mediator

class CloudEventIngestionOptions:
    ''' Represents the service used to configure how the application should ingest incoming cloud events '''
    
    type_maps : dict[str, Type] = dict[str, Type]()
    ''' Gets/sets a cloud event type/CLR type mapping of all supported cloud events'''
    

class CloudEventIngestor(HostedServiceBase):
    ''' Represents the service used to ingest cloud events '''
    
    def __init__(self, options : CloudEventIngestionOptions, cloud_event_bus: CloudEventBus, mediator : Mediator):
        self._options = options
        self._cloud_event_bus = cloud_event_bus
        self._mediator = mediator
        
    _options : CloudEventIngestionOptions

    _cloud_event_bus : CloudEventBus
    
    _mediator : Mediator
    
    async def start_async(self):
        self._cloud_event_bus.input_stream.subscribe(lambda e: asyncio.ensure_future(self._on_cloud_event_async(e)))      

    async def _on_cloud_event_async(self, cloud_event : CloudEvent):

        event_type = self._options.type_maps.get(cloud_event.type, None)
        if event_type is None: 
            print(f"Ignored incoming cloud event: the specified type '{cloud_event.type}' is not supported") #todo: remove
            return #todo: log that we ignored an incoming event
        
        e: object = None
        try:
            e = event_type(**cloud_event.data)
        except Exception as ex:
            print(f"An error occured while reading a cloud event of type '{cloud_event.type}': '{ex}'") #todo: remove
            raise
        
        print(f"Data extracted from the cloud event: {e}") #todo: remove

        try:
            await self._mediator.publish_async(e)
        except Exception as ex:
            print(f"An error occured while dispatching an incoming cloud event of type '{cloud_event.type}': '{ex}'") #todo: remove
            raise
        
    def configure(builder : ApplicationBuilderBase, modules : List[str]) -> ApplicationBuilderBase:
        ''' Registers and configures cloud event related services to the specified service collection.
            
            Args:
                services (ServiceCollection): the service collection to configure
                modules (List[str]): a list containing the names of the modules to scan for classes marked with the 'cloudevent' decorator. Marked classes as used to configure the mapping of cloud events consumed by the cloud event ingestor
        '''
        options : CloudEventIngestionOptions = CloudEventIngestionOptions()
        for module in [ModuleLoader.load(module_name) for module_name in modules]:
            for cloud_event_clr_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and hasattr(cls, "__cloudevent__")):
                cloud_event_type = cloud_event_clr_type.__cloudevent__
                options.type_maps[cloud_event_type] = cloud_event_clr_type
        builder.services.try_add_singleton(CloudEventBus)
        builder.services.add_singleton(CloudEventIngestionOptions, singleton=options)
        builder.services.add_singleton(HostedServiceBase, CloudEventIngestor)
        return builder
        