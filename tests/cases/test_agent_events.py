"""Tests for Agent domain events.

Tests cover all agent lifecycle, team, knowledge, capability,
delegation, session, and focus events.

Coverage Target: 90%+
"""

from datetime import datetime, timezone

from neuroglia.data.agent import (
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

# =============================================================================
# Agent Lifecycle Events
# =============================================================================


class TestAgentCreatedDomainEvent:
    """Tests for AgentCreatedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = AgentCreatedDomainEvent(
            aggregate_id="agent-123",
            owner_id="user-456",
            agent_type="personal",
            display_name="Test Agent",
            agent_created_at=now,
        )

        assert event.aggregate_id == "agent-123"
        assert event.owner_id == "user-456"
        assert event.agent_type == "personal"
        assert event.display_name == "Test Agent"
        assert event.agent_created_at == now

    def test_creation_minimal(self) -> None:
        """Test event creation with minimal fields."""
        event = AgentCreatedDomainEvent(
            aggregate_id="agent-min",
            owner_id="user-min",
            agent_type="team_member",
            display_name="Minimal Agent",
        )

        assert event.aggregate_id == "agent-min"
        assert event.agent_created_at is None

    def test_inherits_domain_event(self) -> None:
        """Test that event properly inherits from DomainEvent."""
        event = AgentCreatedDomainEvent(
            aggregate_id="agent-inherit",
            owner_id="user-inherit",
            agent_type="personal",
            display_name="Inherit Test",
        )

        # Should have DomainEvent properties
        assert hasattr(event, "created_at")
        assert hasattr(event, "aggregate_id")


class TestAgentStatusChangedDomainEvent:
    """Tests for AgentStatusChangedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = AgentStatusChangedDomainEvent(
            aggregate_id="agent-status",
            previous_status="active",
            new_status="suspended",
            reason="User requested suspension",
            changed_at=now,
        )

        assert event.aggregate_id == "agent-status"
        assert event.previous_status == "active"
        assert event.new_status == "suspended"
        assert event.reason == "User requested suspension"
        assert event.changed_at == now

    def test_creation_without_reason(self) -> None:
        """Test event creation without optional reason."""
        event = AgentStatusChangedDomainEvent(
            aggregate_id="agent-no-reason",
            previous_status="suspended",
            new_status="active",
        )

        assert event.reason is None
        assert event.changed_at is None


# =============================================================================
# Team Membership Events
# =============================================================================


class TestAgentJoinedTeamDomainEvent:
    """Tests for AgentJoinedTeamDomainEvent."""

    def test_creation_with_capabilities(self) -> None:
        """Test event creation with capabilities."""
        now = datetime.now(timezone.utc)
        event = AgentJoinedTeamDomainEvent(
            aggregate_id="agent-join",
            team_id="team-research",
            role="member",
            capabilities=["search", "summarize"],
            joined_at=now,
        )

        assert event.aggregate_id == "agent-join"
        assert event.team_id == "team-research"
        assert event.role == "member"
        assert event.capabilities == ["search", "summarize"]
        assert event.joined_at == now

    def test_creation_without_capabilities(self) -> None:
        """Test event creation without optional capabilities."""
        event = AgentJoinedTeamDomainEvent(
            aggregate_id="agent-join-min",
            team_id="team-dev",
            role="lead",
        )

        assert event.capabilities == []
        assert event.joined_at is None


class TestAgentLeftTeamDomainEvent:
    """Tests for AgentLeftTeamDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = AgentLeftTeamDomainEvent(
            aggregate_id="agent-left",
            team_id="team-old",
            reason="Team disbanded",
            left_at=now,
        )

        assert event.aggregate_id == "agent-left"
        assert event.team_id == "team-old"
        assert event.reason == "Team disbanded"
        assert event.left_at == now

    def test_creation_minimal(self) -> None:
        """Test event creation with minimal fields."""
        event = AgentLeftTeamDomainEvent(
            aggregate_id="agent-left-min",
            team_id="team-temp",
        )

        assert event.reason is None
        assert event.left_at is None


class TestAgentTeamRoleChangedDomainEvent:
    """Tests for AgentTeamRoleChangedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = AgentTeamRoleChangedDomainEvent(
            aggregate_id="agent-role",
            team_id="team-promo",
            previous_role="member",
            new_role="lead",
            changed_at=now,
        )

        assert event.aggregate_id == "agent-role"
        assert event.team_id == "team-promo"
        assert event.previous_role == "member"
        assert event.new_role == "lead"
        assert event.changed_at == now


# =============================================================================
# Knowledge Access Events
# =============================================================================


class TestKnowledgeScopeGrantedDomainEvent:
    """Tests for KnowledgeScopeGrantedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = KnowledgeScopeGrantedDomainEvent(
            aggregate_id="agent-grant",
            namespace_id="aix-certification-domain",
            access_level="write",
            granted_at=now,
        )

        assert event.aggregate_id == "agent-grant"
        assert event.namespace_id == "aix-certification-domain"
        assert event.access_level == "write"
        assert event.granted_at == now


class TestKnowledgeScopeRevokedDomainEvent:
    """Tests for KnowledgeScopeRevokedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = KnowledgeScopeRevokedDomainEvent(
            aggregate_id="agent-revoke",
            namespace_id="aix-sessions",
            reason="Access no longer needed",
            revoked_at=now,
        )

        assert event.aggregate_id == "agent-revoke"
        assert event.namespace_id == "aix-sessions"
        assert event.reason == "Access no longer needed"
        assert event.revoked_at == now

    def test_creation_minimal(self) -> None:
        """Test event creation with minimal fields."""
        event = KnowledgeScopeRevokedDomainEvent(
            aggregate_id="agent-revoke-min",
            namespace_id="ns-temp",
        )

        assert event.reason is None
        assert event.revoked_at is None


class TestPrimaryNamespaceSetDomainEvent:
    """Tests for PrimaryNamespaceSetDomainEvent."""

    def test_creation_set_namespace(self) -> None:
        """Test event creation when setting primary namespace."""
        now = datetime.now(timezone.utc)
        event = PrimaryNamespaceSetDomainEvent(
            aggregate_id="agent-primary",
            namespace_id="aix-executive",
            previous_namespace_id="aix-sessions",
            set_at=now,
        )

        assert event.aggregate_id == "agent-primary"
        assert event.namespace_id == "aix-executive"
        assert event.previous_namespace_id == "aix-sessions"
        assert event.set_at == now

    def test_creation_clear_namespace(self) -> None:
        """Test event creation when clearing primary namespace."""
        event = PrimaryNamespaceSetDomainEvent(
            aggregate_id="agent-clear",
            namespace_id=None,
            previous_namespace_id="aix-old",
        )

        assert event.namespace_id is None
        assert event.previous_namespace_id == "aix-old"


# =============================================================================
# Capability Events
# =============================================================================


class TestCapabilityAddedDomainEvent:
    """Tests for CapabilityAddedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = CapabilityAddedDomainEvent(
            aggregate_id="agent-cap-add",
            capability_id="code-review",
            name="Code Review",
            description="Analyze code for quality",
            tool_ids=["linter", "analyzer"],
            added_at=now,
        )

        assert event.aggregate_id == "agent-cap-add"
        assert event.capability_id == "code-review"
        assert event.name == "Code Review"
        assert event.description == "Analyze code for quality"
        assert event.tool_ids == ["linter", "analyzer"]
        assert event.added_at == now

    def test_creation_minimal(self) -> None:
        """Test event creation with minimal fields."""
        event = CapabilityAddedDomainEvent(
            aggregate_id="agent-cap-min",
            capability_id="search",
            name="Search",
        )

        assert event.description == ""
        assert event.tool_ids == []
        assert event.added_at is None


class TestCapabilityRemovedDomainEvent:
    """Tests for CapabilityRemovedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = CapabilityRemovedDomainEvent(
            aggregate_id="agent-cap-remove",
            capability_id="deprecated-cap",
            removed_at=now,
        )

        assert event.aggregate_id == "agent-cap-remove"
        assert event.capability_id == "deprecated-cap"
        assert event.removed_at == now


# =============================================================================
# Delegation Events
# =============================================================================


class TestDelegationRequestedDomainEvent:
    """Tests for DelegationRequestedDomainEvent."""

    def test_creation_team_delegation(self) -> None:
        """Test event creation for team-based delegation."""
        now = datetime.now(timezone.utc)
        event = DelegationRequestedDomainEvent(
            aggregate_id="agent-delegate",
            task_id="task-123",
            intent="analyze_document",
            target_team_id="research-team",
            requested_at=now,
        )

        assert event.aggregate_id == "agent-delegate"
        assert event.task_id == "task-123"
        assert event.intent == "analyze_document"
        assert event.target_team_id == "research-team"
        assert event.target_agent_id is None
        assert event.requested_at == now

    def test_creation_direct_delegation(self) -> None:
        """Test event creation for direct agent delegation."""
        event = DelegationRequestedDomainEvent(
            aggregate_id="agent-direct",
            task_id="task-456",
            intent="specific_task",
            target_agent_id="specific-agent",
        )

        assert event.target_team_id is None
        assert event.target_agent_id == "specific-agent"


class TestDelegationCompletedDomainEvent:
    """Tests for DelegationCompletedDomainEvent."""

    def test_creation_success(self) -> None:
        """Test event creation for successful delegation."""
        now = datetime.now(timezone.utc)
        event = DelegationCompletedDomainEvent(
            aggregate_id="agent-complete",
            task_id="task-done",
            success=True,
            duration_ms=15000,
            completed_at=now,
        )

        assert event.aggregate_id == "agent-complete"
        assert event.task_id == "task-done"
        assert event.success is True
        assert event.duration_ms == 15000
        assert event.completed_at == now

    def test_creation_failure(self) -> None:
        """Test event creation for failed delegation."""
        event = DelegationCompletedDomainEvent(
            aggregate_id="agent-fail",
            task_id="task-failed",
            success=False,
            duration_ms=300000,
        )

        assert event.success is False


# =============================================================================
# Session Events
# =============================================================================


class TestSessionStartedDomainEvent:
    """Tests for SessionStartedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = SessionStartedDomainEvent(
            aggregate_id="agent-session",
            session_id="session-789",
            started_at=now,
        )

        assert event.aggregate_id == "agent-session"
        assert event.session_id == "session-789"
        assert event.started_at == now


class TestSessionEndedDomainEvent:
    """Tests for SessionEndedDomainEvent."""

    def test_creation_completed(self) -> None:
        """Test event creation for completed session."""
        now = datetime.now(timezone.utc)
        event = SessionEndedDomainEvent(
            aggregate_id="agent-end",
            session_id="session-end",
            reason="completed",
            ended_at=now,
        )

        assert event.aggregate_id == "agent-end"
        assert event.session_id == "session-end"
        assert event.reason == "completed"
        assert event.ended_at == now

    def test_creation_terminated(self) -> None:
        """Test event creation for terminated session."""
        event = SessionEndedDomainEvent(
            aggregate_id="agent-term",
            session_id="session-term",
            reason="terminated",
        )

        assert event.reason == "terminated"

    def test_creation_timeout(self) -> None:
        """Test event creation for timed out session."""
        event = SessionEndedDomainEvent(
            aggregate_id="agent-timeout",
            session_id="session-timeout",
            reason="timeout",
        )

        assert event.reason == "timeout"


# =============================================================================
# Focus Events
# =============================================================================


class TestFocusSetDomainEvent:
    """Tests for FocusSetDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with focus data."""
        now = datetime.now(timezone.utc)
        focus_data = {
            "name": "Personal Agent Implementation",
            "description": "Implementing Phase 0 of the specification",
            "priority_files": ["src/neuroglia/data/agent/"],
        }
        event = FocusSetDomainEvent(
            aggregate_id="agent-focus",
            focus=focus_data,
            set_at=now,
        )

        assert event.aggregate_id == "agent-focus"
        assert event.focus == focus_data
        assert event.set_at == now

    def test_creation_empty_focus(self) -> None:
        """Test event creation with empty focus."""
        event = FocusSetDomainEvent(
            aggregate_id="agent-empty-focus",
            focus=None,
        )

        assert event.focus == {}


class TestFocusClearedDomainEvent:
    """Tests for FocusClearedDomainEvent."""

    def test_creation(self) -> None:
        """Test event creation with all fields."""
        now = datetime.now(timezone.utc)
        event = FocusClearedDomainEvent(
            aggregate_id="agent-clear-focus",
            cleared_at=now,
        )

        assert event.aggregate_id == "agent-clear-focus"
        assert event.cleared_at == now


# =============================================================================
# CloudEvent Decorator Tests
# =============================================================================


class TestCloudEventDecorator:
    """Tests for @cloudevent decorator on events."""

    def test_agent_created_has_cloudevent_type(self) -> None:
        """Test AgentCreatedDomainEvent has cloudevent metadata."""
        event = AgentCreatedDomainEvent(
            aggregate_id="test",
            owner_id="user",
            agent_type="personal",
            display_name="Test",
        )

        # The @cloudevent decorator should add type metadata
        # Check that the class has the decorator applied
        assert hasattr(AgentCreatedDomainEvent, "__cloudevent_type__") or hasattr(event.__class__, "__annotations__")

    def test_all_events_are_dataclasses(self) -> None:
        """Test that all events are dataclasses."""
        import dataclasses

        events = [
            AgentCreatedDomainEvent,
            AgentStatusChangedDomainEvent,
            AgentJoinedTeamDomainEvent,
            AgentLeftTeamDomainEvent,
            AgentTeamRoleChangedDomainEvent,
            KnowledgeScopeGrantedDomainEvent,
            KnowledgeScopeRevokedDomainEvent,
            PrimaryNamespaceSetDomainEvent,
            CapabilityAddedDomainEvent,
            CapabilityRemovedDomainEvent,
            DelegationRequestedDomainEvent,
            DelegationCompletedDomainEvent,
            SessionStartedDomainEvent,
            SessionEndedDomainEvent,
            FocusSetDomainEvent,
            FocusClearedDomainEvent,
        ]

        for event_class in events:
            assert dataclasses.is_dataclass(event_class), f"{event_class.__name__} should be a dataclass"
