import datetime
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.integration.models import IntegrationEvent
from neuroglia.mapping.mapper import map_from, map_to
from neuroglia.mediation import Command, CommandHandler

from application.events.integration.desktop_host_command_events import (
    DesktopHostCommandExecutedIntegrationEventV1,
    DesktopHostCommandReceivedIntegrationEventV1,
)
from application.services import DockerHostCommandRunner
from integration.models import TestHostScriptCommandDto
from integration.services import HostCommand

log = logging.getLogger(__name__)


@map_from(TestHostScriptCommandDto)
@map_to(TestHostScriptCommandDto)
@dataclass
class TestHostScriptCommand(Command):
    user_input: str


class TestHostScriptCommandsHandler(CommandHandler[TestHostScriptCommand, OperationResult[Any]]):
    """Represents the service used to handle UserInfo-related Commands"""

    cloud_event_bus: CloudEventBus
    """ Gets the service used to observe the cloud events consumed and produced by the application """

    cloud_event_publishing_options: CloudEventPublishingOptions
    """ Gets the options used to configure how the application should publish cloud events """

    docker_host_command_runner: DockerHostCommandRunner

    def __init__(self, cloud_event_bus: CloudEventBus, cloud_event_publishing_options: CloudEventPublishingOptions, docker_host_command_runner: DockerHostCommandRunner):
        self.cloud_event_bus = cloud_event_bus
        self.cloud_event_publishing_options = cloud_event_publishing_options
        self.docker_host_command_runner = docker_host_command_runner

    async def handle_async(self, command: TestHostScriptCommand) -> OperationResult[Any]:
        command_id = str(uuid.uuid4()).replace("-", "")
        command_line = HostCommand()
        data = {}
        try:
            line = f"~/test_shell_script_on_host.sh -i {command.user_input.replace(' ', '_')}"
            log.debug(f"TestHostScriptCommand Line: {line}")
            await self.publish_cloud_event_async(DesktopHostCommandReceivedIntegrationEventV1(aggregate_id=command_id, command_line=line))

            command_line.line = line
            data = await self.docker_host_command_runner.run(command_line)
            data.update({"aggregate_id": command_id})
            log.debug(f"TestHostScriptCommand: {data}")

            await self.publish_cloud_event_async(DesktopHostCommandExecutedIntegrationEventV1(**data))
            data.update({"success": True}) if len(data["stderr"]) == 0 else data.update({"success": False})
            return self.created(data)

        except Exception as ex:
            return self.bad_request(f"Exception when trying to run a shell script on the host: {command_line.line}: {data}: {ex}")

    async def publish_cloud_event_async(self, e: IntegrationEvent):
        """Converts the specified command into a new integration event, then publishes it as a cloud event"""
        if "__cloudevent__type__" not in dir(e):
            raise Exception(f"Missing a cloudevent configuration for desktop command type {type(e)}")
        id_ = str(uuid.uuid4()).replace("-", "")
        source = self.cloud_event_publishing_options.source
        type_prefix = self.cloud_event_publishing_options.type_prefix
        type_str = f"{type_prefix}.{e.__cloudevent__type__}"
        spec_version = CloudEventSpecVersion.v1_0
        time = datetime.datetime.now()
        subject = e.aggregate_id
        sequencetype = None
        sequence = None
        cloud_event = CloudEvent(id_, source, type_str, spec_version, sequencetype, sequence, time, subject, data=e)
        self.cloud_event_bus.output_stream.on_next(cloud_event)
