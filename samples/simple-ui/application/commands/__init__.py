"""Commands."""

# Import handlers to ensure they are discovered by the mediator
from application.commands.create_task_command import CreateTaskHandler
from application.commands.delete_task_command import DeleteTaskHandler
from application.commands.update_task_command import UpdateTaskHandler

__all__ = ["CreateTaskHandler", "UpdateTaskHandler", "DeleteTaskHandler"]
