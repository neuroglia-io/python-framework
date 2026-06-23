import logging
from typing import Any

from multipledispatch import dispatch
from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.integration.models import IntegrationEvent
from neuroglia.mediation.mediator import IntegrationEventHandler

log = logging.getLogger(__name__)


@cloudevent("com.source.dummy.test.requested.v1")
class TestRequestedIntegrationEventV1(IntegrationEvent[str]):
    """Sample Event:
    {
        "foo": "test",
        "bar": 1,
        "boo": false
    }

    Args:
        IntegrationEvent (_type_): _description_
    """

    foo: str
    bar: int | None
    boo: bool | None
    data: Any | None


class TestIntegrationEventHandler(
    IntegrationEventHandler[TestRequestedIntegrationEventV1]
):
    def __init__(self) -> None:
        pass

    @dispatch(TestRequestedIntegrationEventV1)
    async def handle_async(self, e: TestRequestedIntegrationEventV1) -> None:
        log.info(f"Handling event type: {e.__cloudevent__type__}: {e.__dict__}")
