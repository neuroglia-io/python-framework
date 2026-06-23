# Cloud Provider SPI Migration Summary

## Overview

This document describes the refactoring of the Lab Resource Manager to use a **Cloud Provider Service Provider Interface (SPI)** abstraction layer instead of directly depending on AWS EC2 services.

## Motivation

The original implementation directly used `Ec2ProvisioningService` with boto3, which created several issues:

1. **Vendor Lock-in**: Tightly coupled to AWS EC2, making multi-cloud support impossible
2. **API Stability**: Direct dependency on boto3 and EC2 API meant changes would break our code
3. **Testing Difficulty**: Required AWS credentials and real infrastructure for testing
4. **Limited Flexibility**: Could not support Azure, GCP, on-premises, or custom providers

## Solution: Cloud Provider SPI Pattern

We created an abstract `CloudProviderSPI` interface that defines a provider-agnostic contract for cloud infrastructure provisioning.

### Benefits

✅ **Multi-Cloud Support**: Can easily add Azure, GCP, or on-premises implementations
✅ **API Stability**: Isolates from provider-specific API changes
✅ **Testability**: Easy to mock, no cloud credentials needed for tests
✅ **Flexibility**: Supports custom providers (e.g., private cloud, bare metal)
✅ **Clean Architecture**: Follows established SPI pattern from CML integration

## Implementation Components

### 1. Cloud Provider SPI Interface

**File**: `samples/lab_resource_manager/integration/services/cloud_provider_spi.py` (365 lines)

**Key Abstractions**:

```python
# Generic instance states (provider-agnostic)
class InstanceState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    UNKNOWN = "unknown"

# Generic volume types
class VolumeType(Enum):
    STANDARD = "standard"
    SSD = "ssd"
    PROVISIONED_IOPS_SSD = "provisioned_iops_ssd"
    THROUGHPUT_OPTIMIZED = "throughput_optimized"
    COLD_STORAGE = "cold_storage"
```

**Configuration Classes**:

- `VolumeConfiguration`: Generic volume specs (size, type, IOPS, encryption)
- `NetworkConfiguration`: Generic networking (VPC/VNet, subnet, security groups, IPs)
- `InstanceConfiguration`: Complete instance specification with validation

**InstanceInfo** (Provider-Agnostic Instance Details):

```python
@dataclass
class InstanceInfo:
    instance_id: str
    name: str
    state: InstanceState
    instance_type: str
    public_ip: Optional[str]
    private_ip: Optional[str]
    public_dns: Optional[str]
    private_dns: Optional[str]
    availability_zone: str
    region: str
    launch_time: Optional[datetime]
    termination_time: Optional[datetime]
    provider_data: Dict[str, str]  # Provider-specific extensions
```

**CloudProviderSPI Abstract Interface** (12 methods):

```python
class CloudProviderSPI(ABC):
    @abstractmethod
    async def provision_instance(self, config: InstanceConfiguration) -> InstanceInfo: ...

    @abstractmethod
    async def get_instance_info(self, instance_id: str) -> InstanceInfo: ...

    @abstractmethod
    async def wait_for_instance_running(self, instance_id: str, timeout_seconds: int = 600) -> InstanceInfo: ...

    @abstractmethod
    async def stop_instance(self, instance_id: str) -> None: ...

    @abstractmethod
    async def start_instance(self, instance_id: str) -> None: ...

    @abstractmethod
    async def terminate_instance(self, instance_id: str) -> None: ...

    @abstractmethod
    async def wait_for_instance_terminated(self, instance_id: str, timeout_seconds: int = 300) -> None: ...

    @abstractmethod
    async def add_tags(self, instance_id: str, tags: Dict[str, str]) -> None: ...

    @abstractmethod
    async def list_instances(self, filters: Optional[Dict[str, str]] = None) -> List[InstanceInfo]: ...

    @abstractmethod
    async def get_console_output(self, instance_id: str) -> str: ...

    @abstractmethod
    def get_provider_name(self) -> str: ...
```

**Exception Hierarchy**:

```python
class CloudProvisioningError(Exception):
    """Base exception for cloud provisioning errors."""

class InstanceNotFoundError(CloudProvisioningError):
    """Instance does not exist."""

class InstanceProvisioningError(CloudProvisioningError):
    """Failed to provision instance."""

class InstanceOperationError(CloudProvisioningError):
    """Failed to perform operation on instance."""
```

### 2. AWS EC2 Cloud Provider Implementation

**File**: `samples/lab_resource_manager/integration/services/aws_ec2_cloud_provider.py` (668 lines)

**Features**:

- Implements `CloudProviderSPI` interface for AWS EC2
- Maps generic abstractions to AWS-specific concepts
- Handles boto3 interactions internally
- Converts EC2 responses to provider-agnostic `InstanceInfo`
- Uses AWS-specific `provider_data` for EC2-specific fields

**Key Mapping Examples**:

```python
# Generic InstanceState → AWS EC2 State
state_mapping = {
    "pending": InstanceState.PENDING,
    "running": InstanceState.RUNNING,
    "stopping": InstanceState.STOPPING,
    "stopped": InstanceState.STOPPED,
    "shutting-down": InstanceState.TERMINATING,
    "terminated": InstanceState.TERMINATED,
}

# Generic VolumeType → AWS EBS Volume Type
def _map_volume_type(self, volume_type: VolumeType) -> str:
    mapping = {
        VolumeType.STANDARD: "standard",
        VolumeType.SSD: "gp3",
        VolumeType.PROVISIONED_IOPS_SSD: "io1",
        VolumeType.THROUGHPUT_OPTIMIZED: "st1",
        VolumeType.COLD_STORAGE: "sc1",
    }
    return mapping.get(volume_type, "gp3")
```

**Usage Example**:

```python
# Initialize AWS provider
aws_provider = AwsEc2CloudProvider(
    aws_access_key_id="...",
    aws_secret_access_key="...",
    region_name="us-west-2"
)

# Use provider-agnostic API
config = InstanceConfiguration(...)
instance_info = await aws_provider.provision_instance(config)

# Provider-agnostic instance info
print(f"Instance {instance_info.instance_id} is {instance_info.state}")
```

### 3. Updated LabWorker Controller

**File**: `samples/lab_resource_manager/domain/controllers/lab_worker_controller.py`

**Changes Required** (to be completed):

```python
# OLD
from integration.services.ec2_service import (
    Ec2ProvisioningService,
    Ec2ProvisioningError,
)

class LabWorkerController(ResourceControllerBase):
    def __init__(self, service_provider, ec2_service: Ec2ProvisioningService, ...):
        self.ec2_service = ec2_service

# NEW
from integration.services import (
    CloudProviderSPI,
    InstanceProvisioningError,
    InstanceNotFoundError,
    InstanceOperationError,
)

class LabWorkerController(ResourceControllerBase):
    def __init__(self, service_provider, cloud_provider: CloudProviderSPI, ...):
        self.cloud_provider = cloud_provider
```

**Find-and-Replace Changes**:

1. `self.ec2_service` → `self.cloud_provider`
2. `Ec2ProvisioningError` → `InstanceOperationError` (or appropriate exception)
3. Update provision_instance() calls to use `InstanceConfiguration`
4. Update response handling to use `InstanceInfo` instead of `Ec2InstanceInfo`

### 4. Updated Service Exports

**File**: `samples/lab_resource_manager/integration/services/__init__.py`

**New Exports**:

```python
from .cloud_provider_spi import (
    CloudProviderSPI,
    CloudProvisioningError,
    InstanceConfiguration,
    InstanceInfo,
    InstanceNotFoundError,
    InstanceOperationError,
    InstanceProvisioningError,
    InstanceState,
    NetworkConfiguration,
    VolumeConfiguration,
    VolumeType,
)
from .aws_ec2_cloud_provider import AwsEc2CloudProvider

__all__ = [
    # Cloud Provider Abstraction
    "CloudProviderSPI",
    "AwsEc2CloudProvider",
    "CloudProvisioningError",
    "InstanceNotFoundError",
    "InstanceProvisioningError",
    "InstanceOperationError",
    "InstanceConfiguration",
    "InstanceInfo",
    "InstanceState",
    "NetworkConfiguration",
    "VolumeConfiguration",
    "VolumeType",
    # ... existing exports
]
```

## Future Provider Implementations

### Azure Cloud Provider (Example Stub)

```python
from integration.services import CloudProviderSPI

class AzureCloudProvider(CloudProviderSPI):
    """Azure implementation of CloudProviderSPI."""

    def get_provider_name(self) -> str:
        return "Azure"

    async def provision_instance(self, config: InstanceConfiguration) -> InstanceInfo:
        # Map InstanceConfiguration → Azure VM specs
        # Use azure.mgmt.compute to create VM
        # Return InstanceInfo with Azure-specific provider_data
        pass

    # ... implement other methods
```

### GCP Cloud Provider (Example Stub)

```python
from integration.services import CloudProviderSPI

class GcpCloudProvider(CloudProviderSPI):
    """Google Cloud Platform implementation of CloudProviderSPI."""

    def get_provider_name(self) -> str:
        return "GCP"

    async def provision_instance(self, config: InstanceConfiguration) -> InstanceInfo:
        # Map InstanceConfiguration → GCP instance specs
        # Use google-cloud-compute to create instance
        # Return InstanceInfo with GCP-specific provider_data
        pass

    # ... implement other methods
```

### On-Premises Provider (Example Stub)

```python
from integration.services import CloudProviderSPI

class OnPremisesCloudProvider(CloudProviderSPI):
    """On-premises infrastructure implementation using libvirt/KVM."""

    def get_provider_name(self) -> str:
        return "OnPremises"

    async def provision_instance(self, config: InstanceConfiguration) -> InstanceInfo:
        # Map InstanceConfiguration → KVM VM specs
        # Use libvirt to create VM
        # Return InstanceInfo with KVM-specific provider_data
        pass

    # ... implement other methods
```

## Testing Strategy

### Unit Testing with Mocks

```python
from unittest.mock import Mock, AsyncMock
from integration.services import CloudProviderSPI, InstanceInfo, InstanceState

class TestLabWorkerController:
    def setup_method(self):
        # Mock cloud provider - no AWS credentials needed!
        self.cloud_provider = Mock(spec=CloudProviderSPI)
        self.cloud_provider.provision_instance = AsyncMock(return_value=InstanceInfo(
            instance_id="i-mock123",
            name="test-worker",
            state=InstanceState.RUNNING,
            instance_type="m5zn.metal",
            public_ip="1.2.3.4",
            private_ip="10.0.1.10",
            region="us-west-2",
            availability_zone="us-west-2a",
            provider_data={}
        ))

        self.controller = LabWorkerController(
            service_provider=mock_service_provider,
            cloud_provider=self.cloud_provider,  # Mocked!
            cml_client=mock_cml_client
        )

    async def test_provision_worker(self):
        # Test without real AWS infrastructure
        result = await self.controller.reconcile(test_worker_resource)
        assert result.is_success
        self.cloud_provider.provision_instance.assert_called_once()
```

### Integration Testing with Real Providers

```python
# Test with real AWS
aws_provider = AwsEc2CloudProvider(region_name="us-west-2")
controller = LabWorkerController(cloud_provider=aws_provider, ...)

# Test with real Azure
azure_provider = AzureCloudProvider(subscription_id="...", resource_group="...")
controller = LabWorkerController(cloud_provider=azure_provider, ...)
```

## Migration Checklist

- [x] Create CloudProviderSPI interface (365 lines)
- [x] Create AwsEc2CloudProvider implementation (668 lines)
- [x] Update service exports in **init**.py
- [ ] Update LabWorkerController constructor to use CloudProviderSPI
- [ ] Replace all `self.ec2_service` with `self.cloud_provider`
- [ ] Replace all `Ec2ProvisioningError` with appropriate SPI exceptions
- [ ] Update provision_instance() calls to use InstanceConfiguration
- [ ] Update response handling to use InstanceInfo
- [ ] Update LabWorkerPool controller (if needed)
- [ ] Update Worker Scheduler Service (if needed)
- [ ] Update startup/configuration to inject AwsEc2CloudProvider
- [ ] Update tests to use CloudProviderSPI mocks
- [ ] Update LABWORKER_IMPLEMENTATION_SUMMARY.md with cloud SPI info
- [ ] Remove old ec2_service.py file
- [ ] Test complete system with AWS provider

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Lab Resource Manager                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   CloudProviderSPI (Abstract)                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ + provision_instance(config) → InstanceInfo            │ │
│  │ + get_instance_info(id) → InstanceInfo                 │ │
│  │ + stop_instance(id)                                    │ │
│  │ + start_instance(id)                                   │ │
│  │ + terminate_instance(id)                               │ │
│  │ + list_instances(filters) → List[InstanceInfo]         │ │
│  │ + get_provider_name() → str                            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                    │                    │
         ┌──────────┴───────┬────────────┴────────┬──────────┐
         │                  │                     │          │
         ▼                  ▼                     ▼          ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐
│AwsEc2CloudProvider│ │AzureProvider│ │ GcpProvider │ │OnPremises │
│                  │ │              │ │             │ │  Provider  │
│ Uses: boto3      │ │ Uses: Azure  │ │ Uses: GCP   │ │Uses:libvirt│
│                  │ │      SDK     │ │     SDK     │ │            │
└──────────────────┘ └──────────────┘ └─────────────┘ └────────────┘
```

## Benefits Summary

### Before (Direct EC2 Dependency)

❌ Tightly coupled to AWS
❌ Vulnerable to boto3/EC2 API changes
❌ Cannot support other cloud providers
❌ Difficult to test without AWS credentials
❌ Provider-specific code throughout application

### After (Cloud Provider SPI)

✅ Provider-agnostic architecture
✅ Isolated from API changes
✅ Multi-cloud ready (AWS, Azure, GCP, on-premises)
✅ Easy to mock and test
✅ Clean separation of concerns
✅ Follows established SPI pattern (like CML integration)
✅ Flexible and extensible

## Conclusion

The Cloud Provider SPI abstraction is a critical architectural improvement that:

1. **Protects** the application from cloud provider API changes
2. **Enables** multi-cloud and hybrid cloud deployments
3. **Improves** testability with mockable interfaces
4. **Follows** established patterns from CML integration
5. **Maintains** clean architecture principles

This refactoring demonstrates the value of interface-based design and the Service Provider Interface pattern in building maintainable, flexible cloud-native applications.

---

**Status**: Interface and AWS implementation complete. Controller refactoring in progress.

**Next Steps**: Complete LabWorker Controller migration to use CloudProviderSPI.
