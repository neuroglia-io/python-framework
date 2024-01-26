from dataclasses import dataclass
from multipledispatch import dispatch
from typing import List

from neuroglia.integration.models import IntegrationEvent
from neuroglia.data.abstractions import DomainEvent, Identifiable, queryable
from neuroglia.data.infrastructure.abstractions import QueryableRepository
from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.mediation.mediator import DomainEventHandler, IntegrationEventHandler


@queryable
@dataclass
class ScoreReport(Identifiable[str]):
    candidate_id: str
    total_score: int
    max_score: int
    min_score: int
    reread_score: int
    lab_date: str


@cloudevent("com.cisco.mozart.test-requested.v1")
class ScoreReportSubmittedEventV1(IntegrationEvent[str]):
    candidate_id: str
    total_score: int
    max_score: int
    min_score: int
    reread_score: int
    lab_date: str


class ScoreReportIntegrationEventHandler(IntegrationEventHandler[ScoreReportSubmittedEventV1]):

    repository: QueryableRepository[ScoreReport, str]

    def __init__(self, repository: QueryableRepository[ScoreReport, str]) -> None:
        self.repository = repository

    @dispatch(ScoreReportSubmittedEventV1)
    async def handle_async(self, e: ScoreReportSubmittedEventV1) -> None:
        report = await self.get_or_create_read_model_async(e.aggregate_id)
        report = ScoreReport(candidate_id=e.candidate_id,
                             total_score=e.total_score,
                             max_score=e.max_score,
                             min_score=e.min_score,
                             reread_score=e.reread_score,
                             lab_date=e.lab_date)
        await self.repository.add_async(report)
        reports = (await self.repository.query_async()).where(lambda x: x.candidate_id == e.candidate_id).to_list()
        pass