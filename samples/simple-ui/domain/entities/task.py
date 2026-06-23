"""Task domain entity."""

from dataclasses import dataclass
from datetime import datetime

from neuroglia.data.abstractions import Entity


@dataclass
class Task(Entity):
    """Represents a task in the system."""

    title: str
    description: str
    assigned_to: str
    priority: str  # low, medium, high
    status: str  # pending, in_progress, completed
    created_at: datetime
    created_by: str

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        assigned_to: str,
        priority: str = "medium",
        status: str = "pending",
        created_by: str = "system",
    ):
        super().__init__()
        self.id = id
        self.title = title
        self.description = description
        self.assigned_to = assigned_to
        self.priority = priority
        self.status = status
        self.created_at = datetime.now()
        self.created_by = created_by

    def complete(self):
        """Mark task as completed."""
        self.status = "completed"

    def assign_to(self, user: str):
        """Assign task to a user."""
        self.assigned_to = user
