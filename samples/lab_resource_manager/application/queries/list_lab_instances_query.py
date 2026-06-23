"""List Lab Instances Query.

This query retrieves multiple lab instance resources with filtering,
following CQRS patterns adapted for Resource Oriented Architecture.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from integration.models.lab_instance_dto import LabInstanceDto

from neuroglia.mediation.mediator import Query


@dataclass
class ListLabInstancesQuery(Query[List[LabInstanceDto]]):
    """Query to list lab instances with optional filtering."""

    namespace: Optional[str] = None
    labels: Optional[dict[str, str]] = field(default_factory=dict)
    phase: Optional[str] = None
    student_email: Optional[str] = None
