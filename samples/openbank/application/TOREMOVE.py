from neuroglia.eventing.cloud_events.decorators import cloudevent

@cloudevent("com.test.fake")
class TestCloudEventToRemove:
    
    def __init__(self, **kwargs):
        pass