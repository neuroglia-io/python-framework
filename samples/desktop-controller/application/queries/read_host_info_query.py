import logging
import uuid
from dataclasses import dataclass

from neuroglia.core.operation_result import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Query, QueryHandler
from neuroglia.serialization.json import JsonSerializer

from application.exceptions import ApplicationException
from domain.models import HostInfo
from integration.models import HostInfoDto
from integration.services import HostCommand
from integration.services.remote_file_system_repository import Repository

log = logging.getLogger(__name__)


@dataclass
class ReadHostInfoQuery(Query[OperationResult[str]]):
    pass


class ReadHostInfoQueryHandler(QueryHandler[ReadHostInfoQuery, OperationResult[str]]):
    """Represents the service used to handle ReadHostInfoQuery instances"""

    mapper: Mapper
    json_serializer: JsonSerializer
    host_info_repo: Repository[HostInfo, str]

    def __init__(self, mapper: Mapper, json_serializer: JsonSerializer, host_info_repo: Repository[HostInfo, str]):
        self.mapper = mapper
        self.json_serializer = json_serializer
        self.host_info_repo = host_info_repo

    async def handle_async(self, query: ReadHostInfoQuery) -> OperationResult[str]:
        command_line = HostCommand()
        data = {}
        try:
            host_info = None
            id = str(uuid.uuid4()).split("-")[0]
            if not await self.host_info_repo.contains_async("current"):
                host_info = HostInfo(id="current", desktop_id=id, desktop_name="default")
                host_info = await self.host_info_repo.add_async(host_info)

            host_info: HostInfo = await self.host_info_repo.get_async("current")

            if host_info:
                # content = self.json_serializer.serialize_to_text(host_info)
                # content = self.mapper.map(host_info, HostInfoDto)  # Not sure why the mapper fails here
                return self.ok(HostInfoDto(id=host_info.id, created_at=host_info.created_at, last_modified=host_info.last_modified, desktop_id=host_info.desktop_id, desktop_name=host_info.desktop_name, host_ip_address=host_info.host_ip_address, state=host_info.state.value))
            else:
                return self.bad_request("Exception when reading the current HostInfo!")

        except ApplicationException as ex:
            return self.bad_request(f"Exception when handling {query}: CLI#{command_line.line}: {data}: {ex}")


# Not sure why the mediator.get_services doesnt find RequestHandlers when multiple requests are bundled together like EventHandlers do...
#
# class HostInfoQueriesHandler(QueryHandler[(ReadHostInfoQuery | IsHostLockedQuery), OperationResult[str]]):
#     """Represents the service used to handle HostInfo Queries instances"""

#     def __init__(self, docker_host_command_runner: DockerHostCommandRunner, json_serializer: JsonSerializer):
#         self.json_serializer = json_serializer
#         self.docker_host_command_runner = docker_host_command_runner

#     json_serializer: JsonSerializer
#     docker_host_command_runner: DockerHostCommandRunner

#     @dispatch
#     async def handle_async(self, query: ReadHostInfoQuery) -> OperationResult[str]:
#         command_line = HostCommand()
#         data = {}
#         try:
#             # TODO FIX THIS VIA REPO!
#             id = str(uuid.uuid4()).split("-")[0]
#             line = f"cat {query.file_name}"
#             command_line.line = line
#             data = await self.docker_host_command_runner.run(command_line)
#             hostinfo_json_txt = "".join(data["stdout"])  # data["stdout"] is split by lines...
#             hostinfo_dict = self.json_serializer.deserialize_from_text(hostinfo_json_txt)
#             hostinfo_dict.update({"id": id})  # TODO: REMOVE, should be persisted!!!
#             if hostinfo_dict:
#                 userinfo = HostInfo(**hostinfo_dict)
#                 return self.ok(userinfo)
#             raise ApplicationException(f"The command line {line} failed for some reason: {data}")

#         except Exception as ex:
#             return self.bad_request(f"Exception when trying to read the {query.file_name}: CLI#{command_line.line}: {data}: {ex}")

#     @dispatch
#     async def handle_async(self, query: IsHostLockedQuery) -> OperationResult[str]:
#         command_line = HostCommand()
#         data = {}
#         try:
#             id = str(uuid.uuid4()).split("-")[0]
#             line = f"cat {query.file_name}"
#             command_line.line = line
#             data = await self.docker_host_command_runner.run(command_line)
#             hostinfo_json_txt = "".join(data["stdout"])  # data["stdout"] is split by lines...
#             hostinfo_dict = self.json_serializer.deserialize_from_text(hostinfo_json_txt)
#             hostinfo_dict.update({"id": id})
#             if hostinfo_dict:
#                 userinfo = HostInfo(**hostinfo_dict)
#                 return self.ok(userinfo)

#         except Exception as ex:
#             return self.bad_request(f"Exception when trying to read the {query.file_name}: CLI#{command_line.line}: {data}: {ex}")
