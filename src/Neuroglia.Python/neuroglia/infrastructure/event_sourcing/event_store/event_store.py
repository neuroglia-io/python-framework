import json
import sys
from typing import Dict, List, Optional, Type
from neuroglia.infrastructure.event_sourcing.abstractions import EventDescriptor, EventRecord, EventStore, StreamReadDirection
from neuroglia.serialization.json import JsonSerializer
from esdbclient import EventStoreDBClient, NewEvent, StreamState, RecordedEvent


class ESEventStore(EventStore):
    ''' Represents the EventStore.com implementation of the EventStore abstract class '''
    
    _eventstore_client : EventStoreDBClient = EventStoreDBClient(uri="esdb://localhost:2113?Tls=false") #todo: inject instead
    ''' Gets the service used to interact with the EventStore DB'''

    def append(self, streamId: str, events: List[EventDescriptor], expectedVersion: Optional[int] = None):
        stream_state = StreamState.NO_STREAM if expectedVersion is None else expectedVersion
        formatted_events = [NewEvent
        (
            type = e.type, 
            data = None if e.data == None else json.dumps(e.data.__dict__, default=str).encode('utf-8'), 
            metadata = json.dumps(self._build_event_metadata(type(e.data).__name__, e.metadata), default=str).encode('utf-8')
        ) 
        for e in events]
        self._eventstore_client.append_to_stream(stream_name = streamId, current_version = stream_state, events = formatted_events)

    def get(self, stream_id: str):
        raise NotImplementedError()
    
    def read(self, stream_id: str, read_direction: StreamReadDirection, offset: int, length: Optional[int] = None) -> List[EventRecord]:
        read_response = self._eventstore_client.read_stream(
            stream_name = stream_id, 
            stream_position = offset,
            backwards = True if read_direction == StreamReadDirection.BACKWARDS else False,
            resolve_links = True,
            limit = sys.maxsize if length is None else length
        )
        recorded_events = tuple(read_response)
        return [self._decode_recorded_event(stream_id, recorded_event) for recorded_event in recorded_events]

    def _build_event_metadata(self, event_data_type: Type, additional_metadata: Optional[any]):
        metadata = {'clr-type': event_data_type}
        if additional_metadata != None:
            if isinstance(additional_metadata, dict): metadata.update(additional_metadata)
            elif hasattr(additional_metadata, '__dict__'): metadata.update(additional_metadata.__dict__)
            else: raise Exception()
        return metadata

    def _decode_recorded_event(self, stream_id: str, e : RecordedEvent) -> EventRecord:
        text = e.metadata.decode('utf-8')
        metadata = None if text is None or text.isspace() else JsonSerializer.deserialize(text)
        
        expected_type = None if metadata == None else globals()[metadata['clr-type']]
        text = e.data.decode('utf-8')
        data = None if text is None or text.isspace() else JsonSerializer.deserialize(text, expected_type)
        if isinstance(data,  Dict) and not isinstance(data, expected_type):
            typed_data = expected_type.__new__(expected_type)
            typed_data.__dict__ = data
            data = typed_data
        
        return EventRecord(stream_id = stream_id, id = e.id, offset = e.stream_position, position = e.commit_position, timestamp=None, type = e.type, data = data, metadata = metadata)
    