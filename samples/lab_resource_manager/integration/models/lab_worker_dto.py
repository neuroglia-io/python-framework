"""Lab Worker DTO for API responses.

This DTO represents LabWorker resources in API responses,
following Neuroglia patterns for data transfer objects.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


@dataclass
class AwsEc2ConfigDto:
    """DTO for AWS EC2 configuration."""

    ami_id: str
    instance_type: str = "m5zn.metal"
    key_name: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    security_group_ids: list[str] = field(default_factory=list)
    assign_public_ip: bool = True
    ebs_volume_size_gb: int = 500
    ebs_volume_type: str = "io1"
    ebs_iops: int = 10000
    iam_instance_profile: Optional[str] = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class CmlConfigDto:
    """DTO for CML configuration."""

    license_token: Optional[str] = None
    admin_username: str = "admin"
    admin_password: Optional[str] = None
    api_base_url: Optional[str] = None
    max_nodes_unlicensed: int = 5
    max_nodes_licensed: int = 200
    enable_telemetry: bool = False


@dataclass
class ResourceCapacityDto:
    """DTO for resource capacity information."""

    total_cpu_cores: float
    total_memory_mb: int
    total_storage_gb: int
    allocated_cpu_cores: float = 0.0
    allocated_memory_mb: int = 0
    allocated_storage_gb: int = 0
    max_concurrent_labs: int = 20


@dataclass
class LabWorkerConditionDto:
    """DTO for lab worker conditions."""

    type: str
    status: bool
    last_transition: datetime
    reason: str
    message: str


@dataclass
class LabWorkerMetadataDto:
    """DTO for resource metadata."""

    name: str
    namespace: str
    uid: str
    creation_timestamp: datetime
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    generation: int = 0
    resource_version: str = "1"


@dataclass
class LabWorkerSpecDto:
    """DTO for lab worker specification."""

    lab_track: str
    aws_config: AwsEc2ConfigDto
    cml_config: CmlConfigDto
    desired_phase: str = "Ready"
    auto_license: bool = True
    enable_draining: bool = True


@dataclass
class LabWorkerStatusDto:
    """DTO for lab worker status."""

    phase: str
    conditions: list[LabWorkerConditionDto] = field(default_factory=list)
    ec2_instance_id: Optional[str] = None
    ec2_public_ip: Optional[str] = None
    ec2_private_ip: Optional[str] = None
    ec2_state: Optional[str] = None
    cml_version: Optional[str] = None
    cml_api_url: Optional[str] = None
    cml_ready: bool = False
    cml_licensed: bool = False
    capacity: Optional[ResourceCapacityDto] = None
    hosted_lab_ids: list[str] = field(default_factory=list)
    active_lab_count: int = 0
    provisioning_started: Optional[datetime] = None
    provisioning_completed: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    error_message: Optional[str] = None
    error_count: int = 0
    observed_generation: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class LabWorkerDto:
    """Complete DTO for lab worker resources."""

    api_version: str = "lab.neuroglia.io/v1"
    kind: str = "LabWorker"
    metadata: Optional[LabWorkerMetadataDto] = None
    spec: Optional[LabWorkerSpecDto] = None
    status: Optional[LabWorkerStatusDto] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = LabWorkerMetadataDto(name="", namespace="default", uid="", creation_timestamp=datetime.now())
        if self.spec is None:
            raise ValueError("LabWorkerSpecDto is required")
        if self.status is None:
            self.status = LabWorkerStatusDto(phase="Pending")


class CreateLabWorkerCommandDto(BaseModel):
    """Command to create a new lab worker."""

    name: str
    namespace: str = "default"
    lab_track: str
    ami_id: str
    instance_type: str = "m5zn.metal"
    key_name: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    security_group_ids: list[str] = field(default_factory=list)
    cml_license_token: Optional[str] = None
    auto_license: bool = True
    enable_draining: bool = True
    tags: dict[str, str] = field(default_factory=dict)


class UpdateLabWorkerDto(BaseModel):
    """DTO for updating a lab worker."""

    desired_phase: Optional[str] = None
    enable_draining: Optional[bool] = None
    cml_license_token: Optional[str] = None


class LabWorkerMetricsDto(BaseModel):
    """DTO for lab worker metrics."""

    cpu_utilization_percent: float
    memory_utilization_percent: float
    storage_utilization_percent: float
    lab_count: int
    max_labs: int
