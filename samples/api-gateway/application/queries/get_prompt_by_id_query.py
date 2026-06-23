import datetime
import logging
from dataclasses import asdict, dataclass

import redis
from neuroglia.core.operation_result import OperationResult
from neuroglia.mediation.mediator import Query, QueryHandler

from application.exceptions import ApplicationException
from domain.models.prompt import Prompt

from integration.exceptions import IntegrationException
from integration.models import PromptDto
from integration.models.prompt_dto import PromptContextDto, PromptRequestDto, PromptResponseDto
from integration.services.cache_repository import AsyncStringCacheRepository

log = logging.getLogger(__name__)


@dataclass
class GetPromptByIdQuery(Query[OperationResult[PromptDto]]):
    """Represents the query used to get the details of an Entity (Prompt) by its local unique id."""

    prompt_id: str


class GetPromptByIdQueryHandler(QueryHandler[GetPromptByIdQuery, OperationResult[PromptDto]]):
    """Represents the service used to handle PromptByIdQuery instances"""

    prompts: AsyncStringCacheRepository[Prompt, str]

    def __init__(self, prompts: AsyncStringCacheRepository[Prompt, str]):
        self.prompts = prompts

    async def handle_async(self, query: GetPromptByIdQuery) -> OperationResult[PromptDto]:
        try:
            prompt_id = query.prompt_id
            async with self.prompts as repo:
                if not await repo.contains_async(prompt_id):
                    return self.not_found(PromptDto, prompt_id)
                prompt = await repo.get_async(prompt_id)

            if not prompt or not prompt.request:
                return self.not_found(PromptDto, prompt_id)

            # request_context_dto = PromptContextDto(**prompt.request.context)

            request_dto = PromptRequestDto(
                kind=prompt.request.kind,
                callback_url=prompt.request.callback_url,
                context=prompt.request.context,
                request_id=prompt.request.request_id,
                caller_id=prompt.request.caller_id,
                data_url=prompt.request.data_url,
                downloaded_at=prompt.request.downloaded_at,
                prepared_at=prompt.request.prepared_at,
                submitted_at=prompt.request.submitted_at,
                completed_at=prompt.request.completed_at,
                responded_at=prompt.request.responded_at,
            )
            if prompt.response:
                response_dto = PromptResponseDto(**asdict(prompt.response))
            else:
                response_dto = None

            prompt_dto = PromptDto(
                aggregate_id=prompt.aggregate_id,
                created_at=prompt.created_at,
                last_modified=prompt.last_modified,
                request=request_dto,
                response=response_dto,
                status=prompt.status,
                data_bucket=prompt.data_bucket,
            )
            return self.ok(prompt_dto)

        except (ApplicationException, IntegrationException, redis.ConnectionError) as e:
            log.error(f"Failed to handle PromptByIdQuery: {e}")
            return self.bad_request(f"Failed to handle PromptByIdQuery: {e}")
