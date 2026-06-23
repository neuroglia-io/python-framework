import datetime
import hashlib
import logging
import uuid

from dataclasses import dataclass, field
from typing import Any, List, Optional

from neuroglia.data.abstractions import Entity
from neuroglia.mapping.mapper import map_to

from domain.exceptions import DomainException
from domain.utils import validate_bucket_name

from integration.enums import PromptStatus, PromptKind
from integration.models import PromptDto, PromptResponseDto
from integration.models.prompt_dto import PromptRequestDto

log = logging.getLogger(__name__)


def hash_dict(my_dict):
    sorted_items = tuple(sorted(my_dict.items()))
    hash_value = hashlib.sha256(str(sorted_items).encode()).hexdigest()  # Or another hash function
    return hash_value


@map_to(PromptResponseDto)
@dataclass
class PromptResponse:
    """Represents a response to a prompt."""

    hash: str
    """The unique identifier of the PromptResponse."""

    created_at: datetime.datetime
    """The date and time the prompt was created."""

    last_modified: datetime.datetime
    """The date and time the prompt was last modified."""

    data: dict[str, Any]
    """The response data."""

    def __init__(
        self,
        response: dict[str, Any],
        **kwargs,
    ):
        self.hash = hash_dict(response)
        self.data = response
        self.created_at = datetime.datetime.now()
        self.last_modified = self.created_at
        # Initialize the base dataclass
        super().__init__()


# @map_to(PromptContextDto)
class PromptContext(dict):
    pass

    def __init__(self, *args, **kwargs):
        required_fields = {"flags"}  # The fields you want to enforce

        # Check if all required fields are present in kwargs
        missing_fields = required_fields - set(kwargs)
        # if missing_fields:
        #     raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        for field in missing_fields:
            self[field] = None

        # Initialize the dictionary (you can pre-fill or validate values here)
        super().__init__(*args, **kwargs)


# @map_to(MosaicPromptContextDto)
@dataclass
class MosaicPromptContext(PromptContext):

    mosaic_base_url: str
    """The base URL of Mosaic."""

    form_qualified_name: str
    """The qualified name of the form."""

    form_id: str
    """The identifier of the form."""

    module_id: str
    """The identifier of the module."""

    item_id: str
    """The identifier of the item."""

    item_bp: str
    """The item BP."""

    improve_stem: bool

    review_bp_mapping: bool

    review_technical_accuracy: bool

    improve_options: bool

    suggest_alternate_options: bool

    review_grammar: bool

    additional_context_input: dict[str, Any]


@map_to(PromptRequestDto)
@dataclass
class PromptRequest:
    """Represents the request part of a prompt."""

    kind: PromptKind
    """The identifier of the caller."""

    callback_url: str
    """The caller's URL where to call back to with the Prompt response. TODO: Authenticate the URL."""

    context: PromptContext
    """The context of the prompt."""

    request_id: Optional[str] = None
    """The caller's request identifier."""

    caller_id: Optional[str] = None
    """The caller's identifier."""

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

    def has_valid_data_url(self) -> str | None:
        if self.data_url not in [None, "None"]:
            return self.data_url
        return None

@map_to(PromptDto)
@dataclass
class Prompt(Entity[str]):
    """Represents a Prompt."""

    id: str
    """The unique identifier of the prompt record in the Cache DB. (Required by Entity)"""

    aggregate_id: str
    """The unique identifier of the Prompt. """

    created_at: datetime.datetime
    """The date and time the prompt was created."""

    last_modified: datetime.datetime
    """The date and time the prompt was last modified."""

    request: PromptRequest
    """The request part of the prompt."""

    status: Optional[PromptStatus] = PromptStatus.CREATED
    """The current status of the prompt."""

    data_bucket: Optional[str] = None
    """The name of the bucket containing supporting structured data."""

    response: Optional[PromptResponse] = None
    """The final response received for the prompt."""

    def __init__(
        self,
        request: PromptRequest,
        **kwargs,
    ):
        self.aggregate_id = kwargs.get("aggregate_id", str(uuid.uuid4()).replace("-", ""))
        self.created_at = datetime.datetime.now()
        self.last_modified = self.created_at

        # Required attributes
        self.request = request

        # Set defaults
        self.status = PromptStatus.CREATED
        self.data_bucket = None
        self.response = None

        # Overwrite attributes if any is provided
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.id = Prompt.build_id(self.aggregate_id)

        # Initialize the base dataclass
        super().__init__()

    @staticmethod
    def build_id(aggregate_id: Optional[str] = None) -> str:
        if aggregate_id is None:
            return f"prompt.*"
        return f"prompt.{aggregate_id}"

    def start_preparing(self) -> bool:
        """Moves the prompt to the PREPARING state"""
        return self._try_set_status(PromptStatus.PREPARING)

    def mark_prepared(self, bucket_name: Optional[str] = None) -> bool:
        """Moves the prompt to the PREPARED state (if the bucket name is valid) when the data is downloaded (if any)."""
        if bucket_name:
            is_valid, err = validate_bucket_name(bucket_name)
            if not is_valid:
                raise DomainException(f"Invalid bucket name: {err}")
            self.data_bucket = bucket_name
        return self._try_set_status(PromptStatus.PREPARED)

    def mark_submitted(self) -> bool:
        """Moves the prompt to the SUBMITTED state, when the prompt request was submitted to the downstream GenAI Service."""
        return self._try_set_status(PromptStatus.SUBMITTED)

    def mark_completed(self) -> bool:
        """Moves the prompt to the COMPLETED state, when the prompt response was received from the downstream GenAI Service."""
        return self._try_set_status(PromptStatus.COMPLETED)

    def mark_responded(self) -> bool:
        """Moves the prompt to the RESPONDED state, when the prompt response was sent back to the caller."""
        return self._try_set_status(PromptStatus.RESPONDED)

    def cancel(self) -> bool:
        return self._try_set_status(PromptStatus.CANCELLED)

    def fault(self) -> bool:
        return self._try_set_status(PromptStatus.FAULTED)

    def is_cancelled(self) -> bool:
        return self.status == PromptStatus.CANCELLED

    def is_faulted(self) -> bool:
        return self.status == PromptStatus.FAULTED

    def is_created(self) -> bool:
        return self.status == PromptStatus.CREATED

    def is_preparing(self) -> bool:
        return self.status == PromptStatus.PREPARING

    def is_prepared(self) -> bool:
        return self.status == PromptStatus.PREPARED

    def is_submitted(self) -> bool:
        return self.status == PromptStatus.SUBMITTED or self.status == PromptStatus.COMPLETED or self.status == PromptStatus.RESPONDED

    def is_completed(self) -> bool:
        return self.status == PromptStatus.COMPLETED or self.status == PromptStatus.RESPONDED

    def is_responded(self) -> bool:
        return self.status == PromptStatus.RESPONDED

    def is_valid(self) -> bool:
        # Basic validation
        if self.aggregate_id is None or self.request is None or self.request.kind is None or self.request.context is None or self.request.callback_url is None:
            return False

        # TODO: Validate the context based on the Request.PromptKind

        return self.status in [
            PromptStatus.CREATED,
            PromptStatus.PREPARING,
            PromptStatus.PREPARED,
            PromptStatus.SUBMITTED,
            PromptStatus.COMPLETED,
            PromptStatus.RESPONDED,
        ]

    def __str__(self) -> str:
        return f"Prompt {self.aggregate_id} ({self.status})"

    # Public Functions
    def set_response(self, prompt_response: PromptResponse) -> bool:
        """Sets the response for the prompt and marks the prompt as completed."""
        if self.is_completed() or self.is_responded():
            raise DomainException(f"Prompt {self.aggregate_id} is already completed or responded.")
        if self.response is not None:
            raise DomainException(f"Response for Prompt {self.aggregate_id} already exists ({self.response.hash}).")
        if self.mark_completed():
            self.response = prompt_response
            return True
        else:
            raise DomainException(f"Failed to set response for Prompt {self.aggregate_id}.")
        return False

    # Private Functions
    def _try_set_status(self, status: PromptStatus) -> bool:
        """Prompt status transitions logic."""
        res = True
        original_status = self.status
        match status:
            # Can cancel anytime
            case PromptStatus.CANCELLED:
                self.status = status
            # Can fault anytime
            case PromptStatus.FAULTED:
                self.status = status
            # Ignoring if the status is already set
            case self.status:
                log.debug(f"Status is already {self.status}, ignoring.")
                res = True
            # Valid state transitions
            case _:
                match (self.status, status):
                    case (PromptStatus.CREATED, PromptStatus.PREPARING):
                        self.request.prepared_at = datetime.datetime.now()
                        self.status = status
                    case (PromptStatus.CREATED, PromptStatus.PREPARED):
                        self.request.prepared_at = datetime.datetime.now()
                        self.request.downloaded_at = None
                        self.status = status
                    case (PromptStatus.PREPARING, PromptStatus.PREPARED):
                        self.request.downloaded_at = datetime.datetime.now()
                        self.status = status
                    case (PromptStatus.PREPARED, PromptStatus.SUBMITTED):
                        self.request.submitted_at = datetime.datetime.now()
                        self.status = status
                    case (PromptStatus.SUBMITTED, PromptStatus.COMPLETED):
                        self.request.completed_at = datetime.datetime.now()
                        self.status = status
                    case (PromptStatus.COMPLETED, PromptStatus.RESPONDED):
                        self.request.responded_at = datetime.datetime.now()
                        self.status = status
                    case _:
                        log.info(f"Invalid state transition from {original_status} to {status}")
                        res = False
        if res:
            log.debug(f"Valid state transition from {original_status} to {self.status}")
            self.last_modified = datetime.datetime.now()
        return res
