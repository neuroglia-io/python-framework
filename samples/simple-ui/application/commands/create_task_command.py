"""Command for creating a new task."""

from dataclasses import dataclass
from typing import Optional

from domain.entities.task import Task
from domain.repositories.task_repository import TaskRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler


@dataclass
class CreateTaskCommand(Command[OperationResult["TaskDto"]]):
    """Command to create a new task."""

    title: str
    description: str = ""
    assigned_to: str = ""  # Will be set to created_by if not provided
    priority: str = "medium"
    created_by: str = ""  # Set by controller from authenticated user
    status: Optional[str] = None  # Accept status from frontend (optional)


@dataclass
class TaskDto:
    """Data transfer object for tasks."""

    id: str
    title: str
    description: str
    assigned_to: str
    priority: str
    status: str
    created_by: str


class CreateTaskHandler(CommandHandler[CreateTaskCommand, OperationResult[TaskDto]]):
    """Handler for creating tasks."""

    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, command: CreateTaskCommand) -> OperationResult[TaskDto]:
        """Handle task creation."""
        # Validation
        if not command.title or not command.title.strip():
            return self.bad_request("Task title is required")

        # Default assigned_to to created_by if not provided
        assigned_to = command.assigned_to.strip() if command.assigned_to else command.created_by
        if not assigned_to:
            return self.bad_request("Task must be assigned to a user")

        # Generate ID (in production, use proper ID generation)
        import uuid

        task_id = str(uuid.uuid4())[:8]

        # Create task entity
        task = Task(
            id=task_id,
            title=command.title.strip(),
            description=command.description.strip() if command.description else "",
            assigned_to=assigned_to,
            priority=command.priority or "medium",
            created_by=command.created_by,
        )

        # Save to repository
        await self.task_repository.save_async(task)

        # Return DTO
        dto = TaskDto(
            id=task.id,
            title=task.title,
            description=task.description,
            assigned_to=task.assigned_to,
            priority=task.priority,
            status=task.status,
            created_by=task.created_by,
        )

        return self.created(dto)
