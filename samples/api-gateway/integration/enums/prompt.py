from dataclasses import dataclass
from enum import Enum


class CustomEnum(Enum):
    def __repr__(self):
        return self.value


class PromptStatus(str, CustomEnum):
    """The current status of a Prompt."""

    CREATED = "Created"  # Prompt received from 3rd party requester
    PREPARING = "Preparing"  # Handling Prompt's Data package
    PREPARED = "Prepared"  # Prompt Data package handled
    SUBMITTED = "Submitted"  # Prompt Submitted downstream agent
    COMPLETED = "Completed"  # PromptResponse received from downstream agent
    RESPONDED = "Responded"  # PromptResponse sent to 3rd party requester
    CANCELLED = "Cancelled"  # PromptResponse cancelled by any party requester
    FAULTED = "Faulted"


class PromptKind(str, CustomEnum):
    """The possible Kinds of a PromptRequests."""

    MOSAIC_ITEM = "mosaic_item"
    MOSAIC_FORM = "mosaic_form"
