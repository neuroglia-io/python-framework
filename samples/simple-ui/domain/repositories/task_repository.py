"""Task repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.task import Task


class TaskRepository(ABC):
    """Abstract repository for task persistence."""

    @abstractmethod
    async def get_all_async(self) -> list[Task]:
        """Get all tasks."""

    @abstractmethod
    async def get_by_id_async(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""

    @abstractmethod
    async def get_by_user_async(self, username: str) -> list[Task]:
        """Get tasks assigned to a specific user."""

    @abstractmethod
    async def save_async(self, task: Task) -> None:
        """Save a task."""

    @abstractmethod
    async def delete_async(self, task_id: str) -> None:
        """Delete a task."""
