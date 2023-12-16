from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
from enum import Enum
from typing import List, Optional, Type

from neuroglia.data.abstractions import AggregateRoot, DomainEvent

class EventDescriptor:
    ''' Represents a class used to describe an event to record '''
    
    def __init__(self, type: str, data: Optional[any], metadata: Optional[any] = None):
        self.type = type
        self.data = data
        self.metadata = metadata

    type: str
    ''' Gets the type of the event to record '''
    
    data : any
    ''' Gets the data of the event to record '''
    
    metadata: any
    ''' Gets the metadata of the event to record, if any '''


class EventRecord:
    ''' Represents a recorded event '''
   
    def __init__(self, stream_id: str, id: str, offset: int, position: int, timestamp: datetime, type: str, data: Optional[any] = None, metadata: Optional[any] = None, replayed: bool = False):
        ''' Initializes a new event record '''
        self.stream_id = stream_id
        self.id = id
        self.offset = offset
        self.position = position
        self.timestamp = timestamp
        self.type = type
        self.data = data
        self.metadata = metadata
        self.replayed = replayed

    stream_id: str
    ''' Gets the id of the stream the recorded event belongs to '''
    
    id: str
    ''' Gets the id of the recorded event '''
    
    offset : int
    ''' Gets the offset of the recorded event in the stream it belongs to '''
    
    position: int
    ''' Gets the position of the recorded event in the global stream '''
    
    timestamp: datetime
    ''' Gets the date and time at which the event has been recorded '''
    
    type: str
    ''' Gets the type of the recorded event. Should be a non-versioned reverse uri made out alphanumeric, '-' and '.' characters '''
    
    data: Optional[any]
    ''' Gets the recorded event's data, if any '''
    
    metadadata: Optional[any]
    ''' Gets the recorded event's metadadata, if any '''
    
    replayed: bool
    ''' Gets a boolean indicating whether or not the recorded event is being replayed to its consumer/consumer group '''
    

class StreamReadDirection(Enum):
    ''' Enumerates all directions in which a event sourcing stream can be read '''
    FORWARDS=0,
    ''' Indicates a forwards direction '''
    BACKWARDS=1
    ''' Indicates a backwards direction ''' 

@dataclass
class EventStoreOptions:

    database_name: str
    ''' Gets/sets the name of the database to use, if any '''

class EventStore(ABC):
    ''' Defines the fundamentals of a service used to append and subscribe to sourced events '''
    
    @abstractmethod
    def append(self, streamId: str, events: List[EventDescriptor], expectedVersion: Optional[int] = None):
        ''' Appends a list of events to the specified stream '''
        raise NotImplementedError()

    @abstractmethod
    def get(self, stream_id: str):
        ''' Gets information about the specified stream '''
        raise NotImplementedError()
    
    @abstractmethod
    def read(self, stream_id: str, read_direction: StreamReadDirection, offset: int, length: Optional[int] = None) -> List[EventRecord]:
        ''' Reads recorded events from the specified stream '''
        raise NotImplementedError()

    def observe(self, stream_id: Optional[str], consumer_group: Optional[str] = None, offset: Optional[int]= None):
        ''' 
        Creates a new observable used to stream events published by the event store.
        Typically, this is used by some kind of reconciliation mechanism to consume domain events then publish them to their related handlers, if any.
        '''
        raise NotImplementedError()


class Aggregator:
        
    def aggregate(self, events: List, aggregate_type: Type):
        aggregate: AggregateRoot = object.__new__(aggregate_type)
        aggregate.state = aggregate.__orig_bases__[0].__args__[0]();
        for e in events:
            aggregate.state.on(e.data)
        return aggregate