import asyncio
import datetime
import uuid
import logging
import redis

from dataclasses import asdict, dataclass
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
    PromptFaultedIntegrationEventV1,
    PromptResponseReceivedIntegrationEventV1,
    PromptRespondedIntegrationEventV1,
)
from application.exceptions import ApplicationException
from application.services.background_tasks_scheduler import (
    ScheduledBackgroundJob,
    backgroundjob,
)
from application.settings import app_settings
from domain.models.prompt import Prompt, PromptResponse
from integration import IntegrationException
from integration.services.cache_repository import AsyncStringCacheRepository, CacheRepositoryOptions, CacheClientPool
from integration.services.local_file_system_manager import LocalFileSystemManager

log = logging.getLogger(__name__)


@backgroundjob(type="scheduled")
@dataclass
class HandlePromptResponseJob(ScheduledBackgroundJob):

    _service_provider: ServiceProvider
    """ Gets the service provider used to resolve the dependencies """

    cloud_event_bus: CloudEventBus
    """ Gets the service used to observe the cloud events consumed and produced by the application """

    cloud_event_publishing_options: CloudEventPublishingOptions
    """ Gets the options used to configure how the application should publish cloud events """

    prompts: AsyncStringCacheRepository[Prompt, str]
    """ Gets the repository used to manage the Prompt records """

    local_file_system_manager: LocalFileSystemManager

    def __init__(
        self,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        prompts: AsyncStringCacheRepository[Prompt, str],
        local_file_system_manager: LocalFileSystemManager,
        # genai_api_client: GenAiServiceApiClient,
        # mosaic_api_client: MosaicServiceApiClient,
    ):
        pass
        # Constructor never called directly!
        # self._service_provider = None
        # self.cloud_event_bus = cloud_event_bus
        # self.cloud_event_publishing_options = cloud_event_publishing_options
        # self.repository = repository
        # self.local_file_system_manager = local_file_system_manager
        # self.genai_service_api_client = genai_service_api_client

    async def run_at(self, prompt_id: str, response_id: str) -> None:
        """Called when the HandlePromptResponseJob is executed by the scheduler based on the specified schedule"""
        log.debug(f"Running the HandlePromptResponseJob for prompt {prompt_id} response_id {response_id}")
        # Configure the dependencies required by the BackgroundJob
        self.configure()

        try:
            prompt = None
            # Get the prompt from the DB
            async with self.prompts as repo:
                prompt = await repo.get_async(prompt_id)
                if prompt is None:
                    log.warning(f"Prompt not found: {prompt_id}")
                    raise ApplicationException(f"Prompt not found: {prompt_id}")
                log.debug(f"Prompt found: {prompt_id}: {prompt}")
            
            # Validate the prompt
            if not prompt.is_submitted():
                raise ApplicationException(f"Prompt not submitted: {prompt_id}")

            # Process the prompt response - PLACEHOLDER
            # self.mosaic_api_client.post_genai_response(request_id=prompt.request_id, callback_url=prompt.callback_url, response=response)
            await asyncio.sleep(10)
            if prompt.mark_responded():
                log.debug(f"Prompt {prompt_id} was responded to the caller {prompt.request.caller_id} at {prompt.request.callback_url}")
                async with self.prompts as repo:
                    prompt = await repo.update_async(prompt)
                    log.info(f"Updated Prompt {prompt.aggregate_id} in the cache.")
                await self.emit_event("PromptResponded", **{"aggregate_id": prompt.aggregate_id, "request_id": prompt.request.request_id, "prompt_id": prompt.aggregate_id, "response_hash": prompt.response.hash, "callback_url": prompt.request.callback_url})
                
            log.debug(f"Done")
        except Exception as e:
            log.error(f"An error occurred while processing the prompt: {e}")
            await self.emit_event("PromptFaulted", **{"error": str(e)})

    def configure(self):
        """Configure the dependencies required by the BackgroundJob"""
        self._service_provider = HandlePromptResponseJob._build_services()
        self.cloud_event_bus = self._service_provider.get_required_service(CloudEventBus)
        self.cloud_event_publishing_options = self._service_provider.get_required_service(CloudEventPublishingOptions)
        self.prompts = self._service_provider.get_required_service(AsyncStringCacheRepository[Prompt, str])

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
                    if "error" not in kwargs:
                        raise ApplicationException("The error is missing.")
                    await self.publish_cloud_event_async(
                        PromptFaultedIntegrationEventV1(
                            aggregate_id=kwargs.get("aggregate_id", "unknown_aggregate_id"),
                            created_at=datetime.datetime.now(),
                            request_id=kwargs.get("request_id", "unknown_request_id"),
                            error=kwargs["error"],
                            details=kwargs.get("details", "No Details."),
                        )
                    )
                case "PromptResponseReceived":
                    if "response" not in kwargs:
                        raise ApplicationException("The response is missing.")
                    await self.publish_cloud_event_async(
                        PromptResponseReceivedIntegrationEventV1(
                            aggregate_id=kwargs.get("aggregate_id", "unknown_aggregate_id"),
                            created_at=kwargs.get("created_at", datetime.datetime.now()),
                            request_id=kwargs.get("request_id", "unknown_request_id"),
                            prompt_id=kwargs.get("prompt_id", "unknown_prompt_id"),
                            response=kwargs["response"],
                        )
                    )
                case "PromptResponded":
                    if "response_hash" not in kwargs:
                        raise ApplicationException("The response is missing.")
                    await self.publish_cloud_event_async(
                        PromptRespondedIntegrationEventV1(
                            aggregate_id=kwargs.get("aggregate_id", "unknown_aggregate_id"),
                            created_at=kwargs.get("created_at", datetime.datetime.now()),
                            request_id=kwargs.get("request_id", "unknown_request_id"),
                            prompt_id=kwargs.get("prompt_id", "unknown_prompt_id"),
                            response_hash=kwargs.get("response_hash", "unknown_response_hash"),
                            callback_url=kwargs.get("callback_url", "unknown_callback_url"),
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

        return services.build()
