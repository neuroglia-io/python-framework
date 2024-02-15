from multipledispatch import dispatch

from neuroglia.integration.models import IntegrationEvent
from neuroglia.data.abstractions import Identifiable, queryable
from neuroglia.data.infrastructure.abstractions import QueryableRepository
from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.mediation.mediator import IntegrationEventHandler


@queryable
class ScoreReport(Identifiable[str]):
    id: str
    candidate_id: str
    total_score: int = 0
    max_score: int = 0
    min_score: int = 0
    reread_score: int = 0
    lab_date: str = ""

    def __init__(self,
                 id: str,
                 candidate_id: str,
                 total_score: int,
                 max_score: int,
                 min_score: int,
                 reread_score: int,
                 lab_date: str
                 ) -> None:
        super().__init__()
        self.id = id
        self.candidate_id = candidate_id
        self.total_score = total_score
        self.max_score = max_score
        self.min_score = min_score
        self.reread_score = reread_score
        self.lab_date = lab_date


@cloudevent("com.cisco.mozart.scorereport.submitted.v1")
class ScoreReportSubmittedIntegrationEventV1(IntegrationEvent[str]):
    """ Sample event:
    {
        "aggregate_id": "123",
        "candidate_id": "123",
        "total_score": 81,
        "max_score": 100,
        "min_score": 80,
        "reread_score": 50,
        "lab_date": "2024-02-14"
    }

    """
    aggregate_id: str
    candidate_id: str
    total_score: int = 0
    max_score: int = 0
    min_score: int = 0
    reread_score: int = 0
    lab_date: str = ""


class ScoreReportIntegrationEventHandler(IntegrationEventHandler[ScoreReportSubmittedIntegrationEventV1]):

    repository: QueryableRepository[ScoreReport, str]

    def __init__(self, repository: QueryableRepository[ScoreReport, str]) -> None:
        self.repository = repository

    @dispatch(ScoreReportSubmittedIntegrationEventV1)
    async def handle_async(self, e: ScoreReportSubmittedIntegrationEventV1) -> None:
        report = ScoreReport(id=e.aggregate_id,
                             candidate_id=e.candidate_id,
                             total_score=e.total_score,
                             max_score=e.max_score,
                             min_score=e.min_score,
                             reread_score=e.reread_score,
                             lab_date=e.lab_date)
        await self.repository.add_async(report)
        reports = (await self.repository.query_async()).where(lambda x: x.candidate_id == e.candidate_id).to_list()
        print(reports)
