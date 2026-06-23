"""Command for deleting a task."""

from dataclasses import dataclass

from domain.repositories.task_repository import TaskRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler


@dataclass
class DeleteTaskCommand(Command[OperationResult[None]]):
    """Command to delete a task."""

    task_id: str
    deleted_by: str = ""  # Set by controller from authenticated user
    user_role: str = "user"  # Set by controller for authorization


class DeleteTaskHandler(CommandHandler[DeleteTaskCommand, OperationResult[None]]):
    """Handler for deleting tasks."""

    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, command: DeleteTaskCommand) -> OperationResult[None]:
        """Handle task deletion."""
        # Check if task exists
        task = await self.task_repository.get_by_id_async(command.task_id)
        if not task:
            return self.not_found(f"Task with ID {command.task_id} not found")

        # Authorization check: admins and managers can delete any task, users can only delete their own
        is_admin_or_manager = command.user_role in ["admin", "manager"]
        is_task_owner = task.created_by == command.deleted_by or task.assigned_to == command.deleted_by

        if not is_admin_or_manager and not is_task_owner:
            return OperationResult("Forbidden", 403, "You can only delete tasks that you created or are assigned to", "https://www.w3.org/Protocols/HTTP/HTRESP.html")

        # Delete the task
        await self.task_repository.delete_async(command.task_id)

        return self.ok(None)
