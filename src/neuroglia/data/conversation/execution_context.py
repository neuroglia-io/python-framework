"""Execution context for agent loops.

Captures the state needed to suspend/resume agent execution,
supporting ReAct loops and client action requests.

Architecture:
    This is a VALUE OBJECT that can be embedded in different aggregates:
    - Agent-Host: Conversation.execution_state
    - Agent-Runtime: AgentTask.execution_context

Examples:
    ```python
    from neuroglia.data.conversation import ExecutionContext, LlmMessageSnapshot

    # Create execution context
    context = ExecutionContext(
        max_iterations=50,
        timeout_seconds=300
    )

    # Add message to snapshot
    context.message_snapshot.append(
        LlmMessageSnapshot(role="user", content="Hello")
    )

    # Check if can continue
    if context.can_continue():
        context.iteration += 1
        # ... execute next step
    ```
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LlmMessageSnapshot:
    """Snapshot of an LLM message for execution state preservation.

    Lightweight representation for storing in ExecutionContext.
    Used when suspending/resuming agent execution.

    Attributes:
        role: Message role (system, user, assistant, tool)
        content: Text content of the message
        tool_calls: Tool calls in provider-agnostic format
        tool_call_id: ID for tool response messages
        name: Tool name for tool responses
    """

    role: str
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None  # For tool response messages
    name: str | None = None  # Tool name for tool responses

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LlmMessageSnapshot":
        """Deserialize from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            tool_calls=data.get("tool_calls", []),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
        )

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI chat format for LLM calls."""
        msg: dict[str, Any] = {"role": self.role, "content": self.content}

        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        if self.name:
            msg["name"] = self.name

        return msg


@dataclass
class ExecutionContext:
    """Execution context for agent loops (ReAct, etc.).

    Captures the state needed to suspend/resume agent execution.
    Used by both Agent-Host (in Conversation) and Agent-Runtime (in AgentTask).

    This is a VALUE OBJECT that can be embedded in different aggregates.

    Attributes:
        message_snapshot: Conversation snapshot for LLM (lightweight format)
        iteration: Current iteration number
        max_iterations: Maximum allowed iterations
        tools_called: Total number of tool calls made
        pending_tool_call: Serialized ToolCall awaiting client action
        suspended_at: Timestamp when execution was suspended
        suspension_reason: Reason for suspension
        started_at: Timestamp when execution started
        timeout_seconds: Maximum execution time in seconds

    Examples:
        ```python
        context = ExecutionContext(
            max_iterations=50,
            timeout_seconds=300,
            started_at=datetime.now(UTC)
        )

        # Check limits
        if context.can_continue():
            context.iteration += 1
            # ... execute step

        # Suspend for client action
        context.suspended_at = datetime.now(UTC)
        context.suspension_reason = "client_confirmation_required"
        context.pending_tool_call = tool_call.to_dict()
        ```
    """

    # Conversation snapshot for LLM (lightweight format)
    message_snapshot: list[LlmMessageSnapshot] = field(default_factory=list)

    # Execution progress
    iteration: int = 0
    max_iterations: int = 50
    tools_called: int = 0

    # Suspension state (for client action requests)
    pending_tool_call: dict[str, Any] | None = None  # Serialized ToolCall
    suspended_at: datetime | None = None
    suspension_reason: str | None = None

    # Timing
    started_at: datetime | None = None
    timeout_seconds: int = 300

    def is_suspended(self) -> bool:
        """Check if execution is currently suspended."""
        return self.suspended_at is not None

    def can_continue(self) -> bool:
        """Check if execution can continue (not at limits)."""
        return self.iteration < self.max_iterations

    def is_timed_out(self) -> bool:
        """Check if execution has exceeded timeout."""
        if self.started_at is None:
            return False
        from datetime import timezone

        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        name: str | None = None,
    ) -> None:
        """Add a message to the snapshot.

        Args:
            role: Message role (system, user, assistant, tool)
            content: Text content
            tool_calls: Tool calls (for assistant messages)
            tool_call_id: Tool call ID (for tool messages)
            name: Tool name (for tool messages)
        """
        self.message_snapshot.append(
            LlmMessageSnapshot(
                role=role,
                content=content,
                tool_calls=tool_calls or [],
                tool_call_id=tool_call_id,
                name=name,
            )
        )

    def get_messages_for_llm(self) -> list[dict[str, Any]]:
        """Get messages in OpenAI-compatible format for LLM calls."""
        return [msg.to_openai_format() for msg in self.message_snapshot]

    def suspend(self, reason: str, pending_tool_call: dict[str, Any] | None = None) -> None:
        """Suspend execution for client action.

        Args:
            reason: Reason for suspension
            pending_tool_call: Tool call awaiting client response
        """
        from datetime import timezone

        self.suspended_at = datetime.now(timezone.utc)
        self.suspension_reason = reason
        self.pending_tool_call = pending_tool_call

    def resume(self) -> None:
        """Resume execution after suspension."""
        self.suspended_at = None
        self.suspension_reason = None
        self.pending_tool_call = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "message_snapshot": [m.to_dict() for m in self.message_snapshot],
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "tools_called": self.tools_called,
            "pending_tool_call": self.pending_tool_call,
            "suspended_at": self.suspended_at.isoformat() if self.suspended_at else None,
            "suspension_reason": self.suspension_reason,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionContext":
        """Deserialize from dictionary."""
        return cls(
            message_snapshot=[LlmMessageSnapshot.from_dict(m) for m in data.get("message_snapshot", [])],
            iteration=data.get("iteration", 0),
            max_iterations=data.get("max_iterations", 50),
            tools_called=data.get("tools_called", 0),
            pending_tool_call=data.get("pending_tool_call"),
            suspended_at=(datetime.fromisoformat(data["suspended_at"]) if data.get("suspended_at") else None),
            suspension_reason=data.get("suspension_reason"),
            started_at=(datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None),
            timeout_seconds=data.get("timeout_seconds", 300),
        )
