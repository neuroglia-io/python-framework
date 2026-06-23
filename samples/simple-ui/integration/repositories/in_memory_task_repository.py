"""In-memory implementation of task repository."""

from typing import Optional

from domain.entities.task import Task
from domain.repositories.task_repository import TaskRepository


class InMemoryTaskRepository(TaskRepository):
    """In-memory task repository for demo purposes."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._initialize_sample_data()

    def _initialize_sample_data(self):
        """Initialize with sample tasks."""
        sample_tasks = [
            Task(
                "1",
                "Review code PR #123",
                "Critical bug fix needed",
                "john.doe",
                "high",
                "in_progress",
                "admin",
            ),
            Task(
                "2",
                "Update documentation",
                "Add API docs for new endpoints",
                "jane.smith",
                "medium",
                "pending",
                "admin",
            ),
            Task(
                "3",
                "Deploy to staging",
                "Deploy v2.1.0 to staging environment",
                "admin",
                "high",
                "pending",
                "admin",
            ),
            Task(
                "4",
                "Client meeting prep",
                "Prepare slides for Q4 review",
                "jane.smith",
                "medium",
                "in_progress",
                "manager",
            ),
            Task(
                "5",
                "Database optimization",
                "Optimize slow queries in reports",
                "john.doe",
                "medium",
                "pending",
                "manager",
            ),
            Task(
                "6",
                "Bug fix: Login timeout",
                "Users reporting session timeouts",
                "john.doe",
                "high",
                "pending",
                "user",
            ),
        ]

        for task in sample_tasks:
            self._tasks[task.id] = task

    async def get_all_async(self) -> list[Task]:
        """Get all tasks."""
        return list(self._tasks.values())

    async def get_by_id_async(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    async def get_by_user_async(self, username: str) -> list[Task]:
        """Get tasks assigned to a specific user."""
        return [task for task in self._tasks.values() if task.assigned_to == username]

    async def save_async(self, task: Task) -> None:
        """Save a task."""
        self._tasks[task.id] = task

    async def delete_async(self, task_id: str) -> None:
        """Delete a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
