import logging
import uuid
from dataclasses import dataclass

from neuroglia.core import OperationResult
from neuroglia.mapping.mapper import map_from, map_to
from neuroglia.mediation import Command, CommandHandler
from neuroglia.serialization.json import JsonSerializer

from application.services import DockerHostCommandRunner
from integration.models import SetUserInfoCommandDto, UserInfoDto
from integration.services import HostCommand

log = logging.getLogger(__name__)


@map_from(SetUserInfoCommandDto)
@map_to(SetUserInfoCommandDto)
@dataclass
class SetUserInfoCommand(Command):
    candidate_name: str


class UserInfoCommandsHandler(CommandHandler[SetUserInfoCommand, OperationResult[UserInfoDto]]):
    """Represents the service used to handle UserInfo-related Commands"""

    def __init__(self, docker_host_command_runner: DockerHostCommandRunner, json_serializer: JsonSerializer):
        self.docker_host_command_runner = docker_host_command_runner
        self.json_serializer = json_serializer

    docker_host_command_runner: DockerHostCommandRunner
    json_serializer: JsonSerializer

    async def handle_async(self, command: SetUserInfoCommand) -> OperationResult[UserInfoDto]:
        fake_session_id = str(uuid.uuid4()).split("-")[0]
        command_line = HostCommand()
        data = {}
        try:
            log.debug(f"Creating the userinfo file for sid: {fake_session_id} candidate: {command.candidate_name}")
            user_info = {"session_id": fake_session_id, "username": command.candidate_name}
            user_info_json = self.json_serializer.serialize_to_text(user_info)
            command_line.line = f"""echo '{user_info_json}' > /tmp/userinfo.json"""
            data = await self.docker_host_command_runner.run(command_line)
            return self.created(data)

        except Exception as ex:
            return self.bad_request(f"Exception when creating a UserInfo.candidate_name={command.candidate_name}: {fake_session_id} {command_line} {ex}")
