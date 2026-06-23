import datetime

from pydantic import Field, create_model
from integration.services.snake_to_camel import CamelModel

from typing import Any, Dict, NewType, Annotated, Optional

from pydantic import Field, HttpUrl
from bson import ObjectId

from integration.enums.prompt import PromptStatus, PromptKind


MongoId = NewType("MongoId", str)
QualifiedName = NewType("QualifiedName", str)
MongoIdField = Annotated[MongoId, Field(..., description="MongoDB ObjectId", pattern=r"^[0-9a-fA-F]{24}$")]
QualifiedNameField = Annotated[QualifiedName, Field(..., description="A Mozart Qualified Name", pattern=r"\w+\s\w+\s\w+\sv\d+.*\s\w+\s\w+\.\d+", examples=["Exam CCIE TEST v1 DES 1.1"])]


class PromptResponseDto(CamelModel):
    """Represents the response to a prompt."""

    hash: str
    """The unique identifier of the PromptResponse."""

    created_at: datetime.datetime
    """The date and time the prompt was created."""

    last_modified: datetime.datetime
    """The date and time the prompt was last modified."""

    data: dict[str, Any]
    """The response data."""


class PromptContextDto(CamelModel):
    pass
    # def __init__(self, **data: Any):
    #     fields: Dict[str, Any] = {}
    #     for key, value in data.items():
    #         fields[key] = (Any, value)  # (type, default value)

    #     DynamicModel = create_model("DynamicPromptContext", **fields)
    #     dynamic_instance = DynamicModel(**data)

    #     super().__init__(**dynamic_instance.model_dump())  # Initialize base class

    # def __getattr__(self, name: str) -> Any:
    #     try:
    #         return self.__dict__[name]
    #     except KeyError:
    #         raise AttributeError(f"'PromptContextDto' object has no attribute '{name}'")

    # def __setattr__(self, name: str, value: Any) -> None:
    #     if name in self.__fields__:
    #         super().__setattr__(name, value)
    #     else:
    #         self.__dict__[name] = value

    # def dict(self, *args, **kwargs):
    #     """Override dict to ensure dynamic attributes are included"""
    #     base_dict = super().dict(*args, **kwargs)
    #     dynamic_attrs = {k: v for k, v in self.__dict__.items() if k not in self.__fields__}
    #     return {**base_dict, **dynamic_attrs}


class PromptRequestDto(CamelModel):
    """Represents the request part of a prompt."""

    kind: PromptKind
    """The identifier of the caller."""

    callback_url: str
    """The caller's URL where to call back to with the Prompt response. TODO: Authenticate the URL."""

    context: dict
    """The context of the prompt."""

    request_id: Optional[str]
    """The optional caller's request identifier."""

    caller_id: Optional[str]
    """The optional caller's identifier."""

    data_url: Optional[str] = None
    """The optional URL of the unstructured data.zip to be processed. TODO: Authenticate the URL."""

    downloaded_at: Optional[datetime.datetime] = None
    """The date and time the data was downloaded."""

    prepared_at: Optional[datetime.datetime] = None
    """The date and time the data was prepared."""

    submitted_at: Optional[datetime.datetime] = None
    """The date and time the data was submitted."""

    completed_at: Optional[datetime.datetime] = None
    """The date and time the data was completed."""

    responded_at: Optional[datetime.datetime] = None
    """The date and time the data was responded."""


class PromptDto(CamelModel):

    aggregate_id: str
    """The unique identifier of the Prompt. """

    created_at: datetime.datetime
    """The date and time the prompt was created."""

    last_modified: datetime.datetime
    """The date and time the prompt was last modified."""

    request: PromptRequestDto
    """The request part of the prompt."""

    response: Optional[PromptResponseDto] = None
    """The final response received for the prompt."""

    status: Optional[PromptStatus]
    """The current status of the prompt."""

    data_bucket: Optional[str] = None
    """The name of the bucket containing supporting structured data."""


class CreateNewPromptCommandDto(CamelModel):

    request_id: MongoIdField = Field(examples=[str(ObjectId())])
    """The 3rd party identifier of the request."""

    callback_url: str
    """The caller's URL where to call back to with the Prompt response."""

    context: dict
    """The context of the prompt."""

    caller_id: Optional[str]
    """The optional identifier of the caller."""

    data_url: Optional[str]
    """The optional URL of the data to be processed."""


class CreateNewItemPromptCommandDto(CamelModel):

    callback_url: HttpUrl = Field(examples=["http://mosaic/api/item/6793748709cf1268f2a0c086/ai_response/67a094479a7d0b77d5f02757"])
    """The required URL to call back to with the Prompt response."""

    request_id: Optional[MongoIdField] = Field(default=None, examples=[str(ObjectId())])
    """The optional 3rd party identifier of the request."""

    form_qualified_name: Optional[str] = Field(default=None, pattern=r"\w+\s\w+\s\w+\sv\d+.*\s\w+\s\w+\.\d+", examples=["Exam CCIE TEST v1 DES 1.1"])
    """The optional qualified name of the form."""

    form_id: Optional[MongoIdField] = Field(default=None, examples=[str(ObjectId())])
    """The optional identifier of the form."""

    module_id: Optional[MongoIdField] = Field(default=None, examples=[str(ObjectId())])
    """The optional identifier of the module."""

    item_id: Optional[MongoIdField] = Field(default=None, examples=[str(ObjectId())])
    """The optional identifier of the item."""

    item_url: Optional[HttpUrl] = Field(default=None, examples=["http://mosaic/api/genai/download/item/6793748709cf1268f2a0c086/module/65bb89a4cf6b2c4d4a8e5eaa"])
    """The optional URL to the supporting item data package."""

    item_bp: Optional[str] = Field(default=None, examples=["1.0 Blueprint Domain"])
    """The optional blueprint topic mapped to the item."""

    improve_stem: bool = Field(default=True)
    """The optional flag to indicate if the stem should be improved."""

    review_bp_mapping: bool = Field(default=True)
    """The optional flag to indicate if the blueprint mapping should be reviewed."""

    review_technical_accuracy: bool = Field(default=True)
    """The optional flag to indicate if the technical accuracy should be reviewed."""

    improve_options: bool = Field(default=True)
    """The optional flag to indicate if the options should be improved."""

    suggest_alternate_options: bool = Field(default=True)
    """The optional flag to indicate if alternate options should be suggested."""

    review_grammar: bool = Field(default=True)
    """The optional flag to indicate if the grammar should be reviewed."""

    additional_context_input: Optional[str] = Field(default="Some additional context input or data that the end-user wants to include into the prompt.")
    """The optional additional context input data that the end-user wants to include into the prompt."""

    user_id: Optional[str] = Field(default=None, examples=["username"])
    """The optional identifier of the user submitting the ItemPrompt."""


class ItemPromptCommandResponseDto(CamelModel):

    prompt_id: str
    """The local unique identifier of the aggregate."""

    prompt_context: dict
    """The context of the prompt."""

    request_id: Optional[str]
    """The optional 3rd party identifier of the request."""


class RecordPromptResponseCommandDto(CamelModel):

    prompt_id: str
    """The identifier of the prompt."""

    response: dict[str, Any]
    """The response data."""


class RecordPromptResponseCommandResponseDto(CamelModel):

    prompt_id: str
    """The identifier of the prompt."""

    response_hash: str
    """The hash of the response data."""
