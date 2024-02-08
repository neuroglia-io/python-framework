import logging

from dataclasses import dataclass
from multipledispatch import dispatch
from typing import List

from neuroglia.integration.models import IntegrationEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.mediation.mediator import IntegrationEventHandler


@cloudevent("com.source.dummy.test.requested.v1")
class TestRequestedIntegrationEventV1(IntegrationEvent[str]):
    foo: str


class TestRequestedIntegrationEventHandler(IntegrationEventHandler[TestRequestedIntegrationEventV1]):

    def __init__(self) -> None:
        pass

    @dispatch(TestRequestedIntegrationEventV1)
    async def handle_async(self, e: TestRequestedIntegrationEventV1) -> None:
        logging.info(f"Handling event type: {e.foo}")
        print(f"Handling event type: {e.foo}")
