import datetime
import logging
from dataclasses import dataclass
from typing import Optional

from neuroglia.data.abstractions import Entity
from neuroglia.mapping.mapper import map_from, map_to

from integration.enums.host import HostState
from integration.models import HostInfoDto

log = logging.getLogger(__name__)


@map_from(HostInfoDto)
@map_to(HostInfoDto)
@dataclass
class HostInfo(Entity[str]):
    id: str

    desktop_id: str

    created_at: datetime.datetime = datetime.datetime.now()

    last_modified: datetime.datetime = datetime.datetime.now()

    desktop_name: Optional[str] = "default"

    host_ip_address: Optional[str] = "TBD"

    state: HostState = HostState.PENDING

    def try_set_state(self, state: HostState) -> bool:
        res = True
        if self.state != state:
            match (self.state, state):
                case (HostState.PENDING, HostState.REGISTRATION_REQUESTED):
                    self.state = state
                case (HostState.REGISTRATION_REQUESTED, HostState.UNREGISTERED):
                    self.state = state
                case (HostState.REGISTRATION_REQUESTED, HostState.PENDING):
                    self.state = state
                case (HostState.REGISTRATION_REQUESTED, HostState.UNREGISTERED):
                    self.state = state
                case (HostState.REGISTRATION_REQUESTED, HostState.REGISTERED):
                    self.state = state
                case (HostState.REGISTERED, HostState.READY):
                    self.state = state
                case (HostState.REGISTERED, HostState.LOCKED):
                    self.state = state
                case (HostState.READY, HostState.BUSY):
                    self.state = state
                case (HostState.READY, HostState.LOCKED):
                    self.state = state
                case (HostState.READY, HostState.UNREGISTERED):
                    self.state = state
                case (HostState.BUSY, HostState.READY):
                    self.state = state
                case (HostState.BUSY, HostState.LOCKED):
                    self.state = state
                case (HostState.BUSY, HostState.UNREGISTERED):
                    self.state = state
                case (HostState.UNREGISTERED, HostState.REGISTRATION_REQUESTED):
                    self.state = state
                case (HostState.UNREGISTERED, HostState.REGISTERED):
                    self.state = state
                case _:
                    log.info(f"Invalid state transition from {self.state} to {state}")
                    res = False
        if res:
            log.debug(f"Valid state transition from {self.state} to {state}")
        return res

    def set_desktop_id(self, id: str) -> bool:
        # TODO: add any biz/logic/rule per state?
        # add audit?
        log.debug(f"set_desktop_id({id})")
        self.desktop_id = id
        self.last_modified = datetime.datetime.now()
        return True

    def set_desktop_name(self, name: str) -> bool:
        # TODO: add any biz/logic/rule per state?
        # add audit?
        log.debug(f"set_desktop_name({name})")
        self.desktop_name = name
        self.last_modified = datetime.datetime.now()
        return True

    def set_host_ip_address(self, ip_address: str) -> bool:
        # TODO: add any biz/logic/rule per state?
        # add audit?
        log.debug(f"set_host_ip_address({ip_address})")
        self.host_ip_address = ip_address
        self.last_modified = datetime.datetime.now()
        return True
