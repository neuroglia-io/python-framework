import logging
import uuid

from neuroglia.core.operation_result import OperationResult
from neuroglia.mediation.mediator import Query, QueryHandler
from neuroglia.serialization.json import JsonSerializer

from application.services import DockerHostCommandRunner
from domain.models.user_info import UserInfo
from integration.services import HostCommand

log = logging.getLogger(__name__)


class ReadUserInfoQuery(Query[OperationResult[str]]):
    file_name: str = "/tmp/userinfo.json"


class UserInfoQueriesHandler(QueryHandler[ReadUserInfoQuery, OperationResult[str]]):
    """Represents the service used to handle TestFileFromHostQueries instances"""

    def __init__(self, docker_host_command_runner: DockerHostCommandRunner, json_serializer: JsonSerializer):
        self.json_serializer = json_serializer
        self.docker_host_command_runner = docker_host_command_runner

    json_serializer: JsonSerializer
    docker_host_command_runner: DockerHostCommandRunner

    async def handle_async(self, query: ReadUserInfoQuery) -> OperationResult[str]:
        command_line = HostCommand()
        data = {}
        try:
            id = str(uuid.uuid4()).split("-")[0]
            line = f"cat {query.file_name}"
            command_line.line = line
            data = await self.docker_host_command_runner.run(command_line)
            userinfo_json_txt = "".join(data["stdout"])  # data["stdout"] is split by lines...
            userinfo_dict = self.json_serializer.deserialize_from_text(userinfo_json_txt)
            if userinfo_json_txt:
                userinfo = UserInfo(id=id, **userinfo_dict)
                return self.ok(userinfo)

        except Exception as ex:
            return self.bad_request(f"Exception when trying to run a shell script on the host: {command_line.line}: {data}: {ex}")
