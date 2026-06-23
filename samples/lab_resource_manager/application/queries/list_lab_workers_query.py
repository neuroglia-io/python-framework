"""Query for listing lab workers with filtering."""

from dataclasses import dataclass, field
from typing import Optional

from domain.resources.lab_worker import LabWorkerPhase, LabWorkerSpec, LabWorkerStatus
from integration.models.lab_worker_dto import LabWorkerDto

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.resources import ResourceRepository
from neuroglia.mapping import Mapper
from neuroglia.mediation.mediator import Query, QueryHandler


@dataclass
class ListLabWorkersQuery(Query[OperationResult[list[LabWorkerDto]]]):
    """Query to list lab workers with optional filters."""

    namespace: Optional[str] = None
    lab_track: Optional[str] = None
    phase: Optional[LabWorkerPhase] = None
    limit: int = 100
    offset: int = 0
    labels: dict[str, str] = field(default_factory=dict)


class ListLabWorkersQueryHandler(QueryHandler[ListLabWorkersQuery, OperationResult[list[LabWorkerDto]]]):
    """Handler for listing lab worker resources."""

    def __init__(self, repository: ResourceRepository[LabWorkerSpec, LabWorkerStatus], mapper: Mapper):
        super().__init__()
        self._repository = repository
        self._mapper = mapper

    async def handle_async(self, request: ListLabWorkersQuery) -> OperationResult[list[LabWorkerDto]]:
        """List lab workers with filtering."""
        # Build label selector
        label_selector = request.labels.copy()
        if request.lab_track:
            label_selector["lab-track"] = request.lab_track
        label_selector["resource-type"] = "lab-worker"

        # Get resources from repository
        workers = await self._repository.list_async(namespace=request.namespace, label_selector=label_selector)

        # Filter by phase if specified
        if request.phase:
            workers = [w for w in workers if w.status and w.status.phase == request.phase]

        # Apply pagination
        workers = workers[request.offset : request.offset + request.limit]

        # Map to DTOs
        worker_dtos = [self._mapper.map(w, LabWorkerDto) for w in workers]

        # Return result
        return self.ok(worker_dtos)
