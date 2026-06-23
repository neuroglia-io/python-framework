"""Get Lab Instance Query.

This query retrieves a lab instance resource by ID using
Resource Oriented Architecture patterns with CQRS.
"""

from dataclasses import dataclass
from typing import Optional

from integration.models.lab_instance_dto import LabInstanceDto

from neuroglia.mediation.mediator import Query


@dataclass
class GetLabInstanceQuery(Query[Optional[LabInstanceDto]]):
    """Query to get a lab instance by ID."""

    resource_id: str
