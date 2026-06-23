"""Lab Worker API Controller.

REST API endpoints for managing lab worker resources.
"""

from typing import List, Optional

from application.commands.create_lab_worker_command import CreateLabWorkerCommand
from application.queries.get_lab_worker_query import GetLabWorkerQuery
from application.queries.list_lab_workers_query import ListLabWorkersQuery
from classy_fastapi.decorators import delete, get, post, put
from domain.resources.lab_worker import LabWorkerPhase
from fastapi import HTTPException, Query
from integration.models.lab_worker_dto import CreateLabWorkerCommandDto, LabWorkerDto

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase


class LabWorkersController(ControllerBase):
    """Controller for lab worker resource management."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/", response_model=List[LabWorkerDto])
    async def list_lab_workers(
        self,
        namespace: Optional[str] = Query(None, description="Filter by namespace"),
        lab_track: Optional[str] = Query(None, description="Filter by lab track"),
        phase: Optional[LabWorkerPhase] = Query(None, description="Filter by phase"),
        limit: int = Query(100, description="Limit number of results", ge=1, le=1000),
        offset: int = Query(0, description="Offset for pagination", ge=0),
    ) -> list[LabWorkerDto]:
        """List lab workers with optional filtering.

        Args:
            namespace: Filter by namespace
            lab_track: Filter by lab track (e.g., "aws-saa", "ccna")
            phase: Filter by current phase
            limit: Maximum number of results to return (1-1000)
            offset: Number of results to skip for pagination

        Returns:
            List of lab worker DTOs
        """
        try:
            query = ListLabWorkersQuery(
                namespace=namespace,
                lab_track=lab_track,
                phase=phase,
                limit=limit,
                offset=offset,
            )

            result = await self.mediator.execute_async(query)
            return self.process(result)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list lab workers: {str(e)}")

    @get("/{worker_id}", response_model=LabWorkerDto)
    async def get_lab_worker(self, worker_id: str) -> LabWorkerDto:
        """Get a specific lab worker by ID.

        Args:
            worker_id: The unique ID of the lab worker resource

        Returns:
            Lab worker DTO

        Raises:
            HTTPException: 404 if lab worker not found
        """
        try:
            query = GetLabWorkerQuery(worker_id=worker_id)
            result = await self.mediator.execute_async(query)
            return self.process(result)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get lab worker: {str(e)}")

    @post("/", response_model=LabWorkerDto, status_code=201)
    async def create_lab_worker(self, create_dto: CreateLabWorkerCommandDto) -> LabWorkerDto:
        """Create a new lab worker.

        Args:
            create_dto: Lab worker creation data including AWS config and CML settings

        Returns:
            Created lab worker DTO

        Raises:
            HTTPException: 400 if validation fails, 500 on server error
        """
        try:
            command = self.mapper.map(create_dto, CreateLabWorkerCommand)
            result = await self.mediator.execute_async(command)
            return self.process(result)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create lab worker: {str(e)}")

    @put("/{worker_id}/drain", response_model=LabWorkerDto)
    async def drain_lab_worker(self, worker_id: str) -> LabWorkerDto:
        """Initiate draining of a lab worker.

        Draining prevents new labs from being scheduled on this worker while
        allowing existing labs to complete gracefully.

        Args:
            worker_id: The unique ID of the lab worker resource

        Returns:
            Updated lab worker DTO

        Raises:
            HTTPException: 404 if worker not found, 501 not implemented
        """
        # TODO: Implement UpdateLabWorkerCommand to set draining flag
        raise HTTPException(status_code=501, detail="Drain operation not yet implemented")

    @delete("/{worker_id}", status_code=204)
    async def delete_lab_worker(self, worker_id: str) -> None:
        """Delete a lab worker.

        Workers can only be deleted if they are not currently hosting any lab instances.
        Workers in ACTIVE phase cannot be deleted.

        Args:
            worker_id: The unique ID of the lab worker resource

        Raises:
            HTTPException: 404 if worker not found, 501 not implemented
        """
        # TODO: Implement DeleteLabWorkerCommand
        raise HTTPException(status_code=501, detail="Delete operation not yet implemented")

    @get("/{worker_id}/metrics", response_model=dict)
    async def get_lab_worker_metrics(self, worker_id: str) -> dict:
        """Get current utilization metrics for a lab worker.

        Args:
            worker_id: The unique ID of the lab worker resource

        Returns:
            Dictionary containing current metrics (CPU, memory, hosted labs, etc.)

        Raises:
            HTTPException: 404 if worker not found, 501 not implemented
        """
        # TODO: Add metrics to LabWorkerDto and return from query
        raise HTTPException(status_code=501, detail="Metrics endpoint not yet implemented")
