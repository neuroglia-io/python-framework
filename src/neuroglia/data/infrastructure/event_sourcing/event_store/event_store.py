import inspect
import json
import sys
import threading
from typing import Callable, Dict, List, Optional
from neuroglia.data.abstractions import DomainEvent
from neuroglia.data.infrastructure.event_sourcing.abstractions import EventDescriptor, EventRecord, EventStore, EventStoreOptions, StreamDescriptor, StreamReadDirection
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.serialization.json import JsonSerializer
from esdbclient import EventStoreDBClient, NewEvent, StreamState, RecordedEvent
from esdbclient.exceptions import AlreadyExists
from rx import Observable
from rx.subject import Subject


class ESEventStore(EventStore):
    ''' Represents the EventStore.com implementation of the EventStore abstract class '''
    
    _metadata_type = 'type'
    ''' Gets the name of the metadata attribute used to store the qualified name of the recorded event's type ('{module_name}.{type_name}')  '''

    _default_encoding = 'utf-8'
    ''' Gets the default encoding used to write and read event data '''

    _eventstore_client : EventStoreDBClient
    ''' Gets the service used to interact with the EventStore DB'''
    
    _options : EventStoreOptions
    
    def __init__(self, options: EventStoreOptions, eventstore_client : EventStoreDBClient):
        self._options = options
        self._eventstore_client = eventstore_client

    async def contains_async(self, stream_id: str) -> bool: return await self.get_async(stream_id) != None

    async def append_async(self, stream_id: str, events: List[EventDescriptor], expectedVersion: Optional[int] = None):
        stream_name = self._get_stream_name(stream_id)
        stream_state = StreamState.NO_STREAM if expectedVersion is None else expectedVersion
        formatted_events = [NewEvent
        (
            type = e.type, 
            data = None if e.data == None else json.dumps(e.data.__dict__, default=str).encode(self._default_encoding), 
            metadata = json.dumps(self._build_event_metadata(e.data, e.metadata), default=str).encode(self._default_encoding)
        ) 
        for e in events]
        self._eventstore_client.append_to_stream(stream_name = stream_name, current_version = stream_state, events = formatted_events)

    async def get_async(self, stream_id: str) -> Optional[StreamDescriptor] :
        stream_name = self._get_stream_name(stream_id)
        metadata, metadata_version = self._eventstore_client.get_stream_metadata(stream_name)
        if metadata_version == StreamState.NO_STREAM: return None        
        truncate_before = metadata.get('$tb')
        offset = 0 if truncate_before is None else truncate_before
        read_response = self._eventstore_client.read_stream(
            stream_name = stream_name, 
            stream_position = offset,
            backwards = False,
            resolve_links = True,
            limit = 1
        )
        recorded_events = tuple(read_response)
        first_event = recorded_events[0]
        read_response = self._eventstore_client.read_stream(
            stream_name = stream_name, 
            stream_position = offset,
            backwards = True,
            resolve_links = True,
            limit = 1
        )
        recorded_events = tuple(read_response)
        last_event = recorded_events[0]
        return StreamDescriptor(stream_id, last_event.stream_position, None, None) #todo: esdbclient does not provide timestamps
    
    async def read_async(self, stream_id: str, read_direction: StreamReadDirection, offset: int, length: Optional[int] = None) -> List[EventRecord]:
        stream_name = self._get_stream_name(stream_id)
        read_response = self._eventstore_client.read_stream(
            stream_name = stream_name, 
            stream_position = offset,
            backwards = True if read_direction == StreamReadDirection.BACKWARDS else False,
            resolve_links = True,
            limit = sys.maxsize if length is None else length
        )
        recorded_events = tuple(read_response)
        return [self._decode_recorded_event(stream_id, recorded_event) for recorded_event in recorded_events]

    async def observe_async(self, stream_id: Optional[str], consumer_group: Optional[str]= None, offset: Optional[int]= None) -> Observable:
        stream_name = self._get_stream_name(stream_id)
        subscription = None
        if consumer_group is None: 
            subscription = self._eventstore_client.subscribe_to_stream(stream_name = stream_name, resolve_links = True, stream_position = offset )
        else:
            try : self._eventstore_client.create_subscription_to_stream(stream_name = stream_name, resolve_links = True ) #todo: persistence
            except AlreadyExists: pass
        subject = Subject()
        thread = threading.Thread(target=self._consume_events_async, kwargs={ 'subject': subject, 'subscription': subscription }) #todo: replace by fire and forget async-like task
        thread.start()
        return subject
        
    def _build_event_metadata(self, e: DomainEvent, additional_metadata: Optional[any]):
        module_name = inspect.getmodule(e).__name__
        type_name = type(e).__name__
        metadata = {self._metadata_type: f'{module_name}.{type_name}'}
        if additional_metadata != None:
            if isinstance(additional_metadata, dict): metadata.update(additional_metadata)
            elif hasattr(additional_metadata, '__dict__'): metadata.update(additional_metadata.__dict__)
            else: raise Exception()
        return metadata

    def _decode_recorded_event(self, stream_id: str, e : RecordedEvent) -> EventRecord:
        text = e.metadata.decode(self._default_encoding)
        metadata = JsonSerializer.deserialize(text)
        type_qualified_name_parts = metadata[self._metadata_type].split('.')
        module_name = '.'.join(type_qualified_name_parts[:-1])
        type_name = type_qualified_name_parts[-1]
        module = __import__(module_name, fromlist=[type_name])
        expected_type = getattr(module, type_name)
        text = e.data.decode(self._default_encoding)
        data = None if text is None or text.isspace() else JsonSerializer.deserialize(text, expected_type)
        if isinstance(data,  Dict) and not isinstance(data, expected_type):
            typed_data = expected_type.__new__(expected_type)
            typed_data.__dict__ = data
            data = typed_data
        return EventRecord(stream_id = stream_id, id = e.id, offset = e.stream_position, position = e.commit_position, timestamp=None, type = e.type, data = data, metadata = metadata)
    
    def _get_stream_name(self, stream_id: str) -> str: stream_id if self._options.database_name is None or stream_id.startswith('$ce-') else f'{self._options.database_name}-{stream_id}'
    ''' Converts the specified stream id to a qualified stream id, which is prefixed with the current database name, if any '''
    
    def _consume_events_async(self, subject: Subject, subscription):
        ''' Asynchronously enumerate events returned by a subscription '''
        for e in subscription: subject.on_next(e)
        subject.on_completed()  
             
    def configure(builder : ApplicationBuilderBase, options : EventStoreOptions) -> ApplicationBuilderBase:
        ''' Registers and configures an EventStore implementation of the EventStore class.
            
            Args:
                services (ServiceCollection): the service collection to configure
        '''
        connection_string_name = "eventstore"
        connection_string = builder.settings.connection_strings.get(connection_string_name, None)
        if connection_string is None: raise Exception(f"Missing '{connection_string_name}' connection string")
        builder.services.try_add_singleton(EventStoreOptions, singleton=options)
        builder.services.try_add_singleton(EventStoreDBClient, EventStoreDBClient(uri=connection_string))        
        builder.services.try_add_singleton(EventStore, ESEventStore)
        return builder