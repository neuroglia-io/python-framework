import datetime
import uuid
from abc import ABC, abstractmethod

from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.mapping import Mapper
from neuroglia.mediation import CommandHandler, Mediator, TCommand, TResult

from application.services.docker_host_command_runner import DockerHostCommandRunner

# THIS IS UNUSED RIGHT NOW
# TODO: Fix the mediator as it doesnt resolve the DesktopCommandHandler correctly if it inherits from DesktopCommandHandlerBase (and CommandHandler)


class DesktopCommandHandlerBase(CommandHandler[TCommand, TResult], ABC):
    """Represents the base class for all services used to handle Desktop Commands (run on the Docker Host)"""

    def __init__(self, mediator: Mediator, mapper: Mapper, cloud_event_bus: CloudEventBus, cloud_event_publishing_options: CloudEventPublishingOptions, docker_host_command_runner: DockerHostCommandRunner):
        self.mediator = mediator
        self.mapper = mapper
        self.cloud_event_bus = cloud_event_bus
        self.cloud_event_publishing_options = cloud_event_publishing_options
        self.docker_host_command_runner = docker_host_command_runner
        # super().__init__()

    mediator: Mediator
    """ Gets the service used to mediate calls """

    mapper: Mapper
    """ Gets the service used to map objects """

    cloud_event_bus: CloudEventBus
    """ Gets the service used to observe the cloud events consumed and produced by the application """

    cloud_event_publishing_options: CloudEventPublishingOptions
    """ Gets the options used to configure how the application should publish cloud events """

    docker_host_command_runner: DockerHostCommandRunner

    @abstractmethod
    async def handle_async(self, request: TCommand) -> TResult:
        """Handles the specified request"""
        raise NotImplementedError()

    async def publish_cloud_event_async(self, command: TCommand):
        """Converts the specified command into a new integration event, then publishes it as a cloud event"""
        if "__map_to__" not in dir(command):
            raise Exception(f"Missing a request-to-integration-event mapping configuration for desktop command type {type(command)}")
        id_ = str(uuid.uuid4()).replace("-", "")
        source = self.cloud_event_publishing_options.source
        type_prefix = self.cloud_event_publishing_options.type_prefix
        integration_event_type = command.__map_to__
        integration_event = self.mapper.map(command, integration_event_type)
        type_str = f"{type_prefix}.{integration_event.__cloudevent__}"
        spec_version = CloudEventSpecVersion.v1_0
        time = datetime.datetime.now()
        subject = command.aggregate_id
        sequencetype = None
        sequence = None
        cloud_event = CloudEvent(id_, source, type_str, spec_version, sequencetype, sequence, time, subject, data=integration_event)
        self.cloud_event_bus.output_stream.on_next(cloud_event)
