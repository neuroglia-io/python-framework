import asyncio
import datetime
from typing import Optional
import uuid
import logging
import redis

from dataclasses import asdict, dataclass
from pathlib import Path

from neuroglia.dependency_injection.service_provider import (
    ServiceCollection,
    ServiceProvider,
)
from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.integration.models import IntegrationEvent
from neuroglia.serialization.abstractions import Serializer, TextSerializer
from neuroglia.serialization.json import JsonSerializer
import urllib.parse

from application.events.integration import (
    PromptDataProcessedIntegrationEventV1,
    PromptFaultedIntegrationEventV1,
    PromptSubmittedIntegrationEventV1,
)
from application.exceptions import ApplicationException
from application.services.background_tasks_scheduler import (
    ScheduledBackgroundJob,
    backgroundjob,
)
from application.settings import app_settings
from application.services.utils import get_human_readable_file_size, get_file_size
from domain.models.prompt import Prompt, PromptResponse
from integration import IntegrationException
from integration.services.cache_repository import AsyncStringCacheRepository, CacheRepositoryOptions, CacheClientPool
from integration.services.local_file_system_manager import LocalFileSystemManager, LocalFileSystemManagerSettings
from integration.services.mosaic_api_client import MosaicApiClient, MosaicApiClientOAuthOptions

log = logging.getLogger(__name__)


@backgroundjob(type="scheduled")
@dataclass
class CreatePromptJob(ScheduledBackgroundJob):

    _service_provider: ServiceProvider
    """ Gets the service provider used to resolve the dependencies """

    cloud_event_bus: CloudEventBus
    """ Gets the service used to observe the cloud events consumed and produced by the application """

    cloud_event_publishing_options: CloudEventPublishingOptions
    """ Gets the options used to configure how the application should publish cloud events """

    repository: AsyncStringCacheRepository[Prompt, str]
    """ Gets the repository used to manage the prompt records """

    local_file_system_manager: LocalFileSystemManager

    mosaic_api_client: MosaicApiClient

    # def __init__(
    #     self,
    #     cloud_event_bus: CloudEventBus,
    #     cloud_event_publishing_options: CloudEventPublishingOptions,
    #     repository: AsyncStringCacheRepository[Prompt, str],
    #     local_file_system_manager: LocalFileSystemManager,
    # ):
    #     pass
    #     # Constructor never called directly!

    async def run_at(self, aggregate_id: str) -> None:
        """Called when the job is executed by the scheduler based on the specified schedule"""
        log.debug(f"Running the CreatePromptJob for prompt {aggregate_id}")

        # Configure the dependencies required by the BackgroundJob
        self.configure()

        try:
            # Get the prompt from the DB
            async with self.repository as repo:
                prompt = await repo.get_async(aggregate_id)
                if prompt is None:
                    log.warning(f"Prompt not found: {aggregate_id}")
                    raise ApplicationException(f"Prompt not found: {aggregate_id}")
                log.debug(f"Prompt found: {aggregate_id}: {prompt}")

            if not prompt.start_preparing():
                raise ApplicationException(f"Prompt not prepared: {aggregate_id}")

            # Process Data, if any (PLACEHOLDER)
            if prompt.request.has_valid_data_url():
                log.debug(f"Downloading Prompt data from {prompt.request.data_url}...")
                local_file_path = self.local_file_system_manager.get_file_path(f"{aggregate_id}.zip")
                if "mosaic" in prompt.request.data_url:
                    if self.mosaic_api_client.download_file_locally(prompt.request.data_url, local_file_path):
                        file_size = self.local_file_system_manager.get_file_size(Path(local_file_path))
                        log.debug(f"Downloaded Prompt data in {local_file_path}: {file_size}")
                else:
                    local_file_path = await self.local_file_system_manager.download_file(prompt.request.data_url, local_file_path)
                    file_size = self.local_file_system_manager.get_file_size(Path(local_file_path))
                    log.debug(f"Downloaded Prompt data in {local_file_path}: {file_size}")

                log.debug(f"Uploading Prompt data from {local_file_path} to GenAI service...")
                # remote_file_uri = self.genai_service_api_client.upload_prompt_package(aggregate_id, local_file_path)
                remote_file_uri = f"http://genai-agent.mozart/api/v1/data/{aggregate_id}"
                # remote_prompt_context = self.genai_service_api_client.get_prompt_context(aggregate_id)
                remote_prompt_context = {"prompt_context": "item", "process_id": "123456", "bucket_name": aggregate_id}
                await asyncio.sleep(3)
                log.debug(f"Uploaded Prompt data to GenAI service: {remote_file_uri}")

                if prompt.mark_prepared(bucket_name=aggregate_id):
                    ev = asdict(prompt)
                    ev.update({"request_id": prompt.request.request_id, "process_id": remote_prompt_context["process_id"], "data_url": prompt.request.data_url, "object_url": remote_file_uri})
                    await self.emit_event(f"PromptDataProcessed", **ev)
                else:
                    raise ApplicationException(f"Prompt {aggregate_id} not prepared: {asdict(prompt)}")
            else:
                prompt.mark_prepared()

            if prompt.is_prepared() and not prompt.is_submitted():
                log.debug(f"Submitting the prompt {aggregate_id} to GenAI service...")
                # res = await self.genai_service_api_client.submit_prompt(prompt_dict)
                await asyncio.sleep(3)
                res = {"process_id": "234567"}
                if prompt.mark_submitted():
                    ev = asdict(prompt)
                    ev.update({"request_id": prompt.request.request_id, "process_id": res["process_id"]})
                    await self.emit_event("PromptSubmitted", **ev)
                    log.debug(f"Prompt {aggregate_id} submitted to GenAI (process_id: {res['process_id']})")

            # Update the cache
            async with self.repository as repo:
                await repo.update_async(prompt)
                log.debug(f"Cache updated for {aggregate_id}")
            log.debug(f"Done")

        except Exception as e:
            log.error(f"An error occurred while processing the prompt: {e}")
            await self.emit_event("PromptFaulted", **{"aggregate_id": aggregate_id, "error": str(e)})

    def configure(self):
        """Configure the dependencies required by the BackgroundJob"""
        self._service_provider = CreatePromptJob._build_services()
        self.cloud_event_bus = self._service_provider.get_required_service(CloudEventBus)
        self.cloud_event_publishing_options = self._service_provider.get_required_service(CloudEventPublishingOptions)
        self.repository = self._service_provider.get_required_service(AsyncStringCacheRepository[Prompt, str])
        self.local_file_system_manager = self._service_provider.get_required_service(LocalFileSystemManager)
        self.mosaic_api_client = self._service_provider.get_required_service(MosaicApiClient)

    async def publish_cloud_event_async(self, ev: IntegrationEvent) -> bool:
        """Converts the specified command into a new integration event, then publishes it as a cloud event"""
        try:
            id_ = str(uuid.uuid4()).replace("-", "")
            source = self.cloud_event_publishing_options.source
            type_prefix = self.cloud_event_publishing_options.type_prefix
            type_str = f"{type_prefix}.{ev.__cloudevent__type__}"
            spec_version = CloudEventSpecVersion.v1_0
            time = datetime.datetime.now()
            subject = ev.aggregate_id
            sequencetype = None
            sequence = None
            cloud_event = CloudEvent(id_, source, type_str, spec_version, sequencetype, sequence, time, subject, data=asdict(ev))
            self.cloud_event_bus.output_stream.on_next(cloud_event)
            return True
        except Exception as e:
            raise IntegrationException(f"Failed to publish a cloudevent {ev}: Exception {e}")

    async def emit_event(self, event_type: str, **kwargs) -> None:
        try:
            match event_type:
                case "PromptFaulted":
                    await self.publish_cloud_event_async(
                        PromptFaultedIntegrationEventV1(
                            aggregate_id=kwargs.get("aggregate_id", "unknown"),
                            created_at=kwargs.get("created_at", datetime.datetime.now()),
                            request_id=kwargs.get("request_id", "unknown"),
                            error=kwargs.get("error", "Fault"),
                            details=kwargs.get("details", "No Details."),
                        )
                    )
                case "PromptDataProcessed":
                    if "data_url" not in kwargs:
                        raise ApplicationException("The data URL is missing.")
                    if "object_url" not in kwargs:
                        raise ApplicationException("The object URL is missing.")
                    if "process_id" not in kwargs:
                        raise ApplicationException("The process_id is missing.")
                    await self.publish_cloud_event_async(
                        PromptDataProcessedIntegrationEventV1(
                            aggregate_id=kwargs.get("aggregate_id", "unknown_aggregate_id"),
                            created_at=kwargs.get("created_at", datetime.datetime.now()),
                            request_id=kwargs.get("request_id", "unknown_request_id"),
                            process_id=kwargs.get("process_id", "unknown_process_id"),
                            data_url=kwargs.get("data_url", "unknown_data_url"),
                            object_url=kwargs.get("object_url", "unknown_object_url"),
                        )
                    )
                case "PromptSubmitted":
                    await self.publish_cloud_event_async(
                        PromptSubmittedIntegrationEventV1(
                            aggregate_id=kwargs.get("aggregate_id", "unknown_aggregate_id"),
                            created_at=kwargs.get("created_at", datetime.datetime.now()),
                            request_id=kwargs.get("request_id", "unknown_request_id"),
                            process_id=kwargs.get("process_id", "unknown_process_id"),
                        )
                    )
                case _:
                    raise ApplicationException(f"Unknown event type: {event_type}")
        except IntegrationException as e:
            log.warning(f"The Event Gateway is down: {e}")

    @staticmethod
    def _build_services() -> ServiceProvider:
        """Instantiate the services required by the job (as this is running in a separate process)"""
        services = ServiceCollection()
        services.try_add_singleton(JsonSerializer)
        services.try_add_singleton(Serializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        services.try_add_singleton(TextSerializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))

        services.add_transient(CloudEventBus)
        services.add_transient(CloudEventPublishingOptions, lambda: app_settings.cloud_event_publishing_options)

        connection_string_name = "redis"
        connection_string = app_settings.connection_strings.get(connection_string_name, None)
        if connection_string is None:
            raise IntegrationException(f"Missing '{connection_string_name}' connection string in application settings (missing env var CONNECTION_STRINGS: {'redis': 'redis://redis:6379'} ?)")

        redis_database_url = f"{connection_string}/0"
        parsed_url = urllib.parse.urlparse(connection_string)
        redis_host = parsed_url.hostname
        redis_port = parsed_url.port
        if any(item is None for item in [redis_host, redis_port]):
            raise IntegrationException(f"Issue parsing the connection_string '{connection_string}': host:{redis_host} port:{redis_port} database_name: 0")

        pool = redis.ConnectionPool.from_url(redis_database_url, max_connections=app_settings.redis_max_connections)  # type: ignore

        key_type = str
        for entity_type in [Prompt]:
            services.try_add_singleton(CacheRepositoryOptions[entity_type, key_type], singleton=CacheRepositoryOptions[entity_type, key_type](host=redis_host, port=redis_port, connection_string=redis_database_url))  # type: ignore
            services.try_add_singleton(CacheClientPool[entity_type, key_type], singleton=CacheClientPool(pool=pool))  # type: ignore
            services.add_scoped(AsyncStringCacheRepository[entity_type, key_type], AsyncStringCacheRepository[entity_type, key_type])  # type: ignore
            services.add_transient(AsyncStringCacheRepository[entity_type, key_type], AsyncStringCacheRepository[entity_type, key_type])  # type: ignore

        services.try_add_singleton(LocalFileSystemManagerSettings, singleton=LocalFileSystemManagerSettings(tmp_path=app_settings.tmp_path))
        services.try_add_scoped(LocalFileSystemManager, implementation_type=LocalFileSystemManager)

        services.try_add_singleton(MosaicApiClientOAuthOptions, singleton=app_settings.mosaic_oauth_client)
        services.try_add_transient(MosaicApiClient, MosaicApiClient)

        return services.build()
