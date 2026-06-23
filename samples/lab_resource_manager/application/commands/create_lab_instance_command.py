"""Create Lab Instance Command Handler.

This handler processes commands to create lab instance resources,
following CQRS patterns adapted for Resource Oriented Architecture.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.resources.lab_instance_request import (
    LabInstanceRequest,
    LabInstanceRequestSpec,
)
from integration.models.lab_instance_dto import LabInstanceDto
from integration.repositories.lab_instance_resource_repository import (
    LabInstanceResourceRepository,
)

from neuroglia.core import OperationResult
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Command, CommandHandler

log = logging.getLogger(__name__)


@dataclass
class CreateLabInstanceCommand(Command):
    """Command to create a new lab instance request."""

    name: str
    namespace: str
    lab_template: str
    student_email: str
    duration_minutes: int
    scheduled_start_time: Optional[datetime] = None
    environment: Optional[dict[str, str]] = None


class CreateLabInstanceCommandHandler(CommandHandler[CreateLabInstanceCommand, OperationResult[LabInstanceDto]]):
    """Handler for creating lab instance request resources."""

    def __init__(self, service_provider: ServiceProviderBase, resource_repository: LabInstanceResourceRepository, mapper: Mapper):
        super().__init__(service_provider)
        self.resource_repository = resource_repository
        self.mapper = mapper

    async def handle_async(self, command: CreateLabInstanceCommand) -> OperationResult[LabInstanceDto]:
        """Handle the create lab instance command."""

        try:
            log.info(f"Creating lab instance: {command.namespace}/{command.name}")

            # Create resource specification
            spec = LabInstanceRequestSpec(lab_template=command.lab_template, duration_minutes=command.duration_minutes, student_email=command.student_email, scheduled_start=command.scheduled_start, resource_limits=command.resource_limits, environment_variables=command.environment_variables)

            # Validate specification
            validation_errors = spec.validate()
            if validation_errors:
                error_message = "; ".join(validation_errors)
                log.warning(f"Lab instance validation failed: {error_message}")
                return self.bad_request(f"Validation failed: {error_message}")

            # Create resource metadata
            from neuroglia.data.resources.abstractions import ResourceMetadata

            metadata = ResourceMetadata(name=command.name, namespace=command.namespace, labels=command.labels or {}, annotations={"created-by": "lab-resource-manager", "student-email": command.student_email})

            # Create the lab instance resource
            lab_instance = LabInstanceRequest(metadata=metadata, spec=spec)

            # Check if resource with same name already exists
            existing = await self.resource_repository.get_async(lab_instance.id)
            if existing:
                return self.conflict(f"Lab instance '{command.name}' already exists in namespace '{command.namespace}'")

            # Save the resource
            created_resource = await self.resource_repository.add_async(lab_instance)

            # Map to DTO for response
            result_dto = self.mapper.map(created_resource, LabInstanceDto)

            log.info(f"Lab instance created successfully: {created_resource.id}")
            return self.created(result_dto)

        except Exception as e:
            log.error(f"Failed to create lab instance: {e}")
            return self.internal_server_error(f"Failed to create lab instance: {str(e)}")

    def bad_request(self, message: str) -> OperationResult[LabInstanceDto]:
        """Create a bad request result."""
        return OperationResult.failed(message, 400)

    def conflict(self, message: str) -> OperationResult[LabInstanceDto]:
        """Create a conflict result."""
        return OperationResult.failed(message, 409)

    def created(self, data: LabInstanceDto) -> OperationResult[LabInstanceDto]:
        """Create a successful creation result."""
        return OperationResult.successful(data)

    def internal_server_error(self, message: str) -> OperationResult[LabInstanceDto]:
        """Create an internal server error result."""
        return OperationResult.failed(message, 500)
