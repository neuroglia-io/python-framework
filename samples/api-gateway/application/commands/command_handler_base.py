import datetime
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict

from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.integration.models import IntegrationEvent
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator, TCommand, TResult

from application.settings import AiGatewaySettings
from integration import IntegrationException


class CommandHandlerBase(ABC):
    """Represents the base class for all services used to handle IOLVM Commands."""

    mediator: Mediator
    """ Gets the service used to mediate calls """

    mapper: Mapper
    """ Gets the service used to map objects """

    cloud_event_bus: CloudEventBus
    """ Gets the service used to observe the cloud events consumed and produced by the application """

    cloud_event_publishing_options: CloudEventPublishingOptions
    """ Gets the options used to configure how the application should publish cloud events """

    app_settings: AiGatewaySettings
    """ Gets the application's settings."""

    def __init__(self, mediator: Mediator, mapper: Mapper, cloud_event_bus: CloudEventBus, cloud_event_publishing_options: CloudEventPublishingOptions, app_settings: AiGatewaySettings):
        self.mediator = mediator
        self.mapper = mapper
        self.cloud_event_bus = cloud_event_bus
        self.cloud_event_publishing_options = cloud_event_publishing_options
        self.app_settings = app_settings

    @abstractmethod
    async def handle_async(self, request: TCommand) -> TResult:
        """Handles the specified request"""
        raise NotImplementedError()

    async def publish_cloud_event_async(self, ev: IntegrationEvent) -> bool:
        """Converts the specified command into a new integration event, then publishes it as a cloud event"""
        try:
            id_ = str(uuid.uuid4()).replace("-", "")
            source = self.cloud_event_publishing_options.source
            type_prefix = self.cloud_event_publishing_options.type_prefix
            type_str = f"{type_prefix}.{ev.__cloudevent__type__}"
            spec_version = CloudEventSpecVersion.v1_0
            time = datetime.datetime.now()
            subject = ev.aggregate_id
            sequencetype = None
            sequence = None
            cloud_event = CloudEvent(id_, source, type_str, spec_version, sequencetype, sequence, time, subject, data=asdict(ev))
            self.cloud_event_bus.output_stream.on_next(cloud_event)
            return True
        except Exception as e:
            raise IntegrationException(f"Failed to publish a cloudevent {ev}: Exception {e}")
