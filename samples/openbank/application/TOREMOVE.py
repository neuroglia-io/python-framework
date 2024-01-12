from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.mediation.mediator import IntegrationEventHandler

@cloudevent("com.test.fake")
class TestCloudEventToRemove:
    
    def __init__(self, **kwargs):
        pass
    
class TestCloudEventToRemoveHandler(IntegrationEventHandler[TestCloudEventToRemove]):

    async def handle_async(self, e: TestCloudEventToRemove) -> None:
        print("Event has been handled")