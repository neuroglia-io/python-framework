import datetime
import logging
import uuid
from dataclasses import asdict
from typing import Generic

from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.mediation import DomainEvent, Mediator, TDomainEvent

log = logging.getLogger(__name__)


class BaseDomainEventHandler(Generic[TDomainEvent]):
    """
    Base class for all command handlers that provides application infrastructure:
    - Mediator for inter-service communication
    - Cloud event publishing for domain events
    - Utility methods for common operations

    IMPORTANT: Due to Neuroglia mediator discovery requirements, implementing classes
    MUST inherit from both BaseDomainEventHandler AND DomainEventHandler directly:

    Usage:
    class MyDomainEventHandler(
        BaseDomainEventHandler[MyDomainEvent],
        DomainEventHandler[MyDomainEvent, OperationResult[Dict[str, Any]]]
    ):

    This dual inheritance pattern satisfies both:
    1. Infrastructure needs (BaseDomainEventHandler)
    2. Mediator discovery requirements (direct DomainEventHandler interface)

    The mediator's auto-discovery via Mediator.configure() requires direct DomainEventHandler inheritance.
    """

    mediator: Mediator
    """ Gets the service used to mediate calls """

    cloud_event_bus: CloudEventBus
    """ Gets the service used to observe the cloud events consumed and produced by the application """

    cloud_event_publishing_options: CloudEventPublishingOptions
    """ Gets the options used to configure how the application should publish cloud events """

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
    ):
        self.mediator = mediator
        self.cloud_event_bus = cloud_event_bus
        self.cloud_event_publishing_options = cloud_event_publishing_options

    async def publish_cloud_event_async(self, ev: DomainEvent) -> bool:
        """Converts the specified command into a new integration event, then publishes it as a cloud event"""
        try:
            id_ = str(uuid.uuid4()).replace("-", "")
            source = self.cloud_event_publishing_options.source
            type_prefix = self.cloud_event_publishing_options.type_prefix
            type_str = f"{type_prefix}.{ev.__cloudevent__type__}"
            spec_version = CloudEventSpecVersion.v1_0
            time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            subject = ev.aggregate_id
            sequencetype = None
            sequence = None
            payload = {
                "id": id_,
                "source": source,
                "type": type_str,
                "specversion": spec_version,
                "sequencetype": sequencetype,
                "sequence": sequence,
                "time": time,
                "subject": subject,
                "data": ev.data if hasattr(ev, "data") else asdict(ev),
            }
            cloud_event = CloudEvent(**payload)
            self.cloud_event_bus.output_stream.on_next(cloud_event)
            return True
        except Exception as e:
            raise Exception(f"Failed to publish a cloudevent {ev} Exception {e}")
