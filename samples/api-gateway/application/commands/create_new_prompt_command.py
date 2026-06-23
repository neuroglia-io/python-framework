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
    PromptReceivedIntegrationEventV1,
    PromptFaultedIntegrationEventV1,
)
from application.services.background_tasks_scheduler import (
    BackgroundTasksBus,
    ScheduledTaskDescriptor,
)
from application.settings import AiGatewaySettings

from domain.models.prompt import Prompt, PromptRequest, PromptContext
from integration import IntegrationException
from integration.models import CreateNewPromptCommandDto, ItemPromptCommandResponseDto
from integration.services.cache_repository import AsyncStringCacheRepository
from integration.enums import PromptStatus, PromptKind


log = logging.getLogger(__name__)


@map_from(CreateNewPromptCommandDto)
@dataclass
class CreateNewPromptCommand(Command):

    callback_url: str
    """The required caller's URL where to call back to with the Prompt response."""

    context: dict
    """The required context of the prompt."""

    request_id: Optional[str] = None
    """The identifier of the request."""

    caller_id: Optional[str] = None
    """The identifier of the caller."""

    data_url: Optional[str] = None
    """The URL of the data to be processed."""


class CreateNewPromptCommandHandler(CommandHandlerBase, CommandHandler[CreateNewPromptCommand, OperationResult[Any]]):
    """Represents the service used to handle CreateNewPromptCommand"""

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

    async def handle_async(self, command: CreateNewPromptCommand) -> OperationResult[ItemPromptCommandResponseDto]:
        """Handle Mosaic's Prompt requests."""
        try:
            prompt_request = PromptRequest(
                kind=PromptKind.MOSAIC_ITEM,
                callback_url=command.callback_url,
                context=PromptContext(**command.context),
                request_id=command.request_id or None,
                caller_id=command.caller_id or None,
                data_url=command.data_url or None,
            )
            prompt = Prompt(request=prompt_request)
            if not prompt.is_valid():
                log.error(f"Invalid Prompt {id}: {asdict(prompt)}")
                return self.bad_request(f"Invalid Prompt: {asdict(prompt)}")

            # Check if the prompt already exists and if not, add it to the cache
            async with self.prompts as repo:
                if await repo.contains_async(prompt.aggregate_id):
                    raise ApplicationException(f"A Prompt with id {id} already exists but shouldnt.")
                else:
                    await repo.add_async(prompt)
                    log.info(f"Prompt {prompt.aggregate_id} added to the cache.")

            # Emit the PromptReceived event
            await self.emit_event("PromptReceived", prompt)
            log.info(f"Prompt {prompt.aggregate_id} received.")

            # Schedule the background job to handle the prompt
            scheduled_at = datetime.datetime.now() + datetime.timedelta(seconds=2)
            task_descriptor = ScheduledTaskDescriptor(
                id=prompt.aggregate_id,
                name="CreatePromptJob",
                scheduled_at=scheduled_at,
                data={"aggregate_id": prompt.aggregate_id},  # must  match src.application.tasks.create_prompt_job.run_at() signature!
            )
            self.background_tasks_bus.input_stream.on_next(task_descriptor)
            log.info(f"Prompt {prompt.aggregate_id} scheduled for processing.")

            return self.created(ItemPromptCommandResponseDto(prompt_id=prompt.aggregate_id, prompt_context=prompt.request.context, request_id=command.request_id))

        except (ApplicationException, IntegrationException) as e:
            try:
                kwargs = {"error": str(e)}
                await self.emit_event("PromptFaulted", prompt, **kwargs)
            except IntegrationException as e2:
                log.warning(f"The Event Gateway is down: {e2} - while handling {e}")
            log.error(f"Failed to handle CreateNewPromptCommand: {e}")
            return self.bad_request(f"Failed to handle CreateNewPromptCommand: {e}")

    async def emit_event(self, event_type: str, prompt: Prompt, **kwargs) -> None:
        try:
            match event_type:
                case "PromptFaulted":
                    await self.publish_cloud_event_async(
                        PromptFaultedIntegrationEventV1(
                            aggregate_id=prompt.aggregate_id,
                            created_at=prompt.created_at,
                            request_id=prompt.request.request_id,
                            error=kwargs.get("error", "Fault"),
                            details=kwargs.get("details", "Something happened."),
                        )
                    )
                case "PromptReceived":
                    await self.publish_cloud_event_async(
                        PromptReceivedIntegrationEventV1(
                            aggregate_id=prompt.aggregate_id,
                            created_at=prompt.created_at,
                            last_modified=prompt.last_modified,
                            request_id=prompt.request.request_id,
                            caller_id=prompt.request.caller_id,
                            callback_url=prompt.request.callback_url,
                            data_url=prompt.request.data_url or "No supporting data",
                            context=prompt.request.context,
                            status=PromptStatus.CREATED,
                        )
                    )
                case _:
                    raise ApplicationException(f"Unknown event type: {event_type}")

        except IntegrationException as e:
            log.warning(f"The Event Gateway is down: {e}")
