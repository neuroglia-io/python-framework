"""Tests for Agent-to-Agent (A2A) protocol types.

Tests cover:
- TaskPriority: Priority enum for task requests
- TaskStatus: Status enum for task lifecycle
- AgentIdentity: Agent identity for A2A routing
- TaskRequest: Delegation request from source to target
- TaskResponse: Response from target to source

Coverage Target: 90%+
"""

from datetime import datetime, timezone

from neuroglia.a2a import (
    AgentIdentity,
    TaskPriority,
    TaskRequest,
    TaskResponse,
    TaskStatus,
)

# =============================================================================
# TaskPriority Tests
# =============================================================================


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_all_priorities_exist(self) -> None:
        """Test all priority levels are defined."""
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.NORMAL.value == "normal"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.CRITICAL.value == "critical"

    def test_priority_from_string(self) -> None:
        """Test creating priority from string value."""
        assert TaskPriority("low") == TaskPriority.LOW
        assert TaskPriority("normal") == TaskPriority.NORMAL
        assert TaskPriority("high") == TaskPriority.HIGH
        assert TaskPriority("critical") == TaskPriority.CRITICAL

    def test_priority_is_string_enum(self) -> None:
        """Test that TaskPriority is a string enum."""
        assert isinstance(TaskPriority.NORMAL, str)
        assert TaskPriority.HIGH == "high"


# =============================================================================
# TaskStatus Tests
# =============================================================================


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """Test all status values are defined."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.WAITING_DELEGATION.value == "waiting_delegation"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_status_from_string(self) -> None:
        """Test creating status from string value."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("completed") == TaskStatus.COMPLETED
        assert TaskStatus("failed") == TaskStatus.FAILED

    def test_status_is_string_enum(self) -> None:
        """Test that TaskStatus is a string enum."""
        assert isinstance(TaskStatus.RUNNING, str)
        assert TaskStatus.COMPLETED == "completed"


# =============================================================================
# AgentIdentity Tests
# =============================================================================


class TestAgentIdentity:
    """Tests for AgentIdentity dataclass."""

    def test_creation_personal_agent(self) -> None:
        """Test creating identity for a personal agent."""
        identity = AgentIdentity(
            agent_id="agent-123",
            agent_type="personal",
            owner_id="user-456",
        )

        assert identity.agent_id == "agent-123"
        assert identity.agent_type == "personal"
        assert identity.owner_id == "user-456"
        assert identity.team_id is None

    def test_creation_team_agent(self) -> None:
        """Test creating identity for a team agent."""
        identity = AgentIdentity(
            agent_id="agent-789",
            agent_type="team_member",
            team_id="research-team",
        )

        assert identity.agent_id == "agent-789"
        assert identity.agent_type == "team_member"
        assert identity.owner_id is None
        assert identity.team_id == "research-team"

    def test_creation_autonomous_agent(self) -> None:
        """Test creating identity for an autonomous agent."""
        identity = AgentIdentity(
            agent_id="agent-auto",
            agent_type="autonomous",
        )

        assert identity.agent_id == "agent-auto"
        assert identity.agent_type == "autonomous"
        assert identity.owner_id is None
        assert identity.team_id is None

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        identity = AgentIdentity(
            agent_id="agent-test",
            agent_type="personal",
            owner_id="user-test",
            team_id="team-test",
        )

        data = identity.to_dict()

        assert data["agent_id"] == "agent-test"
        assert data["agent_type"] == "personal"
        assert data["owner_id"] == "user-test"
        assert data["team_id"] == "team-test"

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "agent_id": "agent-xyz",
            "agent_type": "team_member",
            "owner_id": None,
            "team_id": "ops-team",
        }

        identity = AgentIdentity.from_dict(data)

        assert identity.agent_id == "agent-xyz"
        assert identity.agent_type == "team_member"
        assert identity.owner_id is None
        assert identity.team_id == "ops-team"

    def test_from_dict_with_missing_optional_fields(self) -> None:
        """Test deserialization with missing optional fields."""
        data = {
            "agent_id": "agent-min",
            "agent_type": "personal",
        }

        identity = AgentIdentity.from_dict(data)

        assert identity.agent_id == "agent-min"
        assert identity.agent_type == "personal"
        assert identity.owner_id is None
        assert identity.team_id is None

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        original = AgentIdentity(
            agent_id="agent-roundtrip",
            agent_type="personal",
            owner_id="user-roundtrip",
            team_id="team-roundtrip",
        )

        data = original.to_dict()
        restored = AgentIdentity.from_dict(data)

        assert restored.agent_id == original.agent_id
        assert restored.agent_type == original.agent_type
        assert restored.owner_id == original.owner_id
        assert restored.team_id == original.team_id


# =============================================================================
# TaskRequest Tests
# =============================================================================


class TestTaskRequest:
    """Tests for TaskRequest dataclass."""

    def test_creation_minimal(self) -> None:
        """Test creating TaskRequest with minimal fields."""
        source = AgentIdentity(
            agent_id="source-agent",
            agent_type="personal",
            owner_id="user-123",
        )

        request = TaskRequest(
            task_id="task-001",
            correlation_id="corr-001",
            source=source,
        )

        assert request.task_id == "task-001"
        assert request.correlation_id == "corr-001"
        assert request.source.agent_id == "source-agent"
        assert request.target_team_id is None
        assert request.target_agent_id is None
        assert request.required_capabilities == []
        assert request.intent == ""
        assert request.description == ""
        assert request.payload == {}
        assert request.shared_context == {}
        assert request.user_identity is None
        assert request.priority == TaskPriority.NORMAL
        assert request.timeout_seconds == 300
        assert request.max_iterations == 50
        assert request.callback_mode == "sync"
        assert request.webhook_url is None
        assert request.requested_at is None

    def test_creation_full(self) -> None:
        """Test creating TaskRequest with all fields."""
        now = datetime.now(timezone.utc)
        source = AgentIdentity(
            agent_id="personal-agent",
            agent_type="personal",
            owner_id="user-456",
        )

        request = TaskRequest(
            task_id="task-full",
            correlation_id="corr-full",
            source=source,
            target_team_id="research-team",
            target_agent_id="specific-agent",
            required_capabilities=["search", "summarize"],
            intent="analyze_document",
            description="Analyze the quarterly report for insights",
            payload={"document_id": "doc-123"},
            shared_context={"prior_analysis": []},
            user_identity={"sub": "user-456", "roles": ["analyst"]},
            priority=TaskPriority.HIGH,
            timeout_seconds=600,
            max_iterations=100,
            callback_mode="webhook",
            webhook_url="https://example.com/callback",
            requested_at=now,
        )

        assert request.task_id == "task-full"
        assert request.correlation_id == "corr-full"
        assert request.target_team_id == "research-team"
        assert request.target_agent_id == "specific-agent"
        assert request.required_capabilities == ["search", "summarize"]
        assert request.intent == "analyze_document"
        assert request.description == "Analyze the quarterly report for insights"
        assert request.payload == {"document_id": "doc-123"}
        assert request.shared_context == {"prior_analysis": []}
        assert request.user_identity == {"sub": "user-456", "roles": ["analyst"]}
        assert request.priority == TaskPriority.HIGH
        assert request.timeout_seconds == 600
        assert request.max_iterations == 100
        assert request.callback_mode == "webhook"
        assert request.webhook_url == "https://example.com/callback"
        assert request.requested_at == now

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        now = datetime.now(timezone.utc)
        source = AgentIdentity(
            agent_id="agent-serialize",
            agent_type="personal",
            owner_id="user-ser",
        )

        request = TaskRequest(
            task_id="task-ser",
            correlation_id="corr-ser",
            source=source,
            target_team_id="team-ser",
            intent="test_serialization",
            priority=TaskPriority.CRITICAL,
            requested_at=now,
        )

        data = request.to_dict()

        assert data["task_id"] == "task-ser"
        assert data["correlation_id"] == "corr-ser"
        assert data["source"]["agent_id"] == "agent-serialize"
        assert data["target_team_id"] == "team-ser"
        assert data["intent"] == "test_serialization"
        assert data["priority"] == "critical"
        assert data["requested_at"] == now.isoformat()

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "task_id": "task-deser",
            "correlation_id": "corr-deser",
            "source": {
                "agent_id": "agent-deser",
                "agent_type": "team_member",
                "team_id": "dev-team",
            },
            "target_team_id": "ops-team",
            "target_agent_id": "ops-agent-1",
            "required_capabilities": ["deploy"],
            "intent": "deploy_service",
            "description": "Deploy the new version",
            "payload": {"version": "2.0.0"},
            "shared_context": {},
            "user_identity": {"sub": "deployer"},
            "priority": "high",
            "timeout_seconds": 900,
            "max_iterations": 25,
            "callback_mode": "async",
            "webhook_url": None,
            "requested_at": now.isoformat(),
        }

        request = TaskRequest.from_dict(data)

        assert request.task_id == "task-deser"
        assert request.correlation_id == "corr-deser"
        assert request.source.agent_id == "agent-deser"
        assert request.source.agent_type == "team_member"
        assert request.target_team_id == "ops-team"
        assert request.target_agent_id == "ops-agent-1"
        assert request.required_capabilities == ["deploy"]
        assert request.intent == "deploy_service"
        assert request.description == "Deploy the new version"
        assert request.payload == {"version": "2.0.0"}
        assert request.user_identity == {"sub": "deployer"}
        assert request.priority == TaskPriority.HIGH
        assert request.timeout_seconds == 900
        assert request.max_iterations == 25
        assert request.callback_mode == "async"
        assert request.requested_at == now

    def test_from_dict_with_defaults(self) -> None:
        """Test deserialization uses defaults for missing optional fields."""
        data = {
            "task_id": "task-min",
            "correlation_id": "corr-min",
            "source": {
                "agent_id": "agent-min",
                "agent_type": "personal",
            },
        }

        request = TaskRequest.from_dict(data)

        assert request.task_id == "task-min"
        assert request.required_capabilities == []
        assert request.intent == ""
        assert request.description == ""
        assert request.payload == {}
        assert request.shared_context == {}
        assert request.priority == TaskPriority.NORMAL
        assert request.timeout_seconds == 300
        assert request.max_iterations == 50
        assert request.callback_mode == "sync"
        assert request.requested_at is None

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        now = datetime.now(timezone.utc)
        source = AgentIdentity(
            agent_id="agent-rt",
            agent_type="personal",
            owner_id="user-rt",
        )

        original = TaskRequest(
            task_id="task-rt",
            correlation_id="corr-rt",
            source=source,
            target_team_id="team-rt",
            required_capabilities=["cap-1", "cap-2"],
            intent="roundtrip_test",
            description="Testing round-trip serialization",
            payload={"key": "value"},
            shared_context={"ctx": "data"},
            priority=TaskPriority.HIGH,
            timeout_seconds=450,
            max_iterations=75,
            callback_mode="webhook",
            webhook_url="https://test.example.com",
            requested_at=now,
        )

        data = original.to_dict()
        restored = TaskRequest.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.correlation_id == original.correlation_id
        assert restored.source.agent_id == original.source.agent_id
        assert restored.target_team_id == original.target_team_id
        assert restored.required_capabilities == original.required_capabilities
        assert restored.intent == original.intent
        assert restored.description == original.description
        assert restored.payload == original.payload
        assert restored.shared_context == original.shared_context
        assert restored.priority == original.priority
        assert restored.timeout_seconds == original.timeout_seconds
        assert restored.max_iterations == original.max_iterations
        assert restored.callback_mode == original.callback_mode
        assert restored.webhook_url == original.webhook_url
        assert restored.requested_at == original.requested_at


# =============================================================================
# TaskResponse Tests
# =============================================================================


class TestTaskResponse:
    """Tests for TaskResponse dataclass."""

    def test_creation_success(self) -> None:
        """Test creating successful TaskResponse."""
        now = datetime.now(timezone.utc)
        responder = AgentIdentity(
            agent_id="team-agent-1",
            agent_type="team_member",
            team_id="research-team",
        )

        response = TaskResponse(
            task_id="task-001",
            correlation_id="corr-001",
            responder=responder,
            status=TaskStatus.COMPLETED,
            result={"insights": ["insight-1", "insight-2"]},
            iterations_used=5,
            tools_called=3,
            duration_ms=15000,
            completed_at=now,
        )

        assert response.task_id == "task-001"
        assert response.correlation_id == "corr-001"
        assert response.responder.agent_id == "team-agent-1"
        assert response.status == TaskStatus.COMPLETED
        assert response.result == {"insights": ["insight-1", "insight-2"]}
        assert response.error is None
        assert response.iterations_used == 5
        assert response.tools_called == 3
        assert response.duration_ms == 15000
        assert response.completed_at == now

    def test_creation_failure(self) -> None:
        """Test creating failed TaskResponse."""
        now = datetime.now(timezone.utc)
        responder = AgentIdentity(
            agent_id="team-agent-2",
            agent_type="team_member",
            team_id="dev-team",
        )

        response = TaskResponse(
            task_id="task-002",
            correlation_id="corr-002",
            responder=responder,
            status=TaskStatus.FAILED,
            error={"code": "TIMEOUT", "message": "Task exceeded timeout"},
            iterations_used=50,
            duration_ms=300000,
            completed_at=now,
        )

        assert response.task_id == "task-002"
        assert response.status == TaskStatus.FAILED
        assert response.result is None
        assert response.error == {"code": "TIMEOUT", "message": "Task exceeded timeout"}

    def test_is_successful(self) -> None:
        """Test is_successful() method."""
        responder = AgentIdentity(agent_id="agent", agent_type="team_member")

        # Completed = successful
        response = TaskResponse(
            task_id="t1",
            correlation_id="c1",
            responder=responder,
            status=TaskStatus.COMPLETED,
        )
        assert response.is_successful() is True

        # Other statuses = not successful
        for status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.FAILED]:
            response.status = status
            assert response.is_successful() is False

    def test_is_failed(self) -> None:
        """Test is_failed() method."""
        responder = AgentIdentity(agent_id="agent", agent_type="team_member")

        # Failed = failed
        response = TaskResponse(
            task_id="t1",
            correlation_id="c1",
            responder=responder,
            status=TaskStatus.FAILED,
        )
        assert response.is_failed() is True

        # Cancelled = failed
        response.status = TaskStatus.CANCELLED
        assert response.is_failed() is True

        # Other statuses = not failed
        for status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED]:
            response.status = status
            assert response.is_failed() is False

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        now = datetime.now(timezone.utc)
        responder = AgentIdentity(
            agent_id="agent-ser",
            agent_type="team_member",
            team_id="team-ser",
        )

        response = TaskResponse(
            task_id="task-ser",
            correlation_id="corr-ser",
            responder=responder,
            status=TaskStatus.COMPLETED,
            result={"data": "test"},
            iterations_used=10,
            tools_called=5,
            duration_ms=5000,
            completed_at=now,
        )

        data = response.to_dict()

        assert data["task_id"] == "task-ser"
        assert data["correlation_id"] == "corr-ser"
        assert data["responder"]["agent_id"] == "agent-ser"
        assert data["status"] == "completed"
        assert data["result"] == {"data": "test"}
        assert data["error"] is None
        assert data["iterations_used"] == 10
        assert data["tools_called"] == 5
        assert data["duration_ms"] == 5000
        assert data["completed_at"] == now.isoformat()

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "task_id": "task-deser",
            "correlation_id": "corr-deser",
            "responder": {
                "agent_id": "agent-deser",
                "agent_type": "team_member",
                "team_id": "team-deser",
            },
            "status": "completed",
            "result": {"response": "success"},
            "error": None,
            "iterations_used": 8,
            "tools_called": 4,
            "duration_ms": 12000,
            "completed_at": now.isoformat(),
        }

        response = TaskResponse.from_dict(data)

        assert response.task_id == "task-deser"
        assert response.correlation_id == "corr-deser"
        assert response.responder.agent_id == "agent-deser"
        assert response.status == TaskStatus.COMPLETED
        assert response.result == {"response": "success"}
        assert response.error is None
        assert response.iterations_used == 8
        assert response.tools_called == 4
        assert response.duration_ms == 12000
        assert response.completed_at == now

    def test_from_dict_with_defaults(self) -> None:
        """Test deserialization uses defaults for missing optional fields."""
        data = {
            "task_id": "task-min",
            "correlation_id": "corr-min",
            "responder": {
                "agent_id": "agent-min",
                "agent_type": "team_member",
            },
            "status": "pending",
        }

        response = TaskResponse.from_dict(data)

        assert response.task_id == "task-min"
        assert response.result is None
        assert response.error is None
        assert response.iterations_used == 0
        assert response.tools_called == 0
        assert response.duration_ms == 0
        assert response.completed_at is None

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        now = datetime.now(timezone.utc)
        responder = AgentIdentity(
            agent_id="agent-rt",
            agent_type="team_member",
            team_id="team-rt",
        )

        original = TaskResponse(
            task_id="task-rt",
            correlation_id="corr-rt",
            responder=responder,
            status=TaskStatus.COMPLETED,
            result={"complex": {"nested": [1, 2, 3]}},
            iterations_used=15,
            tools_called=7,
            duration_ms=25000,
            completed_at=now,
        )

        data = original.to_dict()
        restored = TaskResponse.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.correlation_id == original.correlation_id
        assert restored.responder.agent_id == original.responder.agent_id
        assert restored.responder.team_id == original.responder.team_id
        assert restored.status == original.status
        assert restored.result == original.result
        assert restored.iterations_used == original.iterations_used
        assert restored.tools_called == original.tools_called
        assert restored.duration_ms == original.duration_ms
        assert restored.completed_at == original.completed_at
