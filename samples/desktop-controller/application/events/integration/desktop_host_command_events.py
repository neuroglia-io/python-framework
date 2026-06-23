import datetime
import logging
from dataclasses import dataclass

from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.integration.models import IntegrationEvent

log = logging.getLogger(__name__)


@cloudevent("registration-requested.v1")
@dataclass
class DesktopHostRegistrationRequestedIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    created_at: datetime.datetime
    last_modified: datetime.datetime
    desktop_id: str
    desktop_name: str
    host_ip_address: str
    state: str


@cloudevent("registration-completed.v1")
@dataclass
class DesktopHostRegisteredIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    created_at: datetime.datetime
    last_modified: datetime.datetime


@cloudevent("desktop.controller.registered.v1")
@dataclass
class DesktopControllerRegisteredIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    created_at: datetime.datetime
    last_modified: datetime.datetime
    desktop_id: str
    desktop_name: str
    host_ip_address: str


@cloudevent("desktop.host-command.received.v1")
@dataclass
class DesktopHostCommandReceivedIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    created_at: datetime.datetime
    last_modified: datetime.datetime
    command_line: str

    def __init__(self, aggregate_id, command_line):
        self.aggregate_id = aggregate_id
        self.command_line = command_line
        self.created_at = datetime.datetime.now()
        self.last_modified = self.created_at
        super().__init__(aggregate_id=self.aggregate_id, created_at=self.created_at)


@cloudevent("desktop.host-command.executed.v1")
@dataclass
class DesktopHostCommandExecutedIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    created_at: datetime.datetime
    last_modified: datetime.datetime
    command_line: str
    stdout: str
    stderr: str

    def __init__(self, aggregate_id, command_line, stdout, stderr):
        self.aggregate_id = aggregate_id
        self.command_line = command_line
        self.stdout = stdout
        self.stderr = stderr
        self.created_at = datetime.datetime.now()
        self.last_modified = self.created_at
        super().__init__(aggregate_id=self.aggregate_id, created_at=self.created_at)
