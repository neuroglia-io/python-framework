"""Query for retrieving a lab worker by ID."""

from dataclasses import dataclass

from domain.resources.lab_worker import LabWorker, LabWorkerSpec, LabWorkerStatus
from integration.models.lab_worker_dto import LabWorkerDto

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.resources import ResourceRepository
from neuroglia.mapping import Mapper
from neuroglia.mediation.mediator import Query, QueryHandler


@dataclass
class GetLabWorkerQuery(Query[OperationResult[LabWorkerDto]]):
    """Query to get a lab worker by ID."""

    worker_id: str


class GetLabWorkerQueryHandler(QueryHandler[GetLabWorkerQuery, OperationResult[LabWorkerDto]]):
    """Handler for retrieving lab worker resources."""

    def __init__(self, repository: ResourceRepository[LabWorkerSpec, LabWorkerStatus], mapper: Mapper):
        super().__init__()
        self._repository = repository
        self._mapper = mapper

    async def handle_async(self, request: GetLabWorkerQuery) -> OperationResult[LabWorkerDto]:
        """Retrieve a lab worker by ID."""
        # Get the resource from repository
        worker = await self._repository.get_async(request.worker_id)

        if not worker:
            return self.not_found(LabWorker, request.worker_id)

        # Map to DTO and return
        worker_dto = self._mapper.map(worker, LabWorkerDto)
        return self.ok(worker_dto)
