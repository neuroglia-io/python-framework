"""
Minimal CQRS Example
===================

This is the absolute minimal example of using Neuroglia's CQRS patterns.
Perfect for getting started quickly.
"""

import asyncio
import uuid
from dataclasses import dataclass

from neuroglia.core.operation_result import OperationResult
from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.mediation import (
    Command,
    CommandHandler,
    InMemoryRepository,
    Mediator,
    Query,
    QueryHandler,
)


# Simple data model
@dataclass
class Task:
    id: str
    title: str
    completed: bool = False


@dataclass
class TaskDto:
    id: str
    title: str
    completed: bool


# Commands and Queries
@dataclass
class CreateTaskCommand(Command[OperationResult[TaskDto]]):
    title: str


@dataclass
class GetTaskQuery(Query[OperationResult[TaskDto]]):
    task_id: str


# Handlers that inherit from the framework handlers
class CreateTaskHandler(CommandHandler[CreateTaskCommand, OperationResult[TaskDto]]):
    def __init__(self, repository: InMemoryRepository[Task]):
        super().__init__()
        self.repository = repository

    async def handle_async(self, request: CreateTaskCommand) -> OperationResult[TaskDto]:
        if not request.title.strip():
            return self.bad_request("Title cannot be empty")

        task = Task(str(uuid.uuid4()), request.title.strip())
        await self.repository.save_async(task)

        task_dto = TaskDto(task.id, task.title, task.completed)
        return self.created(task_dto)


class GetTaskHandler(QueryHandler[GetTaskQuery, OperationResult[TaskDto]]):
    def __init__(self, repository: InMemoryRepository[Task]):
        super().__init__()
        self.repository = repository

    async def handle_async(self, request: GetTaskQuery) -> OperationResult[TaskDto]:
        task = await self.repository.get_by_id_async(request.task_id)

        if not task:
            return self.not_found(Task, request.task_id)

        task_dto = TaskDto(task.id, task.title, task.completed)
        return self.ok(task_dto)


# Application setup
def create_app():
    services = ServiceCollection()

    # Add repository
    services.add_singleton(InMemoryRepository[Task])

    # Add mediator
    services.add_singleton(Mediator)

    # Register handlers in DI
    services.add_scoped(CreateTaskHandler)
    services.add_scoped(GetTaskHandler)

    provider = services.build()

    # Register handlers in mediator's handler registry (for routing)
    if not hasattr(Mediator, "_handler_registry"):
        Mediator._handler_registry = {}
    Mediator._handler_registry[CreateTaskCommand] = CreateTaskHandler
    Mediator._handler_registry[GetTaskQuery] = GetTaskHandler

    return provider


# Usage
async def main():
    provider = create_app()
    mediator: Mediator = provider.get_service(Mediator)  # type: ignore

    # Create a task
    create_cmd = CreateTaskCommand("Learn CQRS")
    result = await mediator.execute_async(create_cmd)

    if result.is_success:
        print(f"Created task: {result.data.title}")

        # Get the task
        get_query = GetTaskQuery(result.data.id)
        task_result = await mediator.execute_async(get_query)

        if task_result.is_success:
            print(f"Retrieved task: {task_result.data.title} (completed: {task_result.data.completed})")
        else:
            print(f"Task not found: {task_result.error_message}")
    else:
        print(f"Error: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
