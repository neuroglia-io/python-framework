import datetime

from pydantic import BaseModel

from integration.enums.host import HostState


class HostInfoDto(BaseModel):
    """Represents the Host Info file content of the Desktop."""

    id: str

    created_at: datetime.datetime

    last_modified: datetime.datetime

    desktop_id: str

    desktop_name: str

    host_ip_address: str

    state: HostState = HostState.PENDING


class SetHostInfoCommandDto(BaseModel):
    """Represents the command used to set the Host Info of the Desktop."""

    desktop_id: str

    desktop_name: str

    host_ip_address: str = "TBD"

    state: HostState = HostState.PENDING
