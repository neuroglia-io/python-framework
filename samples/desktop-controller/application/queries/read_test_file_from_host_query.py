import logging

from neuroglia.core.operation_result import OperationResult
from neuroglia.mediation.mediator import Query, QueryHandler

from application.services import DockerHostCommandRunner
from integration.services import HostCommand

log = logging.getLogger(__name__)


class ReadTestFileFromHostQuery(Query[OperationResult[str]]):
    file_name: str = "/tmp/test.txt"


class TestFileFromHostQueriesHandler(QueryHandler[ReadTestFileFromHostQuery, OperationResult[str]]):
    """Represents the service used to handle TestFileFromHostQueries instances"""

    def __init__(self, docker_host_command_runner: DockerHostCommandRunner):
        self.docker_host_command_runner = docker_host_command_runner

    docker_host_command_runner: DockerHostCommandRunner

    async def handle_async(self, query: ReadTestFileFromHostQuery) -> OperationResult[str]:
        command_line = HostCommand()
        data = {}
        try:
            line = f"cat {query.file_name}"
            command_line.line = line
            data = await self.docker_host_command_runner.run(command_line)
            return self.ok(data)

        except Exception as ex:
            return self.bad_request(f"Exception when trying to run a shell script on the host: {command_line.line}: {data}: {ex}")
