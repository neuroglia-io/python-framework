"""
Data infrastructure implementations for Neuroglia.

Provides concrete implementations for various data storage backends.
"""

# Import what's available - some may be optional dependencies
try:
    from .mongo import MongoQueryProvider, MongoRepository

    __all__ = ["MongoRepository", "MongoQueryProvider"]
except ImportError:
    __all__ = []

try:
    from .memory import MemoryRepository

    __all__.append("MemoryRepository")
except ImportError:
    pass

try:
    from .event_sourcing import (
        AggregateRoot,
        EventSourcingRepository,
        EventStore,
        EventStream,
        Snapshot,
    )

    __all__.extend(["EventStore", "EventSourcingRepository", "AggregateRoot", "Snapshot", "EventStream"])
except ImportError:
    pass

try:
    from .filesystem import FileSystemRepository

    __all__.append("FileSystemRepository")
except ImportError:
    pass

# Tracing mixin - optional OpenTelemetry support
try:
    from .tracing_mixin import TracedRepositoryMixin

    __all__.append("TracedRepositoryMixin")
except ImportError:
    pass
