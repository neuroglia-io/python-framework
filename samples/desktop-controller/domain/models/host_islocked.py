import logging
from dataclasses import dataclass

from neuroglia.data.abstractions import Entity
from neuroglia.mapping.mapper import map_from, map_to

from integration.models import HostIslockedDto

log = logging.getLogger(__name__)


@map_from(HostIslockedDto)
@map_to(HostIslockedDto)
@dataclass
class HostIslocked(Entity[str]):
    id: str

    is_locked: bool
