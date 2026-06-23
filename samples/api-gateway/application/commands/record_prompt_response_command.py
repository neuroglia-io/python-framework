import asyncio
import datetime
import logging
import uuid

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from neuroglia.core import OperationResult
from neuroglia.mapping.mapper import map_to, map_from
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
    PromptResponseReceivedIntegrationEventV1,
    PromptFaultedIntegrationEventV1,
)
from application.services.background_tasks_scheduler import (
    BackgroundTasksBus,
    ScheduledTaskDescriptor,
)
from application.settings import AiGatewaySettings

from domain.models.prompt import Prompt, PromptResponse
from integration import IntegrationException
from integration.models import RecordPromptResponseCommandDto, PromptResponseDto, RecordPromptResponseCommandResponseDto
from integration.services.cache_repository import AsyncStringCacheRepository
from integration.enums import PromptStatus


log = logging.getLogger(__name__)


@map_from(RecordPromptResponseCommandDto)
@dataclass
class RecordPromptResponseCommand(Command):

    prompt_id: str
    """The identifier of the prompt."""

    response: Any
    """The response data."""


class RecordPromptResponseCommandHandler(CommandHandlerBase, CommandHandler[RecordPromptResponseCommand, OperationResult[RecordPromptResponseCommandResponseDto]]):
    """Represents the service used to handle RecordPromptResponseCommand"""

    prompts: AsyncStringCacheRepository[Prompt, str]

    background_tasks_bus: BackgroundTasksBus

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        app_settings: AiGatewaySettings,
        prompts: AsyncStringCacheRepository[Prompt, str],
        background_tasks_bus: BackgroundTasksBus,
    ):
        self.prompts = prompts
        self.background_tasks_bus = background_tasks_bus
        super().__init__(mediator, mapper, cloud_event_bus, cloud_event_publishing_options, app_settings)

    async def handle_async(self, command: RecordPromptResponseCommand) -> OperationResult[RecordPromptResponseCommandResponseDto]:
        """Handle GenAI Prompt Response callback."""
        try:
            prompt = None
            # Validate the command
            async with self.prompts as repo:
                prompt = await repo.get_async(command.prompt_id)
                if prompt is None:
                    raise ApplicationException(f"Prompt {command.prompt_id} not found.")
            if not prompt.is_valid():
                log.error(f"Invalid Prompt {command.prompt_id}: {asdict(prompt)}")
                return self.bad_request(f"Invalid Prompt: {asdict(prompt)}")

            # Record the PromptResponse
            response = PromptResponse(response=command.response)
            if prompt.set_response(response):
                log.debug(f"Added Response {response.hash} to Prompt {prompt.aggregate_id}.")
                async with self.prompts as repo:
                    prompt = await repo.update_async(prompt)
                    log.info(f"Updated Prompt {prompt.aggregate_id} in the cache.")

            if not prompt.is_completed():
                raise ApplicationException(f"Prompt {prompt.aggregate_id} is not completed but should.")

            # Emit the PromptResponseReceived event
            await self.emit_event("PromptResponseReceived", aggregate_id=prompt.aggregate_id, request_id=prompt.request.request_id, prompt_id=prompt.aggregate_id, response_hash=prompt.response.hash, response=response.data)
            log.info(f"Prompt {prompt.aggregate_id} received.")

            # Schedule the background job to handle the prompt
            scheduled_at = datetime.datetime.now() + datetime.timedelta(seconds=2)
            task_descriptor = ScheduledTaskDescriptor(
                id=prompt.aggregate_id,
                name="HandlePromptResponseJob",
                scheduled_at=scheduled_at,
                data={"prompt_id": prompt.aggregate_id, "response_id": response.hash},
            )
            self.background_tasks_bus.input_stream.on_next(task_descriptor)
            log.info(f"PromptResponse {response.hash} for Prompt {prompt.aggregate_id} scheduled for processing.")
            return self.ok(RecordPromptResponseCommandResponseDto(prompt_id=prompt.aggregate_id, response_hash=response.hash))

        except (ApplicationException, IntegrationException) as e:
            try:
                kwargs = {"error": type(e), "details": str(e)}
                await self.emit_event("PromptFaulted", **kwargs)
            except IntegrationException as e2:
                log.warning(f"The Event Gateway is down: {e2} - while handling {e}")
            log.error(f"Failed to handle RecordPromptResponseCommand: {e}")
            return self.bad_request(f"Failed to handle RecordPromptResponseCommand: {e}")

    async def emit_event(self, event_type: str, **kwargs) -> None:
        try:
            match event_type:
                case "PromptFaulted":
                    await self.publish_cloud_event_async(
                        PromptFaultedIntegrationEventV1(
                            aggregate_id=kwargs.get("aggregate_id", "Fault"),
                            created_at=kwargs.get("created_at", datetime.datetime.now()),
                            request_id=kwargs.get("request_id", "Fault"),
                            error=kwargs.get("error", "Fault"),
                            details=kwargs.get("details", "Something happened."),
                        )
                    )
                case "PromptResponseReceived":
                    await self.publish_cloud_event_async(
                        PromptResponseReceivedIntegrationEventV1(
                            aggregate_id=kwargs.get("aggregate_id", "Fault"),
                            created_at=kwargs.get("created_at", datetime.datetime.now()),
                            request_id=kwargs.get("request_id", "Fault"),
                            prompt_id=kwargs.get("prompt_id", "Fault"),
                            response_hash=kwargs.get("response_hash", "Fault"),
                            response=kwargs.get("response", "Fault"),
                        )
                    )
                case _:
                    raise ApplicationException(f"Unknown event type: {event_type}")

        except IntegrationException as e:
            log.warning(f"The Event Gateway is down: {e}")
