import datetime
import logging
import uuid
from typing import Any, Optional

import httpx
import redis
from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator

from api.services.oauth import get_public_key
from application import ApplicationException
from application.commands import CommandHandlerBase
from application.events.integration import (
    HealthCheckCompletedIntegrationEventV1,
    HealthCheckFailedIntegrationEventV1,
    HealthCheckRequestedIntegrationEventV1,
)
from application.settings import AiGatewaySettings

from domain.models.prompt import Prompt
from integration import IntegrationException
from integration.models import ExternalDependenciesHealthCheckResultDto
from integration.services.cache_repository import AsyncStringCacheRepository


log = logging.getLogger(__name__)


class ValidateExternalDependenciesCommand(Command):
    pass


class ValidateExternalDependenciesCommandHandler(CommandHandlerBase, CommandHandler[ValidateExternalDependenciesCommand, OperationResult[Any]]):
    """Represents the service used to handle ValidateExternalDependenciesCommand"""

    repository: AsyncStringCacheRepository[Prompt, str]

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        app_settings: AiGatewaySettings,
        repository: AsyncStringCacheRepository[Prompt, str],
    ):
        super().__init__(mediator, mapper, cloud_event_bus, cloud_event_publishing_options, app_settings)
        self.repository = repository

    async def handle_async(self, command: ValidateExternalDependenciesCommand) -> OperationResult[ExternalDependenciesHealthCheckResultDto]:
        """Validates whether the external dependencies are reachable and responsive."""
        try:
            id = str(uuid.uuid4()).replace("-", "")
            try:
                await self.publish_cloud_event_async(HealthCheckRequestedIntegrationEventV1(aggregate_id=id, created_at=datetime.datetime.now(), health_check_id=id))
            except IntegrationException as e:
                log.warning(f"The Event Gateway is down: {e}")

            identity_provider = await self.check_identity_provider()

            events_gateway = await self.check_events_gateway()

            cache_db = await self.check_cache_db()

            dependencies_health = {
                "identity_provider": identity_provider is not None,
                "events_gateway": events_gateway is not None,
                "cache_db": cache_db is not None,
            }
            dependencies_health["all"] = self.check_all_dependencies(dependencies_health)
            try:
                await self.publish_cloud_event_async(HealthCheckCompletedIntegrationEventV1(aggregate_id=id, created_at=datetime.datetime.now(), **dependencies_health))
            except IntegrationException as e:
                log.warning(f"The Event Gateway is down: {e}")

            return self.ok(ExternalDependenciesHealthCheckResultDto(**dependencies_health))

        except (ApplicationException, IntegrationException) as e:
            try:
                await self.publish_cloud_event_async(HealthCheckFailedIntegrationEventV1(aggregate_id=id, created_at=datetime.datetime.now(), detail=str(e)))
            except IntegrationException as e2:
                log.warning(f"The Event Gateway is down: {e2}")
            log.error(f"Failed to handle ValidateExternalDependenciesCommand: {e}")
            return self.bad_request(f"Failed to handle ValidateExternalDependenciesCommand: {e}")

    def check_all_dependencies(self, dependencies: Optional[dict[str, Any]]) -> bool:
        """Recursively checks the health of all dependencies.

        Args:
            dependencies: A dictionary containing dependencies and their health status.

        Returns:
            True if all dependencies are healthy, False otherwise.
        """
        if dependencies is None:
            return False
        for value in dependencies.values():
            if isinstance(value, dict):
                if not self.check_all_dependencies(value):
                    return False
            elif not value:
                return False
        return True

    async def check_identity_provider(self) -> bool:
        res = await get_public_key(self.app_settings.jwt_authority)
        return res is not None

    async def check_events_gateway(self) -> bool:
        # To test the event gateway, we really need to make an HTTP call to it,
        # just using await self.publish_cloud_event_async will always return True
        # if the event is valid (as the CloudEventPublisher will try to "silently" send
        # the event {retry} times and "just" log ERROR if any)!
        events_gateway = False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.app_settings.cloud_event_sink)
                if response.is_success or response.is_error:
                    events_gateway = True
        except httpx.ConnectError as e:
            log.error(f"Error connecting to events gateway: {e}")
            return False

        return events_gateway

    async def check_cache_db(self) -> bool:
        cache_db = None
        try:
            async with self.repository as repo:
                cache_db = await repo.ping()
        except redis.ConnectionError as e:
            log.error(f"Error connecting to Cache DB: {e}")

        return cache_db is not None
