import logging
from dataclasses import dataclass
from typing import Generic, Optional

from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.serialization.json import JsonSerializer

from integration.services.secured_docker_host import HostCommand, SecuredHost

log = logging.getLogger(__name__)


class RemoteFileSystemRepositoryException(Exception):
    pass


@dataclass
class RemoteFileSystemRepositoryOptions(Generic[TEntity, TKey]):
    """Represents the options used to configure a Redis repository"""

    base_folder: str
    """ Gets the base folder of the remote file-system fro where to start."""


class RemoteFileSystemRepository(Generic[TEntity, TKey], Repository[TEntity, TKey]):
    """Represents a Remote File-System' implementation of the repository Interface."""

    _entity_type: type[TEntity]
    _key_type: type[TKey]
    _options: RemoteFileSystemRepositoryOptions
    _serializer: JsonSerializer
    _secured_host: SecuredHost

    def __init__(self, options: RemoteFileSystemRepositoryOptions, serializer: JsonSerializer, secured_host: SecuredHost):
        """Initializes a new Redis repository"""
        self._options = options
        self._serializer = serializer
        self._secured_host = secured_host

    async def contains_async(self, id: TKey) -> bool:
        """Determines whether or not the repository contains a non-empty file named as 'id'."""
        file_name = self._file_name(id)
        cmd = HostCommand(line=f"file {file_name}")
        await self._secured_host.connect()
        std_out, std_err = await self._secured_host.execute_command(cmd)
        await self._secured_host.close()
        if not len(std_out) or std_err or "empty" in std_out or "No such file" in std_out:
            log.debug(f"contains_async({id}) = False: {std_out}")
            return False
        return True

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Gets the entity with the specified id, if any"""
        file_name = self._file_name(id)
        cmd = HostCommand(line=f"cat {file_name}")
        await self._secured_host.connect()
        std_out, std_err = await self._secured_host.execute_command(cmd)
        await self._secured_host.close()
        if len(std_out) and not std_err:
            log.debug(f"get_sync: {std_out}")
            entity_json_txt = "".join(std_out)  # std_out may be split by lines...
            entity = self._serializer.deserialize_from_text(entity_json_txt, self._get_entity_type())
            return entity
        raise RemoteFileSystemRepositoryException(f"Exception when get_async(id={str(id)}): std_out={std_out} std_err={std_err}")

    async def add_async(self, entity: TEntity) -> TEntity:
        """Adds the specified entity"""
        file_name = self._file_name(entity.id)
        entity_json = self._serializer.serialize_to_text(entity)
        cmd = HostCommand(line=f"""echo '{entity_json}' > {file_name}""")
        await self._secured_host.connect()
        std_out, std_err = await self._secured_host.execute_command(cmd)
        # successful command output is empty!
        await self._secured_host.close()
        if not std_out and not std_err:
            log.debug(f"add_async: succeeded!")
            return entity
        raise RemoteFileSystemRepositoryException(f"Exception when add_async(id={entity.id}): std_out={std_out} std_err={std_err}")

    async def update_async(self, entity: TEntity) -> TEntity:
        """Persists the changes that were made to the specified entity"""
        """ In this case, its just an alias to add_async """
        return await self.add_async(entity)

    async def remove_async(self, id: TKey) -> None:
        """Removes the entity with the specified key"""

    def _file_name(self, id: TKey) -> str:
        entity_type_name = self._get_entity_type().__name__.lower()
        return f"{self._options.base_folder}/{entity_type_name}/{str(id)}.json"

    def _get_entity_type(self) -> str:
        return self.__orig_class__.__args__[0]

    @staticmethod
    def configure(builder: ApplicationBuilderBase, entity_type: type, key_type: type) -> ApplicationBuilderBase:
        builder.services.try_add_singleton(RemoteFileSystemRepositoryOptions, singleton=RemoteFileSystemRepositoryOptions(base_folder=builder.settings.remotefs_base_folder))
        builder.services.try_add_singleton(RemoteFileSystemRepository[entity_type, key_type], implementation_factory=lambda provider: provider.get_required_service(RemoteFileSystemRepository[entity_type, key_type]))
        builder.services.try_add_scoped(Repository[entity_type, key_type], RemoteFileSystemRepository[entity_type, key_type])
        return builder
