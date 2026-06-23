"""
Data access layer for Neuroglia.

Provides domain modeling, repository patterns, queryable data access,
agent building blocks, and conversation value objects.
"""

# Domain abstractions
from .abstractions import (
    AggregateRoot,
    AggregateState,
    DomainEvent,
    Entity,
    Identifiable,
    VersionedState,
)

# Agent module (new in 0.9.0)
from .agent import AgentCapability, BaseAgentState, KnowledgeScope, TeamMembership

# Conversation building blocks (new in 0.9.0)
from .conversation import (
    ExecutionContext,
    LlmMessageSnapshot,
    Message,
    MessageRole,
    MessageStatus,
    Session,
    ToolCall,
    ToolResult,
)

# Exceptions
from .exceptions import (
    DataAccessException,
    EntityNotFoundException,
    OptimisticConcurrencyException,
)

# Repository patterns
from .infrastructure.abstractions import (
    FlexibleRepository,
    QueryableRepository,
    Repository,
)
from .queryable import Queryable, QueryProvider

# Import resource-oriented architecture components (deferred to avoid circular imports)
# from . import resources

__all__ = [
    # Queryable data access
    "Queryable",
    "QueryProvider",
    # Domain abstractions
    "Entity",
    "AggregateRoot",
    "DomainEvent",
    "Identifiable",
    "VersionedState",
    "AggregateState",
    # Repository patterns
    "Repository",
    "QueryableRepository",
    "FlexibleRepository",
    # Exceptions
    "DataAccessException",
    "OptimisticConcurrencyException",
    "EntityNotFoundException",
    # Agent module (new in 0.9.0)
    "BaseAgentState",
    "TeamMembership",
    "KnowledgeScope",
    "AgentCapability",
    # Conversation building blocks (new in 0.9.0)
    "Message",
    "MessageRole",
    "MessageStatus",
    "ToolCall",
    "ToolResult",
    "ExecutionContext",
    "LlmMessageSnapshot",
    "Session",
    # Resource-oriented architecture (commented out to avoid circular imports)
    # "resources"
]
