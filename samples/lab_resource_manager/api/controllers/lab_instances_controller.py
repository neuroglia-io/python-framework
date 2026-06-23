"""Lab Instance API Controller.

REST API endpoints for managing lab instance resources using the traditional
Neuroglia controller approach but handling Resources instead of DDD Entities.
"""

from datetime import datetime
from typing import List, Optional

from application.commands.create_lab_instance_command import CreateLabInstanceCommand
from application.queries.get_lab_instance_query import GetLabInstanceQuery
from application.queries.list_lab_instances_query import ListLabInstancesQuery
from classy_fastapi.decorators import delete, get, post, put
from domain.resources.lab_instance_request import LabInstancePhase
from fastapi import HTTPException, Query
from integration.models.lab_instance_dto import (
    CreateLabInstanceCommandDto,
    LabInstanceDto,
    UpdateLabInstanceDto,
)

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase


class LabInstancesController(ControllerBase):
    """Controller for lab instance resource management."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/", response_model=List[LabInstanceDto])
    async def list_lab_instances(
        self,
        namespace: Optional[str] = Query(None, description="Filter by namespace"),
        student_email: Optional[str] = Query(None, description="Filter by student email"),
        phase: Optional[LabInstancePhase] = Query(None, description="Filter by phase"),
        limit: Optional[int] = Query(None, description="Limit number of results"),
        offset: Optional[int] = Query(0, description="Offset for pagination"),
    ) -> list[LabInstanceDto]:
        """List lab instances with optional filtering."""
        try:
            query = ListLabInstancesQuery(
                namespace=namespace,
                student_email=student_email,
                phase=phase,
                limit=limit,
                offset=offset,
            )

            result = await self.mediator.execute_async(query)
            return self.process(result)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list lab instances: {str(e)}")

    @get("/{lab_instance_id}", response_model=LabInstanceDto)
    async def get_lab_instance(self, lab_instance_id: str) -> LabInstanceDto:
        """Get a specific lab instance by ID."""
        try:
            query = GetLabInstanceQuery(lab_instance_id=lab_instance_id)
            result = await self.mediator.execute_async(query)

            if not result:
                raise HTTPException(status_code=404, detail="Lab instance not found")

            return self.process(result)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get lab instance: {str(e)}")

    @post("/", response_model=LabInstanceDto, status_code=201)
    async def create_lab_instance(self, create_dto: CreateLabInstanceCommandDto) -> LabInstanceDto:
        """Create a new lab instance."""
        try:
            command = self.mapper.map(create_dto, CreateLabInstanceCommand)
            result = await self.mediator.execute_async(command)
            return self.process(result)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create lab instance: {str(e)}")

    @put("/{lab_instance_id}", response_model=LabInstanceDto)
    async def update_lab_instance(self, lab_instance_id: str, update_dto: UpdateLabInstanceDto) -> LabInstanceDto:
        """Update an existing lab instance."""
        try:
            # First get the current instance
            query = GetLabInstanceQuery(lab_instance_id=lab_instance_id)
            current_instance = await self.mediator.execute_async(query)

            if not current_instance:
                raise HTTPException(status_code=404, detail="Lab instance not found")

            # For now, only allow updating scheduled start time if still pending
            if current_instance.status.phase == LabInstancePhase.PENDING and update_dto.scheduled_start_time is not None:
                current_instance.spec.scheduled_start_time = update_dto.scheduled_start_time
                # Save through repository would be done via command pattern
                # This is a simplified example

                return self.mapper.map(current_instance, LabInstanceDto)
            else:
                raise HTTPException(status_code=400, detail="Lab instance cannot be updated in current phase")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update lab instance: {str(e)}")

    @delete("/{lab_instance_id}", status_code=204)
    async def delete_lab_instance(self, lab_instance_id: str):
        """Delete a lab instance (only if not running)."""
        try:
            # Get the instance first
            query = GetLabInstanceQuery(lab_instance_id=lab_instance_id)
            instance = await self.mediator.execute_async(query)

            if not instance:
                raise HTTPException(status_code=404, detail="Lab instance not found")

            # Only allow deletion if not running
            if instance.status.phase == LabInstancePhase.RUNNING:
                raise HTTPException(status_code=400, detail="Cannot delete running lab instance")

            # Implementation would use a DeleteLabInstanceCommand
            # For now, simplified approach
            raise HTTPException(status_code=501, detail="Delete operation not yet implemented")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete lab instance: {str(e)}")

    @post("/{lab_instance_id}/start", response_model=LabInstanceDto)
    async def start_lab_instance(self, lab_instance_id: str) -> LabInstanceDto:
        """Manually start a lab instance."""
        try:
            query = GetLabInstanceQuery(lab_instance_id=lab_instance_id)
            instance = await self.mediator.execute_async(query)

            if not instance:
                raise HTTPException(status_code=404, detail="Lab instance not found")

            if instance.status.phase != LabInstancePhase.PENDING:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot start lab instance in phase {instance.status.phase}",
                )

            # Implementation would use a StartLabInstanceCommand
            # For now, simplified approach - update scheduled start time to now
            instance.spec.scheduled_start_time = datetime.now(timezone.utc)

            return self.mapper.map(instance, LabInstanceDto)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start lab instance: {str(e)}")

    @post("/{lab_instance_id}/stop", response_model=LabInstanceDto)
    async def stop_lab_instance(self, lab_instance_id: str) -> LabInstanceDto:
        """Manually stop a running lab instance."""
        try:
            query = GetLabInstanceQuery(lab_instance_id=lab_instance_id)
            instance = await self.mediator.execute_async(query)

            if not instance:
                raise HTTPException(status_code=404, detail="Lab instance not found")

            if instance.status.phase != LabInstancePhase.RUNNING:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot stop lab instance in phase {instance.status.phase}",
                )

            # Implementation would use a StopLabInstanceCommand
            # For now, simplified approach
            raise HTTPException(status_code=501, detail="Stop operation not yet implemented")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to stop lab instance: {str(e)}")

    @get("/{lab_instance_id}/logs")
    async def get_lab_instance_logs(
        self,
        lab_instance_id: str,
        lines: Optional[int] = Query(100, description="Number of log lines to retrieve"),
    ):
        """Get logs from a lab instance container."""
        try:
            query = GetLabInstanceQuery(lab_instance_id=lab_instance_id)
            instance = await self.mediator.execute_async(query)

            if not instance:
                raise HTTPException(status_code=404, detail="Lab instance not found")

            if not instance.status.container_id:
                raise HTTPException(status_code=400, detail="Lab instance has no associated container")

            # Implementation would use ContainerService to get logs
            # For now, return placeholder
            return {
                "container_id": instance.status.container_id,
                "logs": f"Container logs would be retrieved here (last {lines} lines)",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get lab instance logs: {str(e)}")
