import logging

import paramiko
from fastapi.middleware.cors import CORSMiddleware
from neuroglia.eventing.cloud_events.infrastructure import CloudEventMiddleware
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
)
from neuroglia.hosting.abstractions import HostedService
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator, RequestHandler
from neuroglia.serialization.json import JsonSerializer

from api.services.logger import configure_logging
from api.services.openapi import set_oas_description
from application.queries import (
    IsHostLockedQueryHandler,
    ReadHostInfoQueryHandler,
    TestFileFromHostQueriesHandler,
    UserInfoQueriesHandler,
)
from application.services import DesktopRegistrator, DockerHostCommandRunner
from application.settings import DesktopControllerSettings, app_settings
from domain.models.host_info import HostInfo
from integration.services import DockerHostSshClientSettings, SecuredDockerHost
from integration.services.remote_file_system_repository import (
    RemoteFileSystemRepository,
)
from integration.services.secured_docker_host import SecuredHost, SshClientSettings

configure_logging()
log = logging.getLogger(__name__)
log.debug("Bootstraping the app...")

# app' constants
application_modules = [
    "application.mapping",
    "application.commands",
    "application.queries",
    "application.events",
    "application.services",
]

# app' settings: from api.settings import app_settings
builder = WebApplicationBuilder()
builder.settings = app_settings

# required shared resources
Mapper.configure(builder, application_modules)
Mediator.configure(builder, application_modules)
JsonSerializer.configure(builder)
CloudEventPublisher.configure(builder)

# custom shared resources
RemoteFileSystemRepository.configure(builder, entity_type=HostInfo, key_type=str)

builder.services.add_singleton(DesktopControllerSettings, singleton=app_settings)
builder.services.add_singleton(HostedService, DesktopRegistrator)
builder.services.add_singleton(DockerHostSshClientSettings, singleton=DockerHostSshClientSettings(username=app_settings.docker_host_user_name, hostname=app_settings.docker_host_host_name))
builder.services.add_singleton(SshClientSettings, singleton=SshClientSettings(username=app_settings.docker_host_user_name, hostname=app_settings.docker_host_host_name))  # used by the RemoteFileSystemRepository
builder.services.add_scoped(paramiko.SSHClient, implementation_type=paramiko.SSHClient)
builder.services.add_scoped(SecuredDockerHost, implementation_type=SecuredDockerHost)
builder.services.add_scoped(SecuredHost, implementation_type=SecuredDockerHost)
builder.services.add_scoped(DockerHostCommandRunner, implementation_type=DockerHostCommandRunner)

# FIX: mediator issue TBD
builder.services.add_transient(RequestHandler, TestFileFromHostQueriesHandler)
builder.services.add_transient(RequestHandler, UserInfoQueriesHandler)
builder.services.add_transient(RequestHandler, ReadHostInfoQueryHandler)
builder.services.add_transient(RequestHandler, IsHostLockedQueryHandler)
# builder.services.add_transient(RequestHandler, HostIslockedQueriesHandler)

builder.add_controllers(["api.controllers"])

app = builder.build()

# Custom App
app.settings = app_settings
set_oas_description(app, app_settings)

# app.add_middleware(ExceptionHandlingMiddleware, service_provider=app.services)
app.add_middleware(CloudEventMiddleware, service_provider=app.services)
app.use_controllers()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.run()
log.debug("App is ready to rock.")
