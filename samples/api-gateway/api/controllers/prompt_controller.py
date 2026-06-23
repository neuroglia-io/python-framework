import logging
from typing import Any, Annotated

from classy_fastapi.decorators import post, get
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase

from api.controllers.oauth2_scheme import validate_token
from api.controllers.mosaic_authentication_scheme import validate_mosaic_authentication
from application.commands.create_new_prompt_command import CreateNewPromptCommand
from application.queries.get_prompt_by_id_query import GetPromptByIdQuery
from integration.models import CreateNewItemPromptCommandDto, ItemPromptCommandResponseDto, PromptDto

log = logging.getLogger(__name__)


class PromptController(ControllerBase):
    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post("/item", response_model=ItemPromptCommandResponseDto, status_code=201, responses=ControllerBase.error_responses)
    async def create_new_item_prompt(self, command_dto: CreateNewItemPromptCommandDto, key: str = Depends(validate_mosaic_authentication)) -> Any:
        """Handles an ItemPrompt request from Mosaic.

        **Requires valid API Key.**
        """
        # Converts the Mosaic ItemPrompt schema to a generic CreateNewPromptCommand object
        item_context = {
            "prompt_context": "item",
            "mosaic_base_url": f"https://{command_dto.callback_url.host}",
            "form_qualified_name": command_dto.form_qualified_name,
            "form_id": command_dto.form_id,
            "module_id": command_dto.module_id,
            "item_id": command_dto.item_id,
            "item_bp": command_dto.item_bp,
            "flags": {
                "improve_stem": command_dto.improve_stem,
                "review_bp_mapping": command_dto.review_bp_mapping,
                "review_technical_accuracy": command_dto.review_technical_accuracy,
                "improve_options": command_dto.improve_options,
                "suggest_alternate_options": command_dto.suggest_alternate_options,
                "review_grammar": command_dto.review_grammar,
            },
            "additional_context_input": command_dto.additional_context_input,
        }
        command = CreateNewPromptCommand(
            callback_url=str(command_dto.callback_url),
            context=item_context,
            request_id=command_dto.request_id,
            caller_id=command_dto.user_id,
            data_url=str(command_dto.item_url),
        )
        return self.process(await self.mediator.execute_async(command))  # type: ignore

    @get("/{prompt_id}", response_model=PromptDto, responses=ControllerBase.error_responses)
    async def get_item_prompt_by_id(self, prompt_id: str, key: str = Depends(validate_mosaic_authentication)) -> PromptDto:
        """Get the prompt by its identifier.

        **Requires valid API Key.**"""
        return self.process(await self.mediator.execute_async(GetPromptByIdQuery(prompt_id=prompt_id)))  # type: ignore

    # @post("/form", response_model=Any, status_code=201, responses=ControllerBase.error_responses)
    # async def handle_form_prompt(self) -> Any:
    #     """Handles a FormPrompt request from Mosaic."""
    #     res = OperationResult(title="Form Prompt", status=201, detail="Handling FormPrompt request.")
    #     res.data = {"online": True, "detail": "Handling FormPrompt request."}
    #     return self.process(res)
