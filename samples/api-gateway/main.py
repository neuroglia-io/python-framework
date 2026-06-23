import logging

from fastapi.middleware.cors import CORSMiddleware
from neuroglia.eventing.cloud_events.infrastructure import (
    CloudEventIngestor,
    CloudEventMiddleware,
)
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
)
from neuroglia.hosting.abstractions import ApplicationSettings
from neuroglia.hosting.web import ExceptionHandlingMiddleware, WebApplicationBuilder
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator, RequestHandler
from neuroglia.serialization.json import JsonSerializer

from application.queries import (
    GetPromptByIdQueryHandler,
)
from api.services.logger import configure_logging
from api.services.openapi import set_oas_description
from application.settings import AiGatewaySettings, app_settings
from application.services.background_tasks_scheduler import BackgroundTaskScheduler
from domain.models.prompt import Prompt, PromptResponse
from integration.services.cache_repository import AsyncStringCacheRepository
from integration.services.object_storage_client import MinioStorageManager
from integration.services.local_file_system_manager import LocalFileSystemManager
from integration.services.mosaic_api_client import MosaicApiClient

configure_logging()
log = logging.getLogger(__name__)
log.debug("Bootstraping the app...")

# App' constants
database_name = "ai-gateway"
application_modules = [
    "application.commands",
    "application.events.integration",
    "application.mapping",
    "application.queries",
    "application.services",
    "domain.models",
]

builder = WebApplicationBuilder()
builder.settings = app_settings

# Required shared resources
Mapper.configure(builder, application_modules)
Mediator.configure(builder, application_modules)
JsonSerializer.configure(builder)
CloudEventIngestor.configure(builder, ["application.events.integration"])
CloudEventPublisher.configure(builder)

# App Settings
builder.services.add_singleton(AiGatewaySettings, singleton=app_settings)
builder.services.add_singleton(ApplicationSettings, singleton=app_settings)

# Custom Services
AsyncStringCacheRepository.configure(builder, Prompt, str)
BackgroundTaskScheduler.configure(builder, ["application.tasks"])
MinioStorageManager.configure(builder)
LocalFileSystemManager.configure(builder)

# FIX: mediator issue TBD
builder.services.add_transient(RequestHandler, GetPromptByIdQueryHandler)

builder.add_controllers(["api.controllers"])

app = builder.build()

app.settings = app_settings  # type: ignore (monkey patching)
set_oas_description(app, app_settings)

app.add_middleware(ExceptionHandlingMiddleware, service_provider=app.services)
app.add_middleware(CloudEventMiddleware, service_provider=app.services)
app.use_controllers()

# Enable CORS (TODO: add settings to configure allowed_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.run()
log.debug("App is ready to rock.")
