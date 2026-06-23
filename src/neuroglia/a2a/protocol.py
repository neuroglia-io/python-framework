"""Agent-to-Agent (A2A) protocol types.

Defines the message types for inter-agent communication in the AIX
distributed agent ecosystem. Used for task delegation between:
- Personal Agents (in Agent-Host)
- Team Agents (in Agent-Runtime)

The protocol supports both synchronous and asynchronous delegation
patterns with full context sharing and result routing.

Examples:
    ```python
    from neuroglia.a2a import TaskRequest, TaskResponse, AgentIdentity

    # Create a delegation request
    source = AgentIdentity(
        agent_id="personal-agent-123",
        agent_type="personal",
        owner_id="user-456"
    )

    request = TaskRequest(
        task_id="task-789",
        correlation_id="corr-abc",
        source=source,
        target_team_id="research-team",
        intent="analyze_document",
        description="Analyze the attached document for key insights",
        payload={"document_id": "doc-xyz"}
    )
    ```

See Also:
    - Personal Agent Architecture: /docs/specs/personal-agent-architecture.md
    - Implementation Plan: /docs/specs/personal-agent-implementation-plan.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskPriority(str, Enum):
    """Priority level for A2A task requests.

    Affects queue ordering and timeout handling in Agent-Runtime.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Execution status for A2A tasks.

    Tracks the lifecycle of a delegated task from request to completion.
    """

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_DELEGATION = "waiting_delegation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentIdentity:
    """Identity of an agent in A2A communication.

    Provides the minimum information needed to identify and route
    messages to/from an agent.

    Attributes:
        agent_id: Unique identifier for the agent
        agent_type: Type of agent ("personal" | "team_member" | "autonomous")
        owner_id: ID of the owning user, if applicable
        team_id: ID of the agent's team, if applicable

    Examples:
        ```python
        # Personal agent identity
        personal = AgentIdentity(
            agent_id="agent-123",
            agent_type="personal",
            owner_id="user-456"
        )

        # Team agent identity
        team_agent = AgentIdentity(
            agent_id="agent-789",
            agent_type="team_member",
            team_id="research-team"
        )
        ```
    """

    agent_id: str
    agent_type: str
    owner_id: str | None = None
    team_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for transport."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "owner_id": self.owner_id,
            "team_id": self.team_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentIdentity":
        """Deserialize from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            agent_type=data["agent_type"],
            owner_id=data.get("owner_id"),
            team_id=data.get("team_id"),
        )


@dataclass
class TaskRequest:
    """A2A delegation request from one agent to another.

    Encapsulates all information needed for an agent to delegate
    a task to another agent or team.

    Routing:
        - Set target_team_id for capability-based routing (recommended)
        - Set target_agent_id for direct agent addressing
        - Set required_capabilities for capability matching

    Attributes:
        task_id: Unique identifier for this task
        correlation_id: ID for response routing back to requester
        source: Identity of the requesting agent
        target_team_id: Target team for capability-based routing
        target_agent_id: Target agent for direct addressing
        required_capabilities: Capabilities needed to handle this task
        intent: Short description of the task intent
        description: Detailed task description
        payload: Task-specific data
        shared_context: Context to share with the target agent
        user_identity: User context for authorization
        priority: Task priority level
        timeout_seconds: Maximum execution time
        max_iterations: Maximum ReAct iterations allowed
        callback_mode: Response mode ("sync" | "async" | "webhook")
        webhook_url: URL for webhook callback (if callback_mode="webhook")
        requested_at: Timestamp when request was created

    Examples:
        ```python
        request = TaskRequest(
            task_id="task-123",
            correlation_id="corr-456",
            source=AgentIdentity(
                agent_id="personal-agent",
                agent_type="personal",
                owner_id="user-789"
            ),
            target_team_id="research-team",
            required_capabilities=["document_analysis"],
            intent="analyze_document",
            description="Extract key insights from quarterly report",
            payload={"document_id": "doc-abc"},
            priority=TaskPriority.HIGH,
            timeout_seconds=600
        )
        ```
    """

    # Identity
    task_id: str
    correlation_id: str  # For response routing

    # Source
    source: AgentIdentity

    # Target
    target_team_id: str | None = None
    target_agent_id: str | None = None
    required_capabilities: list[str] = field(default_factory=list)

    # Task Definition
    intent: str = ""
    description: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    # Context
    shared_context: dict[str, Any] = field(default_factory=dict)
    user_identity: dict[str, Any] | None = None

    # Constraints
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_seconds: int = 300
    max_iterations: int = 50

    # Callback
    callback_mode: str = "sync"  # "sync" | "async" | "webhook"
    webhook_url: str | None = None

    # Timestamps
    requested_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for transport."""
        return {
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "source": self.source.to_dict(),
            "target_team_id": self.target_team_id,
            "target_agent_id": self.target_agent_id,
            "required_capabilities": self.required_capabilities,
            "intent": self.intent,
            "description": self.description,
            "payload": self.payload,
            "shared_context": self.shared_context,
            "user_identity": self.user_identity,
            "priority": self.priority.value,
            "timeout_seconds": self.timeout_seconds,
            "max_iterations": self.max_iterations,
            "callback_mode": self.callback_mode,
            "webhook_url": self.webhook_url,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRequest":
        """Deserialize from dictionary."""
        return cls(
            task_id=data["task_id"],
            correlation_id=data["correlation_id"],
            source=AgentIdentity.from_dict(data["source"]),
            target_team_id=data.get("target_team_id"),
            target_agent_id=data.get("target_agent_id"),
            required_capabilities=data.get("required_capabilities", []),
            intent=data.get("intent", ""),
            description=data.get("description", ""),
            payload=data.get("payload", {}),
            shared_context=data.get("shared_context", {}),
            user_identity=data.get("user_identity"),
            priority=TaskPriority(data.get("priority", "normal")),
            timeout_seconds=data.get("timeout_seconds", 300),
            max_iterations=data.get("max_iterations", 50),
            callback_mode=data.get("callback_mode", "sync"),
            webhook_url=data.get("webhook_url"),
            requested_at=(datetime.fromisoformat(data["requested_at"]) if data.get("requested_at") else None),
        )


@dataclass
class TaskResponse:
    """A2A delegation response from target agent.

    Encapsulates the result of a delegated task, including
    execution metadata for observability.

    Attributes:
        task_id: Original task identifier
        correlation_id: Original correlation ID for routing
        responder: Identity of the responding agent
        status: Final task status
        result: Task result data (if successful)
        error: Error details (if failed)
        iterations_used: Number of ReAct iterations used
        tools_called: Total number of tool calls made
        duration_ms: Total execution time in milliseconds
        completed_at: Timestamp when task completed

    Examples:
        ```python
        response = TaskResponse(
            task_id="task-123",
            correlation_id="corr-456",
            responder=AgentIdentity(
                agent_id="team-agent-789",
                agent_type="team_member",
                team_id="research-team"
            ),
            status=TaskStatus.COMPLETED,
            result={"insights": ["Key insight 1", "Key insight 2"]},
            iterations_used=5,
            tools_called=3,
            duration_ms=15000,
            completed_at=datetime.now(UTC)
        )
        ```
    """

    # Identity
    task_id: str
    correlation_id: str

    # Source (responding agent)
    responder: AgentIdentity

    # Result
    status: TaskStatus
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    # Execution Metadata
    iterations_used: int = 0
    tools_called: int = 0
    duration_ms: int = 0

    # Timestamps
    completed_at: datetime | None = None

    def is_successful(self) -> bool:
        """Check if the task completed successfully."""
        return self.status == TaskStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if the task failed."""
        return self.status in (TaskStatus.FAILED, TaskStatus.CANCELLED)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for transport."""
        return {
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "responder": self.responder.to_dict(),
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "iterations_used": self.iterations_used,
            "tools_called": self.tools_called,
            "duration_ms": self.duration_ms,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResponse":
        """Deserialize from dictionary."""
        return cls(
            task_id=data["task_id"],
            correlation_id=data["correlation_id"],
            responder=AgentIdentity.from_dict(data["responder"]),
            status=TaskStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            iterations_used=data.get("iterations_used", 0),
            tools_called=data.get("tools_called", 0),
            duration_ms=data.get("duration_ms", 0),
            completed_at=(datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None),
        )
