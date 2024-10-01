import logging

from multipledispatch import dispatch

from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.integration.models import IntegrationEvent
from neuroglia.mediation.mediator import IntegrationEventHandler

log = logging.getLogger(__name__)


@cloudevent("com.source.dummy.test.requested.v1")
class TestRequestedIntegrationEventV1(IntegrationEvent[str]):
    foo: str
    bar: str


class TestRequestedIntegrationEventHandler(IntegrationEventHandler[TestRequestedIntegrationEventV1]):

    def __init__(self) -> None:
        pass

    @dispatch(TestRequestedIntegrationEventV1)
    async def handle_async(self, e: TestRequestedIntegrationEventV1) -> None:
        log.info(f"Handling event type: {e.__cloudevent__type__} source: {e.__cloudevent__source__}")
