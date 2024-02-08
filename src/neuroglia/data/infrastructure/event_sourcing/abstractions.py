from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Type
from neuroglia.data.abstractions import AggregateRoot


@dataclass
class StreamDescriptor:
    ''' Represents a class used to describe a stream of recorded events '''

    id: str
    ''' Gets the stream's id '''

    length: int
    ''' Gets the stream's length '''

    first_event_at: Optional[datetime] = None
    ''' Gets the date and time at which the first event, if any, has been recorded to the stream '''

    last_event_at: Optional[datetime] = None
    ''' Gets the date and time at which the last event, if any, has been recorded to the stream '''


@dataclass
class EventDescriptor:
    ''' Represents a class used to describe an event to record '''

    type: str
    ''' Gets the type of the event to record '''

    data: Optional[Any] = None
    ''' Gets the data of the event to record '''

    metadata: Optional[Any] = None
    ''' Gets the metadata of the event to record, if any '''


@dataclass
class EventRecord:
    ''' Represents a recorded event '''

    stream_id: str
    ''' Gets the id of the stream the recorded event belongs to '''

    id: str
    ''' Gets the id of the recorded event '''

    offset: int
    ''' Gets the offset of the recorded event in the stream it belongs to '''

    position: int
    ''' Gets the position of the recorded event in the global stream '''

    timestamp: datetime
    ''' Gets the date and time at which the event has been recorded '''

    type: str
    ''' Gets the type of the recorded event. Should be a non-versioned reverse uri made out alphanumeric, '-' and '.' characters '''

    data: Optional[any] = None
    ''' Gets the recorded event's data, if any '''

    metadata: Optional[any] = None
    ''' Gets the recorded event's metadadata, if any '''

    replayed: bool = False
    ''' Gets a boolean indicating whether or not the recorded event is being replayed to its consumer/consumer group '''


class StreamReadDirection(Enum):
    ''' Enumerates all directions in which a event sourcing stream can be read '''
    FORWARDS = 0,
    ''' Indicates a forwards direction '''
    BACKWARDS = 1
    ''' Indicates a backwards direction '''


@dataclass
class EventStoreOptions:

    database_name: str
    ''' Gets/sets the name of the database to use, if any '''


class EventStore(ABC):
    ''' Defines the fundamentals of a service used to append and subscribe to sourced events '''

    @abstractmethod
    async def contains_async(self, stream_id: str) -> bool:
        ''' Determines whether or not the event store contains a stream with the specified id '''
        raise NotImplementedError()

    @abstractmethod
    async def append_async(self, streamId: str, events: List[EventDescriptor], expectedVersion: Optional[int] = None):
        ''' Appends a list of events to the specified stream '''
        raise NotImplementedError()

    @abstractmethod
    async def get_async(self, stream_id: str):
        ''' Gets information about the specified stream '''
        raise NotImplementedError()

    @abstractmethod
    async def read_async(self, stream_id: str, read_direction: StreamReadDirection, offset: int, length: Optional[int] = None) -> List[EventRecord]:
        ''' Reads recorded events from the specified stream '''
        raise NotImplementedError()

    async def observe_async(self, stream_id: Optional[str], consumer_group: Optional[str] = None, offset: Optional[int] = None):
        ''' 
        Creates a new observable used to stream events published by the event store.
        Typically, this is used by some kind of reconciliation mechanism to consume domain events then publish them to their related handlers, if any.
        '''
        raise NotImplementedError()


class Aggregator:

    def aggregate(self, events: List, aggregate_type: Type):
        aggregate: AggregateRoot = object.__new__(aggregate_type)
        aggregate.state = aggregate.__orig_bases__[0].__args__[0]()
        for e in events:
            aggregate.state.on(e.data)
            aggregate.state.state_version = e.data.aggregate_version
        return aggregate
