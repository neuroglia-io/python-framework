import json
from fastapi import FastAPI, Request, Response
from neuroglia.dependency_injection.service_provider import ServiceProvider, ServiceProviderBase
from neuroglia.eventing.cloud_events.cloud_event import CloudEvent
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from starlette.middleware.base import BaseHTTPMiddleware


class CloudEventMiddleware(BaseHTTPMiddleware):
    ''' Represents the HTTP middleware used to handle incoming cloud events '''
     
    def __init__(self, app, service_provider: ServiceProviderBase):
        super().__init__(app)
        self.service_provider = service_provider
        self.cloud_event_bus = self.service_provider.get_required_service(CloudEventBus)
        
    service_provider : ServiceProviderBase
    ''' Gets the current service provider '''
    
    cloud_event_bus : CloudEventBus 
    ''' Gets the service used to stream the application's incoming and outgoing cloud events '''

    async def dispatch(self, request: Request, call_next):
        content_type = request.headers.get('content-type', None)
        if content_type is None or not content_type.startswith('application/cloudevents+json'): return await call_next(request)
        try:
            cloud_event = CloudEvent(**json.loads(await request.body()))
            self.cloud_event_bus.input_stream.on_next(cloud_event)
        except Exception as ex:
            print(f"An error occured while processing an incoming cloud event: {ex}")
            return Response(content=str(ex), status_code=500)
        return Response(status_code=202)
        