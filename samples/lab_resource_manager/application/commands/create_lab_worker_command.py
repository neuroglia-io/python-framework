"""Command to create a new LabWorker resource."""

from dataclasses import dataclass
from typing import Optional

from domain.resources.lab_worker import (
    AwsEc2Config,
    CmlConfig,
    LabWorker,
    LabWorkerPhase,
    LabWorkerSpec,
    LabWorkerStatus,
)
from integration.models.lab_worker_dto import LabWorkerDto

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.resources import ResourceRepository
from neuroglia.data.resources import ResourceMetadata
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler


@dataclass
class CreateLabWorkerCommand(Command[OperationResult[LabWorkerDto]]):
    """Command to create a new lab worker."""

    name: str
    namespace: str
    lab_track: str
    ami_id: str
    instance_type: str = "m5zn.metal"
    key_name: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    security_group_ids: Optional[list[str]] = None
    cml_license_token: Optional[str] = None
    auto_license: bool = True
    enable_draining: bool = True
    tags: Optional[dict[str, str]] = None

    def __post_init__(self):
        if self.security_group_ids is None:
            self.security_group_ids = []
        if self.tags is None:
            self.tags = {}


class CreateLabWorkerCommandHandler(CommandHandler[CreateLabWorkerCommand, OperationResult[LabWorkerDto]]):
    """Handler for creating lab worker resources."""

    def __init__(self, repository: ResourceRepository[LabWorkerSpec, LabWorkerStatus], mapper: Mapper):
        super().__init__()
        self._repository = repository
        self._mapper = mapper

    async def handle_async(self, request: CreateLabWorkerCommand) -> OperationResult[LabWorkerDto]:
        """Create a new lab worker resource."""
        try:
            # Create metadata
            metadata = ResourceMetadata(name=request.name, namespace=request.namespace, labels={"lab-track": request.lab_track, "resource-type": "lab-worker"})

            # Create AWS EC2 configuration (handle None values)
            aws_config = AwsEc2Config(ami_id=request.ami_id, instance_type=request.instance_type, key_name=request.key_name, vpc_id=request.vpc_id, subnet_id=request.subnet_id, security_group_ids=request.security_group_ids or [], tags=request.tags or {})

            # Validate AWS configuration
            validation_errors = aws_config.validate()
            if validation_errors:
                return self.bad_request(f"Invalid AWS configuration: {', '.join(validation_errors)}")

            # Create CML configuration
            cml_config = CmlConfig(license_token=request.cml_license_token)

            # Validate CML configuration
            validation_errors = cml_config.validate()
            if validation_errors:
                return self.bad_request(f"Invalid CML configuration: {', '.join(validation_errors)}")

            # Create spec
            spec = LabWorkerSpec(lab_track=request.lab_track, aws_config=aws_config, cml_config=cml_config, desired_phase=LabWorkerPhase.READY, auto_license=request.auto_license, enable_draining=request.enable_draining)

            # Validate spec
            validation_errors = spec.validate()
            if validation_errors:
                return self.bad_request(f"Invalid specification: {', '.join(validation_errors)}")

            # Create the resource
            worker = LabWorker(metadata=metadata, spec=spec)

            # Save to repository
            await self._repository.add_async(worker)

            # Map to DTO and return
            worker_dto = self._mapper.map(worker, LabWorkerDto)
            return self.created(worker_dto)

        except Exception as e:
            return OperationResult("Internal Server Error", 500, f"Failed to create lab worker: {str(e)}")
