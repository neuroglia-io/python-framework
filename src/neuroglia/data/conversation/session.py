"""Session value object for agent lifecycle.

Represents a single interaction session within an agent's lifecycle.
Multiple sessions can belong to one Agent (Personal or Team).

Architecture:
    - In Agent-Host: Wraps a Conversation
    - In Agent-Runtime: Wraps an AgentTask execution

Examples:
    ```python
    from neuroglia.data.conversation import Session, ExecutionContext
    from datetime import datetime, UTC

    # Create a new session
    session = Session(
        session_id="session-123",
        status="pending",
        created_at=datetime.now(UTC)
    )

    # Start the session
    session.started_at = datetime.now(UTC)
    session.status = "active"

    # Check status
    if session.is_active():
        # ... process session
        pass
    ```
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neuroglia.data.conversation.execution_context import ExecutionContext


@dataclass
class Session:
    """A session within an agent's lifecycle.

    Value object representing a single interaction session.
    Multiple sessions can belong to one Agent (Personal or Team).

    Attributes:
        session_id: Unique identifier for the session
        status: Session status ("pending" | "active" | "paused" | "completed" | "terminated")
        created_at: Timestamp when session was created
        started_at: Timestamp when session was started
        paused_at: Timestamp when session was paused
        completed_at: Timestamp when session completed
        execution_context: Optional execution context (may be stored separately)
        accumulated_pause_ms: Total time spent paused in milliseconds

    Examples:
        ```python
        session = Session(
            session_id="session-123",
            status="active",
            created_at=datetime.now(UTC),
            started_at=datetime.now(UTC)
        )

        if session.is_active():
            # Process session
            pass
        ```
    """

    session_id: str
    status: str  # "pending" | "active" | "paused" | "completed" | "terminated"

    # Timestamps
    created_at: datetime
    started_at: datetime | None = None
    paused_at: datetime | None = None
    completed_at: datetime | None = None

    # Execution context (optional - may be stored separately)
    execution_context: "ExecutionContext | None" = None

    # Pause tracking (for timed sessions)
    accumulated_pause_ms: int = 0

    def is_active(self) -> bool:
        """Check if the session is currently active."""
        return self.status == "active"

    def is_paused(self) -> bool:
        """Check if the session is currently paused."""
        return self.status == "paused"

    def is_completed(self) -> bool:
        """Check if the session has completed (successfully or terminated)."""
        return self.status in ("completed", "terminated")

    def is_pending(self) -> bool:
        """Check if the session is pending (not yet started)."""
        return self.status == "pending"

    def can_resume(self) -> bool:
        """Check if the session can be resumed."""
        return self.status == "paused"

    def get_duration_ms(self) -> int | None:
        """Get the total session duration in milliseconds (excluding pauses).

        Returns None if the session hasn't started yet.
        """
        if self.started_at is None:
            return None

        from datetime import timezone

        end_time = self.completed_at or datetime.now(timezone.utc)
        total_ms = int((end_time - self.started_at).total_seconds() * 1000)
        return total_ms - self.accumulated_pause_ms

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_context": (self.execution_context.to_dict() if self.execution_context else None),
            "accumulated_pause_ms": self.accumulated_pause_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Deserialize from dictionary."""
        from neuroglia.data.conversation.execution_context import ExecutionContext

        return cls(
            session_id=data["session_id"],
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=(datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None),
            paused_at=(datetime.fromisoformat(data["paused_at"]) if data.get("paused_at") else None),
            completed_at=(datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None),
            execution_context=(ExecutionContext.from_dict(data["execution_context"]) if data.get("execution_context") else None),
            accumulated_pause_ms=data.get("accumulated_pause_ms", 0),
        )
