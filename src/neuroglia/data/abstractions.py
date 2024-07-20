from abc import ABC
from datetime import datetime
from typing import Generic, List, Type, TypeVar

TKey = TypeVar("TKey")
''' Represents the generic argument used to specify the type of key to use '''


class Identifiable(Generic[TKey], ABC):
    ''' Defines the fundamentals of an object that can be identified based on a unique identifier '''

    id: TKey
    ''' Gets the object's unique identifier '''


TEntity = TypeVar("TEntity", bound=Identifiable)
''' Represents the generic argument used to specify the type of entity to use '''


class Entity(Generic[TKey], Identifiable[TKey], ABC):
    ''' Represents the abstract class inherited by all entities in the application '''

    def __init__(self) -> None:
        super().__init__()
        self.created_at = datetime.now()

    created_at: datetime
    ''' Gets the date and time the entity has been created at '''

    last_modified: datetime
    ''' Gets the date and time the entity was last modified at, if any '''


class VersionedState(ABC):
    ''' Represents the abstract class inherited by all versioned states '''

    def __init__(self):
        self.state_version = 0

    state_version: int = 0
    ''' Gets the state's version '''


class AggregateState(Generic[TKey], Identifiable[TKey], VersionedState, ABC):
    ''' Represents the abstract class inherited by all aggregate root states '''

    def __init__(self):
        super().__init__()

    id: TKey
    ''' Gets the id of the aggregate the state belongs to '''

    created_at: datetime
    ''' Gets the date and time the aggregate has been created at '''

    last_modified: datetime
    ''' Gets the date and time, if any, the aggregate was last modified at '''


TState = TypeVar("TState", bound=AggregateState)
''' Represents the generic argument used to specify the state of an aggregate root '''


class DomainEvent(Generic[TKey], ABC):
    ''' Represents the base class inherited by all domain events '''

    def __init__(self, aggregate_id: TKey):
        ''' Initializes a new domain event '''
        self.created_at = datetime.now()
        self.aggregate_id = aggregate_id

    created_at: datetime
    ''' Gets the date and time the domain event has been created at '''

    aggregate_id: TKey
    ''' Gets the id of the aggregate that has produced the domain event '''

    aggregate_version: int
    ''' Gets the version of the aggregate's state, after reducing the domain event '''


TEvent = TypeVar("TEvent", bound=DomainEvent)
''' Represents the generic argument used to specify the state of an aggregate root '''


class AggregateRoot(Generic[TState, TKey], Entity[TKey], ABC):
    ''' Represents the base class for all aggregate roots '''

    _pending_events: List[DomainEvent]
    ''' Gets a list containing all domain events pending persistence '''

    def __init__(self):
        ''' Initializes a new aggregate root '''
        self.state = object.__new__(self.__orig_bases__[0].__args__[0])
        self.state.__init__()
        self._pending_events = list[DomainEvent]()

    def id(self):
        ''' Gets the aggregate root's id '''
        return self.state.id

    state: TState
    ''' Gets the aggregate root's state '''

    def register_event(self, e: TEvent) -> TEvent:
        ''' Registers the specified domain event '''
        if not hasattr(self, "_pending_events"):
            self._pending_events = list[DomainEvent]()
        self._pending_events.append(e)
        e.aggregate_version = self.state.state_version + len(self._pending_events)
        return e

    def clear_pending_events(self):
        ''' Clears all pending domain events '''
        self._pending_events.clear()


TAggregate = TypeVar("TAggregate", bound=AggregateRoot)
''' Represents the generic argument used to specify an aggregate root type '''


def queryable(cls):
    cls.__queryable__ = True
    return cls
