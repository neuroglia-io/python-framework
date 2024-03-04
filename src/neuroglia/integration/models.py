from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

TKey = TypeVar("TKey")
''' Represents the generic argument used to specify the type of key to use '''


@dataclass
class IntegrationEvent(Generic[TKey], ABC):
    ''' Represents the base class inherited by all integration events '''

    created_at: datetime
    ''' Gets the date and time the integration event has been created at '''

    aggregate_id: TKey
    ''' Gets the id of the aggregate that has produced the integration event '''
