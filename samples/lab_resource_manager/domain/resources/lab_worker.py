"""LabWorker resource definition.

This module defines the LabWorker resource which represents a CML hypervisor
that hosts and runs LabInstanceRequests. Each LabWorker is provisioned as an
EC2 instance and manages CML lab instances.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from neuroglia.data.resources.abstractions import (
    Resource,
    ResourceMetadata,
    ResourceSpec,
    ResourceStatus,
)
from neuroglia.data.resources.state_machine import StateMachineEngine


class LabWorkerPhase(Enum):
    """Phases of a LabWorker lifecycle."""

    PENDING = "Pending"  # Waiting to be provisioned
    PROVISIONING_EC2 = "ProvisioningEC2"  # Creating EC2 instance
    EC2_READY = "EC2Ready"  # EC2 running, CML starting
    STARTING = "Starting"  # Starting CML services
    READY_UNLICENSED = "ReadyUnlicensed"  # Ready for labs <5 nodes (unlicensed mode)
    LICENSING = "Licensing"  # Applying CML license
    READY = "Ready"  # Ready for full capacity labs (licensed)
    ACTIVE = "Active"  # Hosting lab instances
    DRAINING = "Draining"  # Not accepting new instances, finishing existing
    UNLICENSING = "Unlicensing"  # Removing CML license
    STOPPING = "Stopping"  # Shutting down CML
    TERMINATING_EC2 = "TerminatingEC2"  # Terminating EC2 instance
    TERMINATED = "Terminated"  # Cleaned up and removed
    FAILED = "Failed"  # Error occurred


class LabWorkerConditionType(Enum):
    """Condition types for LabWorker status."""

    EC2_PROVISIONED = "EC2Provisioned"
    CML_READY = "CMLReady"
    LICENSED = "Licensed"
    ACCEPTING_LABS = "AcceptingLabs"
    CAPACITY_AVAILABLE = "CapacityAvailable"
    HEALTH_CHECK_PASSED = "HealthCheckPassed"


@dataclass
class LabWorkerCondition:
    """Condition representing the state of a specific aspect of the LabWorker."""

    type: LabWorkerConditionType
    status: bool  # True/False
    last_transition: datetime
    reason: str
    message: str


@dataclass
class AwsEc2Config:
    """AWS EC2 configuration for provisioning a LabWorker."""

    ami_id: str  # e.g., "ami-0abcdef1234567890"
    instance_type: str = "m5zn.metal"  # EC2 instance type
    key_name: Optional[str] = None  # SSH key pair name
    vpc_id: Optional[str] = None  # VPC ID
    subnet_id: Optional[str] = None  # Subnet ID within VPC
    security_group_ids: list[str] = field(default_factory=list)  # Security group IDs
    assign_public_ip: bool = True  # Whether to assign public IP
    ebs_volume_size_gb: int = 500  # Root volume size
    ebs_volume_type: str = "io1"  # EBS volume type
    ebs_iops: int = 10000  # IOPS for io1 volumes
    iam_instance_profile: Optional[str] = None  # IAM instance profile ARN
    tags: dict[str, str] = field(default_factory=dict)  # EC2 instance tags

    def validate(self) -> list[str]:
        """Validate the EC2 configuration."""
        errors = []

        if not self.ami_id or not self.ami_id.startswith("ami-"):
            errors.append("valid ami_id is required (must start with 'ami-')")

        if self.instance_type not in ["m5zn.metal", "m5zn.12xlarge", "m5zn.6xlarge"]:
            errors.append(f"instance_type {self.instance_type} not supported for CML")

        if self.ebs_volume_type == "io1" and (self.ebs_iops < 100 or self.ebs_iops > 64000):
            errors.append("ebs_iops must be between 100 and 64000 for io1 volumes")

        if self.ebs_volume_size_gb < 100:
            errors.append("ebs_volume_size_gb must be at least 100 GB for CML")

        return errors


@dataclass
class CmlConfig:
    """CML configuration for the LabWorker."""

    license_token: Optional[str] = None  # CML license token (if available)
    admin_username: str = "admin"  # CML admin username
    admin_password: Optional[str] = None  # CML admin password
    api_base_url: Optional[str] = None  # CML API base URL (http://public-ip/api/v0)
    max_nodes_unlicensed: int = 5  # Max nodes in unlicensed mode
    max_nodes_licensed: int = 200  # Max nodes with license
    enable_telemetry: bool = False  # Whether to enable CML telemetry

    def validate(self) -> list[str]:
        """Validate the CML configuration."""
        errors = []

        if not self.admin_username:
            errors.append("admin_username is required")

        if self.max_nodes_unlicensed < 1 or self.max_nodes_unlicensed > 5:
            errors.append("max_nodes_unlicensed must be between 1 and 5")

        if self.max_nodes_licensed < self.max_nodes_unlicensed:
            errors.append("max_nodes_licensed must be >= max_nodes_unlicensed")

        return errors


@dataclass
class ResourceCapacity:
    """Resource capacity information for the LabWorker."""

    total_cpu_cores: float  # Total CPU cores available
    total_memory_mb: int  # Total memory in MB
    total_storage_gb: int  # Total storage in GB
    allocated_cpu_cores: float = 0.0  # Currently allocated CPU
    allocated_memory_mb: int = 0  # Currently allocated memory
    allocated_storage_gb: int = 0  # Currently allocated storage
    max_concurrent_labs: int = 20  # Maximum concurrent lab instances

    @property
    def available_cpu_cores(self) -> float:
        """Calculate available CPU cores."""
        return self.total_cpu_cores - self.allocated_cpu_cores

    @property
    def available_memory_mb(self) -> int:
        """Calculate available memory."""
        return self.total_memory_mb - self.allocated_memory_mb

    @property
    def available_storage_gb(self) -> int:
        """Calculate available storage."""
        return self.total_storage_gb - self.allocated_storage_gb

    @property
    def cpu_utilization_percent(self) -> float:
        """Calculate CPU utilization percentage."""
        if self.total_cpu_cores == 0:
            return 0.0
        return (self.allocated_cpu_cores / self.total_cpu_cores) * 100

    @property
    def memory_utilization_percent(self) -> float:
        """Calculate memory utilization percentage."""
        if self.total_memory_mb == 0:
            return 0.0
        return (self.allocated_memory_mb / self.total_memory_mb) * 100

    @property
    def storage_utilization_percent(self) -> float:
        """Calculate storage utilization percentage."""
        if self.total_storage_gb == 0:
            return 0.0
        return (self.allocated_storage_gb / self.total_storage_gb) * 100

    def can_accommodate(self, cpu_cores: float, memory_mb: int, storage_gb: int) -> bool:
        """Check if the worker can accommodate the requested resources."""
        return self.available_cpu_cores >= cpu_cores and self.available_memory_mb >= memory_mb and self.available_storage_gb >= storage_gb


@dataclass
class LabWorkerSpec(ResourceSpec):
    """Specification for a LabWorker (desired state)."""

    lab_track: str  # Track this worker belongs to (e.g., "ccna", "devnet")
    aws_config: AwsEc2Config  # AWS EC2 provisioning configuration
    cml_config: CmlConfig  # CML configuration
    desired_phase: LabWorkerPhase = LabWorkerPhase.READY  # Target operational phase
    auto_license: bool = True  # Auto-apply license when available
    enable_draining: bool = True  # Allow graceful draining before termination

    def validate(self) -> list[str]:
        """Validate the LabWorker specification."""
        errors = []

        if not self.lab_track:
            errors.append("lab_track is required")

        # Validate nested configs
        errors.extend(self.aws_config.validate())
        errors.extend(self.cml_config.validate())

        return errors


@dataclass
class LabWorkerStatus(ResourceStatus):
    """Status of a LabWorker (current state)."""

    def __init__(self):
        super().__init__()
        self.phase: LabWorkerPhase = LabWorkerPhase.PENDING
        self.conditions: list[LabWorkerCondition] = []

        # EC2 instance information
        self.ec2_instance_id: Optional[str] = None
        self.ec2_public_ip: Optional[str] = None
        self.ec2_private_ip: Optional[str] = None
        self.ec2_state: Optional[str] = None  # "pending", "running", "stopping", "stopped", "terminated"

        # CML information
        self.cml_version: Optional[str] = None
        self.cml_api_url: Optional[str] = None
        self.cml_ready: bool = False
        self.cml_licensed: bool = False

        # Resource capacity
        self.capacity: Optional[ResourceCapacity] = None

        # Lab instances hosted
        self.hosted_lab_ids: list[str] = []  # List of LabInstanceRequest IDs
        self.active_lab_count: int = 0

        # Timestamps
        self.provisioning_started: Optional[datetime] = None
        self.provisioning_completed: Optional[datetime] = None
        self.last_health_check: Optional[datetime] = None

        # Error information
        self.error_message: Optional[str] = None
        self.error_count: int = 0

    def add_condition(self, condition: LabWorkerCondition) -> None:
        """Add or update a condition."""
        # Remove existing condition of the same type
        self.conditions = [c for c in self.conditions if c.type != condition.type]
        self.conditions.append(condition)
        self.last_updated = datetime.now()

    def get_condition(self, condition_type: LabWorkerConditionType) -> Optional[LabWorkerCondition]:
        """Get a condition by type."""
        for condition in self.conditions:
            if condition.type == condition_type:
                return condition
        return None

    def is_condition_true(self, condition_type: LabWorkerConditionType) -> bool:
        """Check if a condition is true."""
        condition = self.get_condition(condition_type)
        return condition is not None and condition.status

    def can_accept_labs(self) -> bool:
        """Check if the worker can accept new lab instances."""
        return self.phase in [LabWorkerPhase.READY, LabWorkerPhase.ACTIVE, LabWorkerPhase.READY_UNLICENSED] and self.cml_ready and self.capacity is not None and self.active_lab_count < self.capacity.max_concurrent_labs

    def is_draining(self) -> bool:
        """Check if the worker is draining."""
        return self.phase == LabWorkerPhase.DRAINING

    def is_terminating(self) -> bool:
        """Check if the worker is terminating."""
        return self.phase in [LabWorkerPhase.STOPPING, LabWorkerPhase.TERMINATING_EC2, LabWorkerPhase.TERMINATED]

    def is_healthy(self) -> bool:
        """Check if the worker is healthy."""
        return self.phase not in [LabWorkerPhase.FAILED, LabWorkerPhase.TERMINATED] and self.ec2_state == "running" and self.cml_ready and self.is_condition_true(LabWorkerConditionType.HEALTH_CHECK_PASSED)


class LabWorkerStateMachine(StateMachineEngine[LabWorkerPhase]):
    """State machine for LabWorker lifecycle management."""

    def __init__(self):
        # Define valid state transitions
        transitions = {
            LabWorkerPhase.PENDING: [LabWorkerPhase.PROVISIONING_EC2, LabWorkerPhase.FAILED],
            LabWorkerPhase.PROVISIONING_EC2: [LabWorkerPhase.EC2_READY, LabWorkerPhase.FAILED],
            LabWorkerPhase.EC2_READY: [LabWorkerPhase.STARTING, LabWorkerPhase.FAILED],
            LabWorkerPhase.STARTING: [LabWorkerPhase.READY_UNLICENSED, LabWorkerPhase.LICENSING, LabWorkerPhase.FAILED],
            LabWorkerPhase.READY_UNLICENSED: [LabWorkerPhase.LICENSING, LabWorkerPhase.ACTIVE, LabWorkerPhase.DRAINING, LabWorkerPhase.FAILED],
            LabWorkerPhase.LICENSING: [LabWorkerPhase.READY, LabWorkerPhase.FAILED],
            LabWorkerPhase.READY: [LabWorkerPhase.ACTIVE, LabWorkerPhase.DRAINING, LabWorkerPhase.UNLICENSING, LabWorkerPhase.FAILED],
            LabWorkerPhase.ACTIVE: [LabWorkerPhase.READY, LabWorkerPhase.DRAINING, LabWorkerPhase.FAILED],  # No labs running
            LabWorkerPhase.DRAINING: [LabWorkerPhase.READY, LabWorkerPhase.UNLICENSING, LabWorkerPhase.STOPPING, LabWorkerPhase.FAILED],  # All labs finished
            LabWorkerPhase.UNLICENSING: [LabWorkerPhase.READY_UNLICENSED, LabWorkerPhase.STOPPING, LabWorkerPhase.FAILED],
            LabWorkerPhase.STOPPING: [LabWorkerPhase.TERMINATING_EC2, LabWorkerPhase.FAILED],
            LabWorkerPhase.TERMINATING_EC2: [LabWorkerPhase.TERMINATED, LabWorkerPhase.FAILED],
            LabWorkerPhase.TERMINATED: [],  # Terminal state
            LabWorkerPhase.FAILED: [LabWorkerPhase.STOPPING, LabWorkerPhase.TERMINATING_EC2],  # Allow recovery attempt
        }

        super().__init__(initial_state=LabWorkerPhase.PENDING, transitions=transitions)


class LabWorker(Resource[LabWorkerSpec, LabWorkerStatus]):
    """Complete LabWorker resource with spec, status, and state machine."""

    def __init__(self, metadata: ResourceMetadata, spec: LabWorkerSpec, status: Optional[LabWorkerStatus] = None):
        super().__init__(api_version="lab.neuroglia.io/v1", kind="LabWorker", metadata=metadata, spec=spec, status=status or LabWorkerStatus(), state_machine=LabWorkerStateMachine())

    def transition_to_phase(self, new_phase: LabWorkerPhase, reason: str) -> bool:
        """Transition to a new phase with validation."""
        if self.state_machine.transition(new_phase):
            self.status.phase = new_phase
            self.status.last_updated = datetime.now()
            return True
        return False

    def is_provisioned(self) -> bool:
        """Check if EC2 instance is provisioned."""
        return self.status.ec2_instance_id is not None and self.status.ec2_state == "running"

    def is_licensed(self) -> bool:
        """Check if CML is licensed."""
        return self.status.cml_licensed

    def is_ready_for_labs(self) -> bool:
        """Check if worker is ready to host lab instances."""
        return self.status.can_accept_labs()

    def get_capacity_info(self) -> Optional[ResourceCapacity]:
        """Get current capacity information."""
        return self.status.capacity

    def add_lab_instance(self, lab_id: str) -> bool:
        """Add a lab instance to this worker."""
        if not self.status.can_accept_labs():
            return False

        if lab_id not in self.status.hosted_lab_ids:
            self.status.hosted_lab_ids.append(lab_id)
            self.status.active_lab_count = len(self.status.hosted_lab_ids)

            # Transition to ACTIVE if first lab
            if self.status.active_lab_count == 1 and self.status.phase == LabWorkerPhase.READY:
                self.transition_to_phase(LabWorkerPhase.ACTIVE, "FirstLabAdded")

        return True

    def remove_lab_instance(self, lab_id: str) -> bool:
        """Remove a lab instance from this worker."""
        if lab_id in self.status.hosted_lab_ids:
            self.status.hosted_lab_ids.remove(lab_id)
            self.status.active_lab_count = len(self.status.hosted_lab_ids)

            # Transition back to READY if no labs
            if self.status.active_lab_count == 0 and self.status.phase == LabWorkerPhase.ACTIVE:
                self.transition_to_phase(LabWorkerPhase.READY, "AllLabsRemoved")

            return True
        return False

    def get_utilization_metrics(self) -> dict[str, float]:
        """Get resource utilization metrics."""
        if not self.status.capacity:
            return {}

        return {"cpu_utilization_percent": self.status.capacity.cpu_utilization_percent, "memory_utilization_percent": self.status.capacity.memory_utilization_percent, "storage_utilization_percent": self.status.capacity.storage_utilization_percent, "lab_count": self.status.active_lab_count, "max_labs": self.status.capacity.max_concurrent_labs}
