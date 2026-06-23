import datetime
import logging
import uuid
from typing import Any

from neuroglia.core.operation_result import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.hosting.abstractions import HostedService
from neuroglia.integration.models import IntegrationEvent
from neuroglia.mediation.mediator import Mediator
from neuroglia.serialization.json import JsonSerializer

from application.events.integration.desktop_host_command_events import (
    DesktopHostRegistrationRequestedIntegrationEventV1,
)
from application.exceptions import ApplicationException
from domain.models import HostInfo
from integration.enums.host import HostState
from integration.models import HostInfoDto

log = logging.getLogger(__name__)
logging.getLogger("paramiko").setLevel(logging.WARNING)


class DesktopRegistrator(HostedService):
    """The service that requests the registration of the DesktopController (simply via Cloudevent!)"""

    mediator: Mediator
    """ Gets the Meditator to run the Query. """

    json_serializer: JsonSerializer
    """ Gets the default JSON serializer. """

    cloud_event_bus: CloudEventBus
    """ Gets the service used to observe the cloud events consumed and produced by the application """

    cloud_event_publishing_options: CloudEventPublishingOptions
    """ Gets the options used to configure how the application should publish cloud events """

    host_info_repo: Repository[HostInfo, str]
    """ The Repository for HostInfo entities."""

    def __init__(self, mediator: Mediator, json_serializer: JsonSerializer, cloud_event_bus: CloudEventBus, cloud_event_publishing_options: CloudEventPublishingOptions, host_info_repo: Repository[HostInfo, str]):
        self.mediator = mediator
        self.json_serializer = json_serializer
        self.cloud_event_bus = cloud_event_bus
        self.cloud_event_publishing_options = cloud_event_publishing_options
        self.host_info_repo = host_info_repo

    async def start_async(self):
        """Starts the program"""
        await self.request_registration()

    async def stop_async(self):
        """Attempts to gracefully stop the program"""
        log.debug(f"TODO: Emit the Unregistration Requested Event!")

    def dispose(self):
        """Disposes of the program's resources"""
        raise NotImplementedError()

    async def request_registration(self) -> Any:
        log.debug(f"Requesting Registration...")
        host_info = await self.get_registry_info()
        if host_info and host_info.try_set_state(HostState.REGISTRATION_REQUESTED):
            # avoid circular import:
            from application.commands import SetHostInfoCommand

            command = SetHostInfoCommand(desktop_id=host_info.desktop_id, desktop_name=host_info.desktop_name, state=host_info.state, host_ip_address=host_info.host_ip_address)
            cmd_op_result: OperationResult = await self.mediator.execute_async(command)
            if cmd_op_result and cmd_op_result.status < 202 and host_info.state == HostState.REGISTRATION_REQUESTED:
                host_info_data = host_info.__dict__
                host_info_data.update({"aggregate_id": host_info_data.pop("id")})  # rename id to aggregate_id
                log.info(f"HostInfo changed to {host_info_data}.")
                await self.publish_cloud_event_async(DesktopHostRegistrationRequestedIntegrationEventV1(**host_info_data))
            else:
                log.warn(f"Host state failed to change to {HostState.REGISTRATION_REQUESTED}: {cmd_op_result}")
            log.debug(f"Sent the Registration Requested Event!")
        else:
            raise ApplicationException(f"Requesting Registration failed...")

    async def get_registry_info(self) -> HostInfo | None:
        # avoid circular import:
        from application.queries.read_host_info_query import ReadHostInfoQuery

        query = ReadHostInfoQuery()
        res: OperationResult = await self.mediator.execute_async(query)

        if res.status == 200 and "data" in dir(res):
            host_info_dto: HostInfoDto = res.data
            log.debug(f"get_registry_info: {res.data} {type(res.data)}")
            return HostInfo(id=host_info_dto.id, desktop_id=host_info_dto.desktop_id, created_at=host_info_dto.created_at, last_modified=host_info_dto.last_modified, desktop_name=host_info_dto.desktop_name, host_ip_address=host_info_dto.host_ip_address, state=host_info_dto.state)
        else:
            raise ApplicationException(f"Get HostInfo failed: {res.status} {res.title}: {res.detail}")

    async def publish_cloud_event_async(self, e: IntegrationEvent):
        """Converts the specified integration event as a cloud event and publishes it on the Bus..."""
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
        log.debug(f"Emitted CloudEvent {cloud_event}")
