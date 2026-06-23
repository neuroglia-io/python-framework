"""Tests for Agent state management and value objects.

Tests cover:
- BaseAgentState: Core agent state with lifecycle, membership, and delegation
- TeamMembership: Team membership value object
- KnowledgeScope: Knowledge namespace access value object
- AgentCapability: Agent capability value object

Coverage Target: 90%+
"""

from datetime import datetime, timezone
from typing import Any

from neuroglia.data.agent import (
    AgentCapability,
    BaseAgentState,
    KnowledgeScope,
    TeamMembership,
)

# =============================================================================
# TeamMembership Tests
# =============================================================================


class TestTeamMembership:
    """Tests for TeamMembership value object."""

    def test_creation_with_all_fields(self) -> None:
        """Test creating TeamMembership with all fields."""
        now = datetime.now(timezone.utc)
        membership = TeamMembership(
            team_id="team-research",
            role="member",
            joined_at=now,
            capabilities=["search", "summarize"],
        )

        assert membership.team_id == "team-research"
        assert membership.role == "member"
        assert membership.joined_at == now
        assert membership.capabilities == ["search", "summarize"]

    def test_creation_with_defaults(self) -> None:
        """Test creating TeamMembership with default capabilities."""
        now = datetime.now(timezone.utc)
        membership = TeamMembership(
            team_id="team-dev",
            role="lead",
            joined_at=now,
        )

        assert membership.capabilities == []

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        now = datetime.now(timezone.utc)
        membership = TeamMembership(
            team_id="team-ops",
            role="observer",
            joined_at=now,
            capabilities=["monitor"],
        )

        data = membership.to_dict()

        assert data["team_id"] == "team-ops"
        assert data["role"] == "observer"
        assert data["joined_at"] == now.isoformat()
        assert data["capabilities"] == ["monitor"]

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "team_id": "team-qa",
            "role": "member",
            "joined_at": now.isoformat(),
            "capabilities": ["test", "validate"],
        }

        membership = TeamMembership.from_dict(data)

        assert membership.team_id == "team-qa"
        assert membership.role == "member"
        assert membership.joined_at == now
        assert membership.capabilities == ["test", "validate"]

    def test_from_dict_with_missing_capabilities(self) -> None:
        """Test deserialization with missing optional fields."""
        now = datetime.now(timezone.utc)
        data = {
            "team_id": "team-security",
            "role": "lead",
            "joined_at": now.isoformat(),
        }

        membership = TeamMembership.from_dict(data)

        assert membership.capabilities == []

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        now = datetime.now(timezone.utc)
        original = TeamMembership(
            team_id="team-infra",
            role="member",
            joined_at=now,
            capabilities=["deploy", "scale", "monitor"],
        )

        data = original.to_dict()
        restored = TeamMembership.from_dict(data)

        assert restored.team_id == original.team_id
        assert restored.role == original.role
        assert restored.joined_at == original.joined_at
        assert restored.capabilities == original.capabilities


# =============================================================================
# KnowledgeScope Tests
# =============================================================================


class TestKnowledgeScope:
    """Tests for KnowledgeScope value object."""

    def test_creation(self) -> None:
        """Test creating KnowledgeScope."""
        now = datetime.now(timezone.utc)
        scope = KnowledgeScope(
            namespace_id="aix-certification-domain",
            access_level="write",
            granted_at=now,
        )

        assert scope.namespace_id == "aix-certification-domain"
        assert scope.access_level == "write"
        assert scope.granted_at == now

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        now = datetime.now(timezone.utc)
        scope = KnowledgeScope(
            namespace_id="aix-executive",
            access_level="read",
            granted_at=now,
        )

        data = scope.to_dict()

        assert data["namespace_id"] == "aix-executive"
        assert data["access_level"] == "read"
        assert data["granted_at"] == now.isoformat()

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "namespace_id": "aix-sessions",
            "access_level": "admin",
            "granted_at": now.isoformat(),
        }

        scope = KnowledgeScope.from_dict(data)

        assert scope.namespace_id == "aix-sessions"
        assert scope.access_level == "admin"
        assert scope.granted_at == now

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        now = datetime.now(timezone.utc)
        original = KnowledgeScope(
            namespace_id="shared-knowledge",
            access_level="write",
            granted_at=now,
        )

        data = original.to_dict()
        restored = KnowledgeScope.from_dict(data)

        assert restored.namespace_id == original.namespace_id
        assert restored.access_level == original.access_level
        assert restored.granted_at == original.granted_at


# =============================================================================
# AgentCapability Tests
# =============================================================================


class TestAgentCapability:
    """Tests for AgentCapability value object."""

    def test_creation_with_all_fields(self) -> None:
        """Test creating AgentCapability with all fields."""
        capability = AgentCapability(
            capability_id="code-review",
            name="Code Review",
            description="Analyze code for quality and best practices",
            tool_ids=["static-analyzer", "linter"],
        )

        assert capability.capability_id == "code-review"
        assert capability.name == "Code Review"
        assert capability.description == "Analyze code for quality and best practices"
        assert capability.tool_ids == ["static-analyzer", "linter"]

    def test_creation_with_defaults(self) -> None:
        """Test creating AgentCapability with default tool_ids."""
        capability = AgentCapability(
            capability_id="summarize",
            name="Summarize",
            description="Summarize documents and conversations",
        )

        assert capability.tool_ids == []

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        capability = AgentCapability(
            capability_id="search",
            name="Search",
            description="Search across knowledge bases",
            tool_ids=["vector-search", "keyword-search"],
        )

        data = capability.to_dict()

        assert data["capability_id"] == "search"
        assert data["name"] == "Search"
        assert data["description"] == "Search across knowledge bases"
        assert data["tool_ids"] == ["vector-search", "keyword-search"]

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "capability_id": "translate",
            "name": "Translate",
            "description": "Translate text between languages",
            "tool_ids": ["deepl", "google-translate"],
        }

        capability = AgentCapability.from_dict(data)

        assert capability.capability_id == "translate"
        assert capability.name == "Translate"
        assert capability.description == "Translate text between languages"
        assert capability.tool_ids == ["deepl", "google-translate"]

    def test_from_dict_with_missing_tool_ids(self) -> None:
        """Test deserialization with missing optional fields."""
        data = {
            "capability_id": "analyze",
            "name": "Analyze",
            "description": "Analyze data patterns",
        }

        capability = AgentCapability.from_dict(data)

        assert capability.tool_ids == []

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        original = AgentCapability(
            capability_id="deploy",
            name="Deploy",
            description="Deploy applications to infrastructure",
            tool_ids=["kubectl", "terraform", "ansible"],
        )

        data = original.to_dict()
        restored = AgentCapability.from_dict(data)

        assert restored.capability_id == original.capability_id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.tool_ids == original.tool_ids


# =============================================================================
# BaseAgentState Tests
# =============================================================================


class TestBaseAgentState:
    """Tests for BaseAgentState aggregate state."""

    def test_initialization(self) -> None:
        """Test default initialization."""
        state = BaseAgentState()

        assert state.id == ""
        assert state.agent_type == ""
        assert state.display_name == ""
        assert state.owner_id == ""
        assert state.status == "active"
        assert state.team_memberships == []
        assert state.knowledge_scopes == []
        assert state.capabilities == []
        assert state.preferences == {}
        assert state.learned_patterns == []
        assert state.active_delegations == []
        assert state.delegation_history == []
        assert state.primary_namespace is None
        assert state.active_session_id is None
        assert state.current_focus is None
        assert state.last_active_at is not None

    def test_is_active(self) -> None:
        """Test is_active() method."""
        state = BaseAgentState()
        assert state.is_active() is True

        state.status = "suspended"
        assert state.is_active() is False

        state.status = "archived"
        assert state.is_active() is False

    def test_is_member_of_team(self) -> None:
        """Test is_member_of_team() method."""
        now = datetime.now(timezone.utc)
        state = BaseAgentState()
        state.team_memberships = [
            TeamMembership(team_id="team-a", role="member", joined_at=now),
            TeamMembership(team_id="team-b", role="lead", joined_at=now),
        ]

        assert state.is_member_of_team("team-a") is True
        assert state.is_member_of_team("team-b") is True
        assert state.is_member_of_team("team-c") is False

    def test_has_knowledge_access(self) -> None:
        """Test has_knowledge_access() method."""
        now = datetime.now(timezone.utc)
        state = BaseAgentState()
        state.knowledge_scopes = [
            KnowledgeScope(namespace_id="ns-1", access_level="read", granted_at=now),
            KnowledgeScope(namespace_id="ns-2", access_level="write", granted_at=now),
        ]

        assert state.has_knowledge_access("ns-1") is True
        assert state.has_knowledge_access("ns-2") is True
        assert state.has_knowledge_access("ns-3") is False

    def test_has_capability(self) -> None:
        """Test has_capability() method."""
        state = BaseAgentState()
        state.capabilities = [
            AgentCapability(capability_id="search", name="Search", description="Search"),
            AgentCapability(capability_id="summarize", name="Summarize", description="Summarize"),
        ]

        assert state.has_capability("search") is True
        assert state.has_capability("summarize") is True
        assert state.has_capability("translate") is False

    def test_get_team_role(self) -> None:
        """Test get_team_role() method."""
        now = datetime.now(timezone.utc)
        state = BaseAgentState()
        state.team_memberships = [
            TeamMembership(team_id="team-a", role="member", joined_at=now),
            TeamMembership(team_id="team-b", role="lead", joined_at=now),
        ]

        assert state.get_team_role("team-a") == "member"
        assert state.get_team_role("team-b") == "lead"
        assert state.get_team_role("team-c") is None

    def test_get_knowledge_access_level(self) -> None:
        """Test get_knowledge_access_level() method."""
        now = datetime.now(timezone.utc)
        state = BaseAgentState()
        state.knowledge_scopes = [
            KnowledgeScope(namespace_id="ns-1", access_level="read", granted_at=now),
            KnowledgeScope(namespace_id="ns-2", access_level="admin", granted_at=now),
        ]

        assert state.get_knowledge_access_level("ns-1") == "read"
        assert state.get_knowledge_access_level("ns-2") == "admin"
        assert state.get_knowledge_access_level("ns-3") is None

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        now = datetime.now(timezone.utc)
        state = BaseAgentState()
        state.id = "agent-123"
        state.agent_type = "personal"
        state.display_name = "Test Agent"
        state.owner_id = "user-456"
        state.primary_namespace = "aix-sessions"
        state.status = "active"
        state.team_memberships = [
            TeamMembership(team_id="team-a", role="member", joined_at=now),
        ]
        state.knowledge_scopes = [
            KnowledgeScope(namespace_id="ns-1", access_level="write", granted_at=now),
        ]
        state.capabilities = [
            AgentCapability(capability_id="search", name="Search", description="Search"),
        ]
        state.active_session_id = "session-789"
        state.current_focus = {"name": "Test Focus", "description": "Testing"}
        state.preferences = {"theme": "dark"}
        state.learned_patterns = [{"pattern": "test"}]
        state.active_delegations = ["task-1"]
        state.delegation_history = [{"task_id": "task-0", "completed": True}]

        data = state.to_dict()

        assert data["id"] == "agent-123"
        assert data["agent_type"] == "personal"
        assert data["display_name"] == "Test Agent"
        assert data["owner_id"] == "user-456"
        assert data["primary_namespace"] == "aix-sessions"
        assert data["status"] == "active"
        assert len(data["team_memberships"]) == 1
        assert len(data["knowledge_scopes"]) == 1
        assert len(data["capabilities"]) == 1
        assert data["active_session_id"] == "session-789"
        assert data["current_focus"] == {"name": "Test Focus", "description": "Testing"}
        assert data["preferences"] == {"theme": "dark"}
        assert data["learned_patterns"] == [{"pattern": "test"}]
        assert data["active_delegations"] == ["task-1"]
        assert data["delegation_history"] == [{"task_id": "task-0", "completed": True}]
        assert "state_version" in data
        assert "created_at" in data
        assert "last_active_at" in data

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "id": "agent-abc",
            "agent_type": "team_member",
            "display_name": "Team Agent",
            "owner_id": "system",
            "team_memberships": [
                {
                    "team_id": "team-x",
                    "role": "lead",
                    "joined_at": now.isoformat(),
                    "capabilities": ["manage"],
                }
            ],
            "knowledge_scopes": [
                {
                    "namespace_id": "ns-shared",
                    "access_level": "read",
                    "granted_at": now.isoformat(),
                }
            ],
            "primary_namespace": "ns-shared",
            "capabilities": [
                {
                    "capability_id": "coordinate",
                    "name": "Coordinate",
                    "description": "Coordinate team activities",
                    "tool_ids": ["scheduler"],
                }
            ],
            "active_session_id": "session-xyz",
            "current_focus": {"task": "coordination"},
            "preferences": {"notifications": True},
            "learned_patterns": [{"context": "meeting"}],
            "active_delegations": ["task-a", "task-b"],
            "delegation_history": [],
            "status": "active",
            "created_at": now.isoformat(),
            "last_active_at": now.isoformat(),
            "state_version": 5,
        }

        state = BaseAgentState.from_dict(data)

        assert state.id == "agent-abc"
        assert state.agent_type == "team_member"
        assert state.display_name == "Team Agent"
        assert state.owner_id == "system"
        assert len(state.team_memberships) == 1
        assert state.team_memberships[0].team_id == "team-x"
        assert state.team_memberships[0].role == "lead"
        assert len(state.knowledge_scopes) == 1
        assert state.knowledge_scopes[0].namespace_id == "ns-shared"
        assert state.primary_namespace == "ns-shared"
        assert len(state.capabilities) == 1
        assert state.capabilities[0].capability_id == "coordinate"
        assert state.active_session_id == "session-xyz"
        assert state.current_focus == {"task": "coordination"}
        assert state.preferences == {"notifications": True}
        assert state.active_delegations == ["task-a", "task-b"]
        assert state.status == "active"
        assert state.state_version == 5
        assert state.created_at == now
        assert state.last_active_at == now

    def test_from_dict_with_minimal_data(self) -> None:
        """Test deserialization with minimal data (defaults)."""
        data: dict[str, Any] = {}

        state = BaseAgentState.from_dict(data)

        assert state.id == ""
        assert state.agent_type == ""
        assert state.display_name == ""
        assert state.owner_id == ""
        assert state.team_memberships == []
        assert state.knowledge_scopes == []
        assert state.capabilities == []
        assert state.status == "active"
        assert state.state_version == 0

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        now = datetime.now(timezone.utc)
        original = BaseAgentState()
        original.id = "agent-roundtrip"
        original.agent_type = "personal"
        original.display_name = "Roundtrip Agent"
        original.owner_id = "user-test"
        original.team_memberships = [
            TeamMembership(team_id="team-test", role="member", joined_at=now),
        ]
        original.knowledge_scopes = [
            KnowledgeScope(namespace_id="ns-test", access_level="write", granted_at=now),
        ]
        original.capabilities = [
            AgentCapability(
                capability_id="test-cap",
                name="Test",
                description="Test capability",
                tool_ids=["tool-1"],
            ),
        ]
        original.status = "active"
        original.primary_namespace = "ns-test"
        original.active_session_id = "session-test"
        original.current_focus = {"focus": "testing"}
        original.preferences = {"key": "value"}
        original.learned_patterns = [{"p": 1}]
        original.active_delegations = ["del-1"]
        original.delegation_history = [{"d": 1}]

        data = original.to_dict()
        restored = BaseAgentState.from_dict(data)

        assert restored.id == original.id
        assert restored.agent_type == original.agent_type
        assert restored.display_name == original.display_name
        assert restored.owner_id == original.owner_id
        assert len(restored.team_memberships) == len(original.team_memberships)
        assert len(restored.knowledge_scopes) == len(original.knowledge_scopes)
        assert len(restored.capabilities) == len(original.capabilities)
        assert restored.status == original.status
        assert restored.primary_namespace == original.primary_namespace
        assert restored.active_session_id == original.active_session_id
        assert restored.current_focus == original.current_focus
        assert restored.preferences == original.preferences
        assert restored.learned_patterns == original.learned_patterns
        assert restored.active_delegations == original.active_delegations
        assert restored.delegation_history == original.delegation_history


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestAgentStateEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_team_memberships_query(self) -> None:
        """Test querying empty team memberships."""
        state = BaseAgentState()
        assert state.is_member_of_team("any-team") is False
        assert state.get_team_role("any-team") is None

    def test_empty_knowledge_scopes_query(self) -> None:
        """Test querying empty knowledge scopes."""
        state = BaseAgentState()
        assert state.has_knowledge_access("any-namespace") is False
        assert state.get_knowledge_access_level("any-namespace") is None

    def test_empty_capabilities_query(self) -> None:
        """Test querying empty capabilities."""
        state = BaseAgentState()
        assert state.has_capability("any-capability") is False

    def test_multiple_team_memberships_same_check(self) -> None:
        """Test is_member_of_team with multiple memberships."""
        now = datetime.now(timezone.utc)
        state = BaseAgentState()
        state.team_memberships = [
            TeamMembership(team_id="team-a", role="member", joined_at=now),
            TeamMembership(team_id="team-b", role="lead", joined_at=now),
            TeamMembership(team_id="team-c", role="observer", joined_at=now),
        ]

        # All should be found
        assert state.is_member_of_team("team-a") is True
        assert state.is_member_of_team("team-b") is True
        assert state.is_member_of_team("team-c") is True
        # Non-existent should not
        assert state.is_member_of_team("team-d") is False
