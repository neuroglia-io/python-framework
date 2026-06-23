import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.eventing.cloud_events.cloud_event import CloudEvent
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.serialization.json import JsonSerializer


class CloudEventMiddleware(BaseHTTPMiddleware):
    """Represents the HTTP middleware used to handle incoming cloud events"""

    def __init__(self, app, service_provider: ServiceProviderBase):
        super().__init__(app)
        self.service_provider = service_provider
        self.serializer = self.service_provider.get_required_service(JsonSerializer)
        self.cloud_event_bus = self.service_provider.get_required_service(CloudEventBus)

    service_provider: ServiceProviderBase
    """ Gets the current service provider """

    cloud_event_bus: CloudEventBus
    """ Gets the service used to stream the application's incoming and outgoing cloud events """

    serializer: JsonSerializer
    """ Gets the service used to serialize/deserialize values to/from JSON """

    async def dispatch(self, request: Request, call_next):
        content_type = request.headers.get("content-type", None)
        if content_type is None or not content_type.startswith("application/cloudevents+json"):
            return await call_next(request)
        try:
            attributes = self.serializer.deserialize(await request.body(), dict)
            cloud_event = CloudEvent(**attributes)
            self.cloud_event_bus.input_stream.on_next(cloud_event)
        except Exception as ex:
            logging.error(f"An error occured while processing an incoming cloud event: {ex}")
            return Response(content=str(ex), status_code=500)
        return Response(status_code=202)
