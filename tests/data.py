import uuid
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Generic, Optional, TypeVar

from multipledispatch import dispatch

from neuroglia.data.abstractions import (
    AggregateRoot,
    AggregateState,
    DomainEvent,
    Identifiable,
)
from neuroglia.mediation.mediator import Command, Query, QueryHandler

T = TypeVar("T")
TKey = TypeVar("TKey")


class UserCreatedDomainEventV1(DomainEvent[str]):
    def __init__(self, aggregate_id: str, name: str, email: str):
        super().__init__(aggregate_id)
        self.name = name
        self.email = email

    name: str

    email: str


class UserEmailChangedDomainEventV1(DomainEvent[str]):
    def __init__(self, aggregate_id: str, email: str):
        super().__init__(aggregate_id)
        self.email = email

    email: str


class UserStateV1(AggregateState[str]):
    name: str

    email: str

    @dispatch(UserCreatedDomainEventV1)
    def on(self, e: UserCreatedDomainEventV1):
        self._id = e.aggregate_id
        self.created_at = e.created_at
        self.name = e.name
        self.email = e.email

    @dispatch(UserEmailChangedDomainEventV1)
    def on(self, e: UserEmailChangedDomainEventV1):
        self.last_modified = e.created_at
        self.email = e.email


class User(AggregateRoot[UserStateV1, str]):
    def __init__(self, name: str, email: Optional[str] = None):
        super().__init__()
        self.state.on(self.register_event(UserCreatedDomainEventV1(str(uuid.uuid4()).replace("-", ""), name, email)))

    def set_email(self, email: str):
        self.state.on(self.register_event(UserEmailChangedDomainEventV1(self.id, email)))


@dataclass
class UserDto(Identifiable):
    id: str

    name: str

    email: str


@dataclass
class GreetCommand(Command):
    greetings: str


class TestData:
    id: str

    name: str

    data: UserDto

    properties: dict


# Mock sample classes for tests
class PersonGender(Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


@dataclass
class AddressDto:
    street: str
    number: str
    postal_code: str
    city: str
    state: str
    country: str


@dataclass
class PersonDto(Identifiable):
    id: str
    first_name: str
    last_name: str
    nationality: str
    gender: PersonGender
    birth_date: date
    address: AddressDto


@dataclass
class GetByIdQuery(Query, Generic[T, TKey]):
    id: TKey


class GetByIdQueryHandler(QueryHandler):
    async def handle_async(self, query: GetByIdQuery) -> T:
        # Mock implementation
        pass
