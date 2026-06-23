"""Agent state management and value objects.

Provides base classes and value objects for Agent aggregates
across the AIX ecosystem. Services extend BaseAgentState with
domain-specific fields.

Architecture:
    - Agent-Host extends with: conversation_history, user_preferences
    - Agent-Runtime extends with: team_id, execution_stats
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from neuroglia.data.abstractions import AggregateState


@dataclass
class TeamMembership:
    """Value object representing team membership.

    Captures the relationship between an agent and a team,
    including role and granted capabilities within that team.

    Attributes:
        team_id: Unique identifier of the team
        role: Membership role ("member" | "lead" | "observer")
        joined_at: Timestamp when the agent joined the team
        capabilities: List of capability IDs granted within this team

    Examples:
        ```python
        membership = TeamMembership(
            team_id="team-research",
            role="member",
            joined_at=datetime.now(UTC),
            capabilities=["search", "summarize"]
        )
        ```
    """

    team_id: str
    role: str  # "member" | "lead" | "observer"
    joined_at: datetime
    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "team_id": self.team_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat(),
            "capabilities": self.capabilities,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TeamMembership":
        """Deserialize from dictionary."""
        return cls(
            team_id=data["team_id"],
            role=data["role"],
            joined_at=datetime.fromisoformat(data["joined_at"]),
            capabilities=data.get("capabilities", []),
        )


@dataclass
class KnowledgeScope:
    """Value object representing knowledge namespace access.

    Defines the level of access an agent has to a specific
    knowledge namespace in the Knowledge Manager.

    Attributes:
        namespace_id: Unique identifier of the knowledge namespace
        access_level: Access level ("read" | "write" | "admin")
        granted_at: Timestamp when access was granted

    Examples:
        ```python
        scope = KnowledgeScope(
            namespace_id="aix-certification-domain",
            access_level="write",
            granted_at=datetime.now(UTC)
        )
        ```
    """

    namespace_id: str
    access_level: str  # "read" | "write" | "admin"
    granted_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "namespace_id": self.namespace_id,
            "access_level": self.access_level,
            "granted_at": self.granted_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeScope":
        """Deserialize from dictionary."""
        return cls(
            namespace_id=data["namespace_id"],
            access_level=data["access_level"],
            granted_at=datetime.fromisoformat(data["granted_at"]),
        )


@dataclass
class AgentCapability:
    """Value object representing an agent capability.

    A capability is a named set of skills/tools that an agent
    can perform. Used for capability-based routing in A2A delegation.

    Attributes:
        capability_id: Unique identifier for the capability
        name: Human-readable name
        description: Detailed description of what the capability enables
        tool_ids: List of tool IDs that implement this capability

    Examples:
        ```python
        capability = AgentCapability(
            capability_id="code-review",
            name="Code Review",
            description="Analyze code for quality, security, and best practices",
            tool_ids=["static-analyzer", "security-scanner"]
        )
        ```
    """

    capability_id: str
    name: str
    description: str
    tool_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "tool_ids": self.tool_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCapability":
        """Deserialize from dictionary."""
        return cls(
            capability_id=data["capability_id"],
            name=data["name"],
            description=data["description"],
            tool_ids=data.get("tool_ids", []),
        )


@dataclass
class BaseAgentState(AggregateState[str]):
    """Base state for all Agent aggregates.

    Provides the core identity, ownership, and context that both
    Personal Agents and Team Agents share. Services extend this
    with domain-specific fields.

    Domain Extensions:
        - Agent-Host adds: conversation_history, user_preferences
        - Agent-Runtime adds: team_id, execution_stats

    Attributes:
        id: Unique identifier for the agent
        agent_type: Type of agent ("personal" | "team_member" | "autonomous")
        display_name: Human-readable name for the agent
        owner_id: User ID (for personal) or system (for team)
        team_memberships: List of teams the agent belongs to
        knowledge_scopes: List of knowledge namespaces the agent can access
        primary_namespace: Default knowledge namespace for this agent
        capabilities: List of capabilities the agent can perform
        active_session_id: Currently active session, if any
        current_focus: Current work focus context
        preferences: Agent preferences and settings
        learned_patterns: Patterns learned from interactions
        active_delegations: IDs of currently active delegation tasks
        delegation_history: History of delegation requests
        status: Agent lifecycle status ("active" | "suspended" | "archived")
        created_at: Timestamp when agent was created
        last_active_at: Timestamp of last activity

    Examples:
        ```python
        class PersonalAgentState(BaseAgentState):
            '''Agent-Host specific state.'''
            conversation_ids: list[str] = field(default_factory=list)
            user_preferences: dict[str, Any] = field(default_factory=dict)

            def __init__(self):
                super().__init__()
                self.conversation_ids = []
                self.user_preferences = {}

        class TeamAgentState(BaseAgentState):
            '''Agent-Runtime specific state.'''
            team_id: str = ""
            execution_stats: dict[str, int] = field(default_factory=dict)

            def __init__(self):
                super().__init__()
                self.team_id = ""
                self.execution_stats = {}
        ```

    See Also:
        - Personal Agent Architecture: /docs/specs/personal-agent-architecture.md
        - A2A Protocol: neuroglia.a2a.protocol
    """

    # Identity
    id: str = ""
    agent_type: str = ""  # "personal" | "team_member" | "autonomous"
    display_name: str = ""

    # Ownership
    owner_id: str = ""  # User ID (for personal) or system (for team)

    # Team Membership
    team_memberships: list[TeamMembership] = field(default_factory=list)

    # Knowledge Context
    knowledge_scopes: list[KnowledgeScope] = field(default_factory=list)
    primary_namespace: str | None = None

    # Capabilities
    capabilities: list[AgentCapability] = field(default_factory=list)

    # Current Context
    active_session_id: str | None = None
    current_focus: dict[str, Any] | None = None

    # Memory
    preferences: dict[str, Any] = field(default_factory=dict)
    learned_patterns: list[dict[str, Any]] = field(default_factory=list)

    # Delegation State
    active_delegations: list[str] = field(default_factory=list)  # Task IDs
    delegation_history: list[dict[str, Any]] = field(default_factory=list)

    # Lifecycle
    status: str = "active"  # "active" | "suspended" | "archived"
    # Note: created_at is inherited from AggregateState
    last_active_at: datetime | None = None

    def __init__(self) -> None:
        """Initialize BaseAgentState with default values."""
        super().__init__()
        self.team_memberships = []
        self.knowledge_scopes = []
        self.capabilities = []
        self.preferences = {}
        self.learned_patterns = []
        self.active_delegations = []
        self.delegation_history = []
        # Set last_active_at (created_at is set by AggregateState)
        self.last_active_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Check if the agent is in active status."""
        return self.status == "active"

    def is_member_of_team(self, team_id: str) -> bool:
        """Check if the agent is a member of a specific team."""
        return any(m.team_id == team_id for m in self.team_memberships)

    def has_knowledge_access(self, namespace_id: str) -> bool:
        """Check if the agent has any access to a knowledge namespace."""
        return any(s.namespace_id == namespace_id for s in self.knowledge_scopes)

    def has_capability(self, capability_id: str) -> bool:
        """Check if the agent has a specific capability."""
        return any(c.capability_id == capability_id for c in self.capabilities)

    def get_team_role(self, team_id: str) -> str | None:
        """Get the agent's role in a specific team."""
        for membership in self.team_memberships:
            if membership.team_id == team_id:
                return membership.role
        return None

    def get_knowledge_access_level(self, namespace_id: str) -> str | None:
        """Get the agent's access level for a knowledge namespace."""
        for scope in self.knowledge_scopes:
            if scope.namespace_id == namespace_id:
                return scope.access_level
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary for persistence."""
        return {
            "id": self.id,
            "agent_type": self.agent_type,
            "display_name": self.display_name,
            "owner_id": self.owner_id,
            "team_memberships": [m.to_dict() for m in self.team_memberships],
            "knowledge_scopes": [s.to_dict() for s in self.knowledge_scopes],
            "primary_namespace": self.primary_namespace,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "active_session_id": self.active_session_id,
            "current_focus": self.current_focus,
            "preferences": self.preferences,
            "learned_patterns": self.learned_patterns,
            "active_delegations": self.active_delegations,
            "delegation_history": self.delegation_history,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "state_version": self.state_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseAgentState":
        """Deserialize state from dictionary."""
        state = cls()
        state.id = data.get("id", "")
        state.agent_type = data.get("agent_type", "")
        state.display_name = data.get("display_name", "")
        state.owner_id = data.get("owner_id", "")
        state.team_memberships = [TeamMembership.from_dict(m) for m in data.get("team_memberships", [])]
        state.knowledge_scopes = [KnowledgeScope.from_dict(s) for s in data.get("knowledge_scopes", [])]
        state.primary_namespace = data.get("primary_namespace")
        state.capabilities = [AgentCapability.from_dict(c) for c in data.get("capabilities", [])]
        state.active_session_id = data.get("active_session_id")
        state.current_focus = data.get("current_focus")
        state.preferences = data.get("preferences", {})
        state.learned_patterns = data.get("learned_patterns", [])
        state.active_delegations = data.get("active_delegations", [])
        state.delegation_history = data.get("delegation_history", [])
        state.status = data.get("status", "active")
        # Override created_at if provided (base class sets it in __init__)
        if data.get("created_at"):
            state.created_at = datetime.fromisoformat(data["created_at"])
        state.last_active_at = datetime.fromisoformat(data["last_active_at"]) if data.get("last_active_at") else None
        state.state_version = data.get("state_version", 0)
        return state
