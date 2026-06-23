"""Agent domain events.

Domain events emitted by Agent aggregates to capture state changes.
These events are used for:
- Event sourcing (rebuilding state)
- Projections (updating read models)
- Integration events (notifying other services via CloudEvents)

All events use the @cloudevent decorator for CloudEvents v1.0
compatibility and cross-service communication.

See Also:
    - Agent State: neuroglia.data.agent.agent_state
    - CloudEvents: neuroglia.eventing.cloud_events
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent

# =============================================================================
# AGENT LIFECYCLE EVENTS
# =============================================================================


@cloudevent("agent.created.v1")
@dataclass
class AgentCreatedDomainEvent(DomainEvent[str]):
    """Emitted when a new agent is created.

    Marks the beginning of an agent's lifecycle.

    Attributes:
        aggregate_id: Unique identifier for the agent
        owner_id: ID of the owning user (for personal agents)
        agent_type: Type of agent ("personal" | "team_member" | "autonomous")
        display_name: Human-readable name for the agent
        agent_created_at: Timestamp when the agent was created (distinct from event created_at)
    """

    aggregate_id: str = ""
    owner_id: str = ""
    agent_type: str = ""
    display_name: str = ""
    agent_created_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        owner_id: str,
        agent_type: str,
        display_name: str,
        agent_created_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.owner_id = owner_id
        self.agent_type = agent_type
        self.display_name = display_name
        self.agent_created_at = agent_created_at


@cloudevent("agent.status.changed.v1")
@dataclass
class AgentStatusChangedDomainEvent(DomainEvent[str]):
    """Emitted when an agent's status transitions.

    Tracks lifecycle state changes (active, suspended, archived).

    Attributes:
        aggregate_id: Unique identifier for the agent
        previous_status: Status before the change
        new_status: Status after the change
        reason: Optional reason for the status change
        changed_at: Timestamp of the change
    """

    aggregate_id: str = ""
    previous_status: str = ""
    new_status: str = ""
    reason: str | None = None
    changed_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        previous_status: str,
        new_status: str,
        reason: str | None = None,
        changed_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.previous_status = previous_status
        self.new_status = new_status
        self.reason = reason
        self.changed_at = changed_at


# =============================================================================
# TEAM MEMBERSHIP EVENTS
# =============================================================================


@cloudevent("agent.team.joined.v1")
@dataclass
class AgentJoinedTeamDomainEvent(DomainEvent[str]):
    """Emitted when an agent joins a team.

    Attributes:
        aggregate_id: Unique identifier for the agent
        team_id: ID of the team joined
        role: Role in the team ("member" | "lead" | "observer")
        capabilities: Capabilities granted within this team
        joined_at: Timestamp when the agent joined
    """

    aggregate_id: str = ""
    team_id: str = ""
    role: str = ""
    capabilities: list[str] = field(default_factory=list)
    joined_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        team_id: str,
        role: str,
        capabilities: list[str] | None = None,
        joined_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.team_id = team_id
        self.role = role
        self.capabilities = capabilities or []
        self.joined_at = joined_at


@cloudevent("agent.team.left.v1")
@dataclass
class AgentLeftTeamDomainEvent(DomainEvent[str]):
    """Emitted when an agent leaves a team.

    Attributes:
        aggregate_id: Unique identifier for the agent
        team_id: ID of the team left
        reason: Optional reason for leaving
        left_at: Timestamp when the agent left
    """

    aggregate_id: str = ""
    team_id: str = ""
    reason: str | None = None
    left_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        team_id: str,
        reason: str | None = None,
        left_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.team_id = team_id
        self.reason = reason
        self.left_at = left_at


@cloudevent("agent.team.role.changed.v1")
@dataclass
class AgentTeamRoleChangedDomainEvent(DomainEvent[str]):
    """Emitted when an agent's role in a team changes.

    Attributes:
        aggregate_id: Unique identifier for the agent
        team_id: ID of the team
        previous_role: Previous role in the team
        new_role: New role in the team
        changed_at: Timestamp of the change
    """

    aggregate_id: str = ""
    team_id: str = ""
    previous_role: str = ""
    new_role: str = ""
    changed_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        team_id: str,
        previous_role: str,
        new_role: str,
        changed_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.team_id = team_id
        self.previous_role = previous_role
        self.new_role = new_role
        self.changed_at = changed_at


# =============================================================================
# KNOWLEDGE ACCESS EVENTS
# =============================================================================


@cloudevent("agent.knowledge.scope.granted.v1")
@dataclass
class KnowledgeScopeGrantedDomainEvent(DomainEvent[str]):
    """Emitted when an agent is granted access to a knowledge namespace.

    Attributes:
        aggregate_id: Unique identifier for the agent
        namespace_id: ID of the knowledge namespace
        access_level: Level of access granted ("read" | "write" | "admin")
        granted_at: Timestamp when access was granted
    """

    aggregate_id: str = ""
    namespace_id: str = ""
    access_level: str = ""
    granted_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        namespace_id: str,
        access_level: str,
        granted_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.namespace_id = namespace_id
        self.access_level = access_level
        self.granted_at = granted_at


@cloudevent("agent.knowledge.scope.revoked.v1")
@dataclass
class KnowledgeScopeRevokedDomainEvent(DomainEvent[str]):
    """Emitted when an agent's access to a knowledge namespace is revoked.

    Attributes:
        aggregate_id: Unique identifier for the agent
        namespace_id: ID of the knowledge namespace
        reason: Optional reason for revocation
        revoked_at: Timestamp when access was revoked
    """

    aggregate_id: str = ""
    namespace_id: str = ""
    reason: str | None = None
    revoked_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        namespace_id: str,
        reason: str | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.namespace_id = namespace_id
        self.reason = reason
        self.revoked_at = revoked_at


@cloudevent("agent.primary.namespace.set.v1")
@dataclass
class PrimaryNamespaceSetDomainEvent(DomainEvent[str]):
    """Emitted when an agent's primary knowledge namespace is set.

    Attributes:
        aggregate_id: Unique identifier for the agent
        namespace_id: ID of the primary namespace (None to clear)
        previous_namespace_id: Previous primary namespace, if any
        set_at: Timestamp when the primary namespace was set
    """

    aggregate_id: str = ""
    namespace_id: str | None = None
    previous_namespace_id: str | None = None
    set_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        namespace_id: str | None,
        previous_namespace_id: str | None = None,
        set_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.namespace_id = namespace_id
        self.previous_namespace_id = previous_namespace_id
        self.set_at = set_at


# =============================================================================
# CAPABILITY EVENTS
# =============================================================================


@cloudevent("agent.capability.added.v1")
@dataclass
class CapabilityAddedDomainEvent(DomainEvent[str]):
    """Emitted when a capability is added to an agent.

    Attributes:
        aggregate_id: Unique identifier for the agent
        capability_id: ID of the capability
        name: Name of the capability
        description: Description of the capability
        tool_ids: Tools that implement this capability
        added_at: Timestamp when the capability was added
    """

    aggregate_id: str = ""
    capability_id: str = ""
    name: str = ""
    description: str = ""
    tool_ids: list[str] = field(default_factory=list)
    added_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        capability_id: str,
        name: str,
        description: str = "",
        tool_ids: list[str] | None = None,
        added_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.capability_id = capability_id
        self.name = name
        self.description = description
        self.tool_ids = tool_ids or []
        self.added_at = added_at


@cloudevent("agent.capability.removed.v1")
@dataclass
class CapabilityRemovedDomainEvent(DomainEvent[str]):
    """Emitted when a capability is removed from an agent.

    Attributes:
        aggregate_id: Unique identifier for the agent
        capability_id: ID of the capability removed
        removed_at: Timestamp when the capability was removed
    """

    aggregate_id: str = ""
    capability_id: str = ""
    removed_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        capability_id: str,
        removed_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.capability_id = capability_id
        self.removed_at = removed_at


# =============================================================================
# DELEGATION EVENTS
# =============================================================================


@cloudevent("agent.delegation.requested.v1")
@dataclass
class DelegationRequestedDomainEvent(DomainEvent[str]):
    """Emitted when an agent requests delegation to another agent/team.

    Attributes:
        aggregate_id: Unique identifier for the requesting agent
        task_id: ID of the delegated task
        target_team_id: ID of the target team, if any
        target_agent_id: ID of the target agent, if any
        intent: Intent/purpose of the delegation
        requested_at: Timestamp when delegation was requested
    """

    aggregate_id: str = ""
    task_id: str = ""
    target_team_id: str | None = None
    target_agent_id: str | None = None
    intent: str = ""
    requested_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        task_id: str,
        intent: str,
        target_team_id: str | None = None,
        target_agent_id: str | None = None,
        requested_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.task_id = task_id
        self.intent = intent
        self.target_team_id = target_team_id
        self.target_agent_id = target_agent_id
        self.requested_at = requested_at


@cloudevent("agent.delegation.completed.v1")
@dataclass
class DelegationCompletedDomainEvent(DomainEvent[str]):
    """Emitted when a delegation task completes.

    Attributes:
        aggregate_id: Unique identifier for the requesting agent
        task_id: ID of the completed task
        success: Whether the delegation was successful
        duration_ms: Total duration in milliseconds
        completed_at: Timestamp when delegation completed
    """

    aggregate_id: str = ""
    task_id: str = ""
    success: bool = False
    duration_ms: int = 0
    completed_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        task_id: str,
        success: bool,
        duration_ms: int = 0,
        completed_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.task_id = task_id
        self.success = success
        self.duration_ms = duration_ms
        self.completed_at = completed_at


# =============================================================================
# SESSION EVENTS
# =============================================================================


@cloudevent("agent.session.started.v1")
@dataclass
class SessionStartedDomainEvent(DomainEvent[str]):
    """Emitted when an agent starts a new session.

    Attributes:
        aggregate_id: Unique identifier for the agent
        session_id: ID of the new session
        started_at: Timestamp when the session started
    """

    aggregate_id: str = ""
    session_id: str = ""
    started_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        session_id: str,
        started_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.session_id = session_id
        self.started_at = started_at


@cloudevent("agent.session.ended.v1")
@dataclass
class SessionEndedDomainEvent(DomainEvent[str]):
    """Emitted when an agent's session ends.

    Attributes:
        aggregate_id: Unique identifier for the agent
        session_id: ID of the ended session
        reason: Reason for session end ("completed" | "timeout" | "terminated")
        ended_at: Timestamp when the session ended
    """

    aggregate_id: str = ""
    session_id: str = ""
    reason: str = ""
    ended_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        session_id: str,
        reason: str = "completed",
        ended_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.session_id = session_id
        self.reason = reason
        self.ended_at = ended_at


# =============================================================================
# FOCUS EVENTS
# =============================================================================


@cloudevent("agent.focus.set.v1")
@dataclass
class FocusSetDomainEvent(DomainEvent[str]):
    """Emitted when an agent's current focus is set or updated.

    Attributes:
        aggregate_id: Unique identifier for the agent
        focus: Focus context dictionary
        set_at: Timestamp when focus was set
    """

    aggregate_id: str = ""
    focus: dict[str, Any] = field(default_factory=dict)
    set_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        focus: dict[str, Any] | None = None,
        set_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.focus = focus or {}
        self.set_at = set_at


@cloudevent("agent.focus.cleared.v1")
@dataclass
class FocusClearedDomainEvent(DomainEvent[str]):
    """Emitted when an agent's current focus is cleared.

    Attributes:
        aggregate_id: Unique identifier for the agent
        cleared_at: Timestamp when focus was cleared
    """

    aggregate_id: str = ""
    cleared_at: datetime | None = None

    def __init__(
        self,
        aggregate_id: str,
        cleared_at: datetime | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.cleared_at = cleared_at
