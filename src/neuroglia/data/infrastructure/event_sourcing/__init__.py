"""
Event sourcing infrastructure for Neuroglia.

Provides event store implementations and aggregate root support.
"""

from .abstractions import (
    Aggregator,
    EventDescriptor,
    EventRecord,
    EventStore,
    EventStoreOptions,
    StreamDescriptor,
    StreamReadDirection,
)
from .event_sourcing_repository import EventSourcingRepository
from .read_model_reconciliator import (
    ReadModelConciliationOptions,
    ReadModelReconciliator,
)

__all__ = [
    "EventStore",
    "EventSourcingRepository",
    "EventRecord",
    "EventDescriptor",
    "StreamDescriptor",
    "StreamReadDirection",
    "EventStoreOptions",
    "Aggregator",
    "ReadModelConciliationOptions",
    "ReadModelReconciliator",
]
