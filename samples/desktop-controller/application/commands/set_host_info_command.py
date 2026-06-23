import logging
from dataclasses import dataclass

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mapping.mapper import Mapper, map_from, map_to
from neuroglia.mediation import Command, CommandHandler
from neuroglia.serialization.json import JsonSerializer

from application.exceptions import ApplicationException
from application.settings import DesktopControllerSettings
from domain.models.host_info import HostInfo
from integration.enums.host import HostState
from integration.models import HostInfoDto, SetHostInfoCommandDto

log = logging.getLogger(__name__)


@map_from(SetHostInfoCommandDto)
@map_to(SetHostInfoCommandDto)
@dataclass
class SetHostInfoCommand(Command):
    desktop_id: str

    desktop_name: str

    host_ip_address: str = "TBD"

    state: HostState = HostState.PENDING


class SetHostInfoCommandHandler(CommandHandler[SetHostInfoCommand, OperationResult[HostInfoDto]]):
    """Represents the service used to handle HostInfo-related Commands"""

    mapper: Mapper
    json_serializer: JsonSerializer
    host_info_repo: Repository[HostInfo, str]
    app_settings: DesktopControllerSettings

    def __init__(self, mapper: Mapper, json_serializer: JsonSerializer, host_info_repo: Repository[HostInfo, str], app_settings: DesktopControllerSettings):
        self.mapper = mapper
        self.json_serializer = json_serializer
        self.host_info_repo = host_info_repo
        self.app_settings = app_settings

    async def handle_async(self, command: SetHostInfoCommand) -> OperationResult[HostInfoDto]:
        updated = False
        host_info = None
        try:
            host_info = await self.host_info_repo.get_async("current")
            if host_info is None:
                raise ApplicationException(f"Current HostInfo is not set!")

            if host_info.state != command.state:
                log.info(f"Desktop State changed from {host_info.state} to {command.state}")
                updated = updated or host_info.try_set_state(command.state)

            if host_info.desktop_id != command.desktop_id:
                log.info(f"Desktop ID changed from {host_info.desktop_id} to {command.desktop_id}")
                updated = updated or host_info.set_desktop_id(command.desktop_id)

            if host_info.desktop_name != command.desktop_name:
                log.info(f"Desktop Name changed from {host_info.desktop_name} to {command.desktop_name}")
                updated = updated or host_info.set_desktop_name(command.desktop_name)

            if host_info.host_ip_address != command.host_ip_address:
                log.info(f"Desktop Host IP Address changed from {host_info.host_ip_address} to {command.host_ip_address}")
                updated = updated or host_info.set_host_ip_address(command.host_ip_address)

            if updated:
                host_info: HostInfo = await self.host_info_repo.update_async(host_info)

            return self.ok(HostInfoDto(id=host_info.id, created_at=host_info.created_at, last_modified=host_info.last_modified, desktop_id=host_info.desktop_id, desktop_name=host_info.desktop_name, host_ip_address=host_info.host_ip_address, state=host_info.state.value))

        except ApplicationException as ex:
            return self.bad_request(f"Exception when creating a HostInfo.desktop_name={command.desktop_name}: desktop_id={command.desktop_id} Exception={ex}")
