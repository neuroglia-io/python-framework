import datetime
from dataclasses import dataclass

from neuroglia.data.abstractions import Entity
from neuroglia.mapping.mapper import map_from, map_to

from integration.models import UserInfoDto


@map_from(UserInfoDto)
@map_to(UserInfoDto)
@dataclass
class UserInfo(Entity[str]):
    id: str

    session_id: str

    username: str

    created_at: datetime.datetime = datetime.datetime.now()

    last_modified: datetime.datetime = datetime.datetime.now()
