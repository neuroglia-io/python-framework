"""Query for retrieving tasks."""

from dataclasses import dataclass
from typing import List, Optional

from application.commands.create_task_command import TaskDto
from domain.repositories.task_repository import TaskRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetTasksQuery(Query[OperationResult[List[TaskDto]]]):
    """Query to get tasks, optionally filtered by user."""

    username: Optional[str] = None
    role: Optional[str] = None


class GetTasksHandler(QueryHandler[GetTasksQuery, OperationResult[List[TaskDto]]]):
    """Handler for retrieving tasks."""

    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, query: GetTasksQuery) -> OperationResult[list[TaskDto]]:
        """Handle task retrieval with role-based filtering."""

        # Get tasks based on role
        if query.role in ["admin", "manager"]:
            # Admins and managers see all tasks
            tasks = await self.task_repository.get_all_async()
        else:
            # Regular users see only their assigned tasks
            if not query.username:
                return self.bad_request("Username required for user role")
            tasks = await self.task_repository.get_by_user_async(query.username)

        # Convert to DTOs
        dtos = [
            TaskDto(
                id=task.id,
                title=task.title,
                description=task.description,
                assigned_to=task.assigned_to,
                priority=task.priority,
                status=task.status,
                created_by=task.created_by,
            )
            for task in tasks
        ]

        return self.ok(dtos)
