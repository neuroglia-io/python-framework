"""Tasks API controller."""

from typing import List

from api.controllers.auth_controller import UserInfo, get_current_user
from application.commands.create_task_command import CreateTaskCommand, TaskDto
from application.commands.delete_task_command import DeleteTaskCommand
from application.commands.update_task_command import UpdateTaskCommand, UpdateTaskDto
from application.queries.get_tasks_query import GetTasksQuery
from classy_fastapi import delete, get, post, put
from fastapi import Depends

from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase


class TasksController(ControllerBase):
    """Tasks management controller."""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        super().__init__(service_provider, mapper, mediator)

    @get("/", response_model=List[TaskDto])
    async def get_tasks(self, current_user: UserInfo = Depends(get_current_user)) -> list[TaskDto]:
        """Get tasks based on user role."""
        query = GetTasksQuery(username=current_user.username, role=current_user.role)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/", response_model=TaskDto, status_code=201)
    async def create_task(
        self,
        command: CreateTaskCommand,
        current_user: UserInfo = Depends(get_current_user),
    ) -> TaskDto:
        """Create a new task (all users can create tasks)."""
        # Set created_by to current user
        command.created_by = current_user.username
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/{task_id}", response_model=TaskDto)
    async def update_task(
        self,
        task_id: str,
        update_data: UpdateTaskDto,
        current_user: UserInfo = Depends(get_current_user),
    ) -> TaskDto:
        """Update an existing task."""
        # Create command with data from request body and path/user
        command = UpdateTaskCommand(task_id=task_id, title=update_data.title, description=update_data.description, status=update_data.status, assigned_to=update_data.assigned_to, priority=update_data.priority, updated_by=current_user.username, user_role=current_user.role)

        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/{task_id}", status_code=204)
    async def delete_task(
        self,
        task_id: str,
        current_user: UserInfo = Depends(get_current_user),
    ) -> None:
        """Delete a task."""
        command = DeleteTaskCommand(task_id=task_id, deleted_by=current_user.username, user_role=current_user.role)

        result = await self.mediator.execute_async(command)
        self.process(result)
