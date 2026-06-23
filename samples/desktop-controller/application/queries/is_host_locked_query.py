import logging
import uuid
from dataclasses import dataclass

from neuroglia.core.operation_result import OperationResult
from neuroglia.mediation.mediator import Query, QueryHandler
from neuroglia.serialization.json import JsonSerializer

from application.services import DockerHostCommandRunner
from domain.models import HostIslocked
from integration.services import HostCommand

log = logging.getLogger(__name__)


@dataclass
class IsHostLockedQuery(Query[OperationResult[str]]):
    file_name: str = "/tmp/is_locked.json"


class IsHostLockedQueryHandler(QueryHandler[IsHostLockedQuery, OperationResult[str]]):
    """Represents the service used to handle IsHostLockedQuery instances"""

    json_serializer: JsonSerializer
    docker_host_command_runner: DockerHostCommandRunner

    def __init__(self, docker_host_command_runner: DockerHostCommandRunner, json_serializer: JsonSerializer):
        self.json_serializer = json_serializer
        self.docker_host_command_runner = docker_host_command_runner

    async def handle_async(self, query: IsHostLockedQuery) -> OperationResult[str]:
        command_line = HostCommand()
        data = {}
        try:
            # REPLACE WITH REPO!
            id = str(uuid.uuid4()).split("-")[0]
            line = f"cat {query.file_name}"
            command_line.line = line
            data = await self.docker_host_command_runner.run(command_line)
            ishostlocked_json_txt = "".join(data["stdout"])  # data["stdout"] is split by lines...
            ishostlocked_dict = self.json_serializer.deserialize_from_text(ishostlocked_json_txt)
            ishostlocked_dict.update({"id": id})
            if ishostlocked_dict:
                ishostlocked = HostIslocked(**ishostlocked_dict)
                return self.ok(ishostlocked)

        except Exception as ex:
            return self.bad_request(f"Exception when trying to read the {query.file_name}: CLI#{command_line.line}: {data}: {ex}")
