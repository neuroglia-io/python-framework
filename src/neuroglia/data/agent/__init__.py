"""Agent module for Neuroglia framework.

Provides base classes and value objects for Agent aggregates
across the AIX ecosystem.

This module defines:
- BaseAgentState: Base state class for all agent aggregates
- Value Objects: TeamMembership, KnowledgeScope, AgentCapability
- Domain Events: Agent lifecycle, team, knowledge, and delegation events

Services extend BaseAgentState with domain-specific fields:
- Agent-Host adds: conversation_history, user_preferences
- Agent-Runtime adds: team_id, execution_stats

Examples:
    ```python
    from neuroglia.data.agent import (
        BaseAgentState,
        TeamMembership,
        AgentCapability,
        AgentCreatedDomainEvent,
    )

    # Extend for Personal Agent
    class PersonalAgentState(BaseAgentState):
        conversation_ids: list[str] = field(default_factory=list)

    # Create team membership
    membership = TeamMembership(
        team_id="research-team",
        role="member",
        joined_at=datetime.now(UTC),
        capabilities=["search", "summarize"]
    )
    ```

See Also:
    - A2A Protocol: neuroglia.a2a
    - Conversation Building Blocks: neuroglia.data.conversation
"""

from neuroglia.data.agent.agent_events import (
    AgentCreatedDomainEvent,
    AgentJoinedTeamDomainEvent,
    AgentLeftTeamDomainEvent,
    AgentStatusChangedDomainEvent,
    AgentTeamRoleChangedDomainEvent,
    CapabilityAddedDomainEvent,
    CapabilityRemovedDomainEvent,
    DelegationCompletedDomainEvent,
    DelegationRequestedDomainEvent,
    FocusClearedDomainEvent,
    FocusSetDomainEvent,
    KnowledgeScopeGrantedDomainEvent,
    KnowledgeScopeRevokedDomainEvent,
    PrimaryNamespaceSetDomainEvent,
    SessionEndedDomainEvent,
    SessionStartedDomainEvent,
)
from neuroglia.data.agent.agent_state import (
    AgentCapability,
    BaseAgentState,
    KnowledgeScope,
    TeamMembership,
)

__all__ = [
    # State
    "BaseAgentState",
    # Value Objects
    "TeamMembership",
    "KnowledgeScope",
    "AgentCapability",
    # Lifecycle Events
    "AgentCreatedDomainEvent",
    "AgentStatusChangedDomainEvent",
    # Team Events
    "AgentJoinedTeamDomainEvent",
    "AgentLeftTeamDomainEvent",
    "AgentTeamRoleChangedDomainEvent",
    # Knowledge Events
    "KnowledgeScopeGrantedDomainEvent",
    "KnowledgeScopeRevokedDomainEvent",
    "PrimaryNamespaceSetDomainEvent",
    # Capability Events
    "CapabilityAddedDomainEvent",
    "CapabilityRemovedDomainEvent",
    # Delegation Events
    "DelegationRequestedDomainEvent",
    "DelegationCompletedDomainEvent",
    # Session Events
    "SessionStartedDomainEvent",
    "SessionEndedDomainEvent",
    # Focus Events
    "FocusSetDomainEvent",
    "FocusClearedDomainEvent",
]
