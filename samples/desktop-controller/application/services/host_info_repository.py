from neuroglia.serialization.json import JsonSerializer

from domain.models.host_info import HostInfo
from integration.services.remote_file_system_repository import (
    RemoteFileSystemRepository,
    RemoteFileSystemRepositoryOptions,
)
from integration.services.secured_docker_host import SecuredDockerHost

# UNUSED!


class HostInfoRepository(RemoteFileSystemRepository[HostInfo, str]):
    def __init__(self, options: RemoteFileSystemRepositoryOptions, serializer: JsonSerializer, secured_docker_host: SecuredDockerHost):
        super().__init__(options=options, serializer=serializer, secured_host=secured_docker_host)
