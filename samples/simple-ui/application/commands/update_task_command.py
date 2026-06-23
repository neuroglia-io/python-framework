"""Command for updating an existing task."""

from dataclasses import dataclass
from typing import Optional

from application.commands.create_task_command import TaskDto
from domain.repositories.task_repository import TaskRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler


@dataclass
class UpdateTaskDto:
    """Data transfer object for updating a task."""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None


@dataclass
class UpdateTaskCommand(Command[OperationResult[TaskDto]]):
    """Command to update an existing task."""

    task_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    updated_by: str = ""  # Set by controller from authenticated user
    user_role: str = "user"  # Set by controller for authorization


class UpdateTaskHandler(CommandHandler[UpdateTaskCommand, OperationResult[TaskDto]]):
    """Handler for updating tasks."""

    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, command: UpdateTaskCommand) -> OperationResult[TaskDto]:
        """Handle task update."""
        # Get existing task
        task = await self.task_repository.get_by_id_async(command.task_id)
        if not task:
            return self.not_found(f"Task with ID {command.task_id} not found")

        # Authorization check: admins and managers can edit any task, users can only edit their own
        is_admin_or_manager = command.user_role in ["admin", "manager"]
        is_task_owner = task.created_by == command.updated_by or task.assigned_to == command.updated_by

        if not is_admin_or_manager and not is_task_owner:
            return OperationResult("Forbidden", 403, "You can only edit tasks that you created or are assigned to", "https://www.w3.org/Protocols/HTTP/HTRESP.html")

        # Update fields if provided
        if command.title is not None:
            if not command.title.strip():
                return self.bad_request("Task title cannot be empty")
            task.title = command.title.strip()

        if command.description is not None:
            task.description = command.description.strip()

        if command.status is not None:
            valid_statuses = ["pending", "in_progress", "completed"]
            if command.status not in valid_statuses:
                return self.bad_request(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            task.status = command.status

        if command.assigned_to is not None:
            # Only admins and managers can reassign tasks
            if not is_admin_or_manager:
                return OperationResult("Forbidden", 403, "Only admins and managers can reassign tasks to other users", "https://www.w3.org/Protocols/HTTP/HTRESP.html")
            if not command.assigned_to.strip():
                return self.bad_request("Assigned to cannot be empty")
            task.assigned_to = command.assigned_to.strip()

        if command.priority is not None:
            valid_priorities = ["low", "medium", "high"]
            if command.priority not in valid_priorities:
                return self.bad_request(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
            task.priority = command.priority

        # Save updated task
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

        return self.ok(dto)
