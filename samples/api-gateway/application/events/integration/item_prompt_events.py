import datetime
import logging
from dataclasses import dataclass
from typing import Any, Optional

from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.integration.models import IntegrationEvent

from integration.enums.prompt import PromptStatus

log = logging.getLogger(__name__)


@cloudevent("prompt.received.v1")
@dataclass
class PromptReceivedIntegrationEventV1(IntegrationEvent[str]):

    aggregate_id: str
    """The unique id of the Event"""

    created_at: datetime.datetime
    """The date and time the prompt was created."""

    last_modified: datetime.datetime
    """The date and time the prompt was last modified."""

    callback_url: str
    """The required caller's URL where to call back to with the Prompt response."""

    context: dict
    """The required context of the prompt."""

    request_id: Optional[str]
    """The optional 3rd party identifier of the request."""

    caller_id: Optional[str]
    """The optional identifier of the caller."""

    data_url: Optional[str]
    """The optional URL of the data to be processed."""

    status: Optional[PromptStatus]
    """The current status of the prompt."""


@cloudevent("prompt.data.processed.v1")
@dataclass
class PromptDataProcessedIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    """The unique id of the Event"""

    created_at: datetime.datetime
    """The timestamp when the event was emitted."""

    request_id: Optional[str]
    """The optional 3rd party identifier of the request."""

    process_id: str
    """The identifier of the ingestion process."""

    data_url: Any
    """The URL of the original/raw/unstructured content package from Mosaic."""

    object_url: Any
    """The public S3 URL where the structured package was stored."""


@cloudevent("prompt.faulted.v1")
@dataclass
class PromptFaultedIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    """The unique id of the Event"""

    created_at: datetime.datetime
    """The timestamp when the event was emitted."""

    request_id: Optional[str]
    """The optional 3rd party identifier of the request."""
    
    error: Any
    """The error that caused the fault."""

    details: Any
    """The details of the fault."""


@cloudevent("prompt.submitted.v1")
@dataclass
class PromptSubmittedIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    """The unique id of the Event"""

    created_at: datetime.datetime
    """The timestamp when the event was emitted."""

    request_id: Optional[str]
    """The optional 3rd party identifier of the request."""

    process_id: Any
    """The identifier of the submission process."""


@cloudevent("prompt.response.received.v1")
@dataclass
class PromptResponseReceivedIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    """The unique id of the Event"""

    created_at: datetime.datetime
    """The timestamp when the event was emitted."""

    prompt_id: str
    """The identifier of the prompt."""

    request_id: Optional[str]
    """The optional 3rd party identifier of the request."""

    response_hash: str
    """The SHA256 hash of the response."""

    response: Any
    """The response to the prompt."""


@cloudevent("prompt.responded.v1")
@dataclass
class PromptRespondedIntegrationEventV1(IntegrationEvent[str]):
    aggregate_id: str
    """The unique id of the Event"""

    created_at: datetime.datetime
    """The timestamp when the event was emitted."""

    prompt_id: str
    """The identifier of the prompt."""

    request_id: Optional[str]
    """The optional 3rd party identifier of the request."""

    response_hash: str
    """The response hash to the prompt."""

    callback_url: str
    """The URL where the response was posted."""
