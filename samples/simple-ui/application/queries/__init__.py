"""Queries."""

# Import handlers to ensure they are discovered by the mediator
from application.queries.get_tasks_query import GetTasksHandler

__all__ = ["GetTasksHandler"]
