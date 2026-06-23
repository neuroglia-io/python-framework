# ResourceAllocator Service

The ResourceAllocator service provides resource allocation and availability checking for lab instances in the
Resource Oriented Architecture (ROA) sample. It manages CPU, memory, and other resource limits for containers,
ensuring efficient resource utilization and preventing over-allocation.

## 🎯 Overview

The ResourceAllocator implements a simple in-memory resource management system that:

- **Tracks Available Resources**: Monitors total CPU cores and memory
- **Checks Availability**: Validates if requested resources can be allocated
- **Allocates Resources**: Reserves resources for lab instances
- **Releases Resources**: Frees up resources when lab instances complete
- **Prevents Over-allocation**: Ensures resource requests don't exceed capacity

## 🏗️ Architecture Integration

The ResourceAllocator integrates with the LabInstanceController as shown in the highlighted line:

```python
# From LabInstanceController line 318:
return await self.resource_allocator.check_availability(resource.spec.resource_limits)
```

### Dependency Flow

```text
LabInstanceController
         │
         ▼
  ResourceAllocator ──── Tracks ──── CPU & Memory Resources
         │                               │
         ▼                               ▼
   Allocation Logic              Resource Accounting
```

## 🚀 Key Features

### Resource Format Support

Supports multiple resource limit formats:

```python
# CPU as string numbers
{"cpu": "1", "memory": "2Gi"}      # 1 CPU core, 2GB RAM
{"cpu": "0.5", "memory": "512Mi"}  # 0.5 CPU core, 512MB RAM
{"cpu": "2.5", "memory": "4Gi"}    # 2.5 CPU cores, 4GB RAM

# Memory in various units
{"cpu": "1", "memory": "1Gi"}      # Gigabytes
{"cpu": "1", "memory": "1024Mi"}   # Megabytes
{"cpu": "1", "memory": "2G"}       # Alternative GB format
```

### Resource Tracking

```python
# Get current resource usage
usage = allocator.get_resource_usage()
print(f"CPU: {usage['cpu_utilization']:.1f}%")
print(f"Memory: {usage['memory_utilization']:.1f}%")
print(f"Active allocations: {usage['active_allocations']}")
```

### Error Handling

```python
try:
    allocation = await allocator.allocate_resources(resource_limits)
except ValueError as e:
    # Handle insufficient resources
    print(f"Resource allocation failed: {e}")
```

## 📋 API Reference

### ResourceAllocator Class

#### Constructor

```python
ResourceAllocator(total_cpu: float = 32.0, total_memory_gb: int = 128)
```

**Parameters:**

- `total_cpu`: Total CPU cores available for allocation
- `total_memory_gb`: Total memory in GB available for allocation

#### Core Methods

##### `check_availability(resource_limits: Dict[str, str]) -> bool`

Checks if the requested resources are available for allocation.

**Parameters:**

- `resource_limits`: Dictionary with resource requirements (e.g., `{"cpu": "2", "memory": "4Gi"}`)

**Returns:**

- `True` if resources are available, `False` otherwise

**Example:**

```python
available = await allocator.check_availability({"cpu": "2", "memory": "4Gi"})
if available:
    print("Resources are available")
```

##### `allocate_resources(resource_limits: Dict[str, str]) -> Dict[str, str]`

Allocates resources for a lab instance.

**Parameters:**

- `resource_limits`: Dictionary with resource requirements

**Returns:**

- Allocation dictionary that can be stored in resource status

**Raises:**

- `ValueError`: If resources are not available or limits are invalid

**Example:**

```python
allocation = await allocator.allocate_resources({"cpu": "2", "memory": "4Gi"})
print(f"Allocated: {allocation['allocation_id']}")
```

##### `release_resources(allocation_data: Dict[str, str]) -> None`

Releases previously allocated resources.

**Parameters:**

- `allocation_data`: Allocation dictionary returned by `allocate_resources`

**Example:**

```python
await allocator.release_resources(allocation)
print("Resources released")
```

#### Utility Methods

##### `get_resource_usage() -> Dict[str, float]`

Returns current resource usage statistics.

**Returns:**

```python
{
    "total_cpu": 8.0,
    "allocated_cpu": 3.0,
    "available_cpu": 5.0,
    "cpu_utilization": 37.5,
    "total_memory_mb": 16384,
    "allocated_memory_mb": 6144,
    "available_memory_mb": 10240,
    "memory_utilization": 37.5,
    "active_allocations": 2
}
```

##### `get_active_allocations() -> Dict[str, Dict[str, str]]`

Returns information about all active allocations.

##### `cleanup_expired_allocations(max_age_hours: int = 24) -> int`

Cleans up allocations older than the specified age.

## 🔧 Configuration Examples

### Development Environment

```python
# Small development setup
allocator = ResourceAllocator(
    total_cpu=4.0,      # 4 CPU cores
    total_memory_gb=8   # 8 GB RAM
)
```

### Production Environment

```python
# Large production setup
allocator = ResourceAllocator(
    total_cpu=64.0,     # 64 CPU cores
    total_memory_gb=256 # 256 GB RAM
)
```

### Environment-based Configuration

```python
import os

allocator = ResourceAllocator(
    total_cpu=float(os.getenv("TOTAL_CPU_CORES", "32")),
    total_memory_gb=int(os.getenv("TOTAL_MEMORY_GB", "128"))
)
```

## 🎮 Usage in LabInstanceController

The ResourceAllocator is used throughout the controller lifecycle:

### 1. Resource Availability Check (Pending Phase)

```python
async def _reconcile_pending_phase(self, resource: LabInstanceRequest) -> ReconciliationResult:
    # Check resource availability
    resources_available = await self._check_resource_availability(resource)
    if not resources_available:
        return ReconciliationResult.requeue_after(
            timedelta(minutes=2),
            "Waiting for resources to become available"
        )
```

### 2. Resource Allocation (Provisioning Phase)

```python
async def _transition_to_provisioning(self, resource: LabInstanceRequest) -> None:
    # Allocate resources
    allocation = await self.resource_allocator.allocate_resources(resource.spec.resource_limits)

    # Store allocation in resource status
    resource.status.resource_allocation = allocation
```

### 3. Resource Release (Completion/Failure)

```python
async def _transition_to_completed(self, resource: LabInstanceRequest) -> None:
    # Release resources
    if resource.status.resource_allocation:
        await self.resource_allocator.release_resources(resource.status.resource_allocation)
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_resource_allocator.py
```

Run the controller integration demo:

```bash
python demo_controller_integration.py
```

View the setup example:

```bash
python example_controller_setup.py
```

## 📊 Monitoring and Observability

### Resource Usage Tracking

```python
# Monitor resource utilization
usage = allocator.get_resource_usage()
if usage['cpu_utilization'] > 80:
    print("High CPU utilization warning")

if usage['memory_utilization'] > 90:
    print("High memory utilization warning")
```

### Active Allocation Monitoring

```python
# Monitor active allocations
allocations = allocator.get_active_allocations()
for alloc_id, alloc_info in allocations.items():
    print(f"{alloc_id}: {alloc_info['cpu']} CPU, {alloc_info['memory']} Memory")
```

### Cleanup Monitoring

```python
# Periodic cleanup of expired allocations
cleaned_up = await allocator.cleanup_expired_allocations(max_age_hours=24)
if cleaned_up > 0:
    print(f"Cleaned up {cleaned_up} expired allocations")
```

## 🔗 Related Components

- **LabInstanceController**: Uses ResourceAllocator for resource management
- **ContainerService**: Works with ResourceAllocator to provision containers
- **LabInstanceRequest**: Defines resource requirements that ResourceAllocator manages

## 🎯 Design Principles

### 1. Simple and Reliable

The ResourceAllocator uses a straightforward in-memory approach that's easy to understand and debug.

### 2. Fail-Safe Resource Management

- Always checks availability before allocation
- Prevents over-allocation with clear error messages
- Handles invalid resource formats gracefully

### 3. Observable and Monitorable

- Provides detailed usage statistics
- Tracks all active allocations
- Includes logging for debugging

### 4. Flexible Resource Formats

- Supports multiple memory units (Mi, Gi, M, G)
- Accepts fractional CPU values
- Validates resource limits on input

## 🚀 Future Enhancements

Potential improvements for production use:

1. **Persistent Storage**: Store allocations in a database for restart resilience
2. **Resource Quotas**: Per-user or per-namespace resource limits
3. **Resource Reservations**: Advance booking of resources for scheduled labs
4. **Multi-Node Support**: Distribute resources across multiple nodes
5. **Resource Metrics**: Integration with Prometheus/Grafana for monitoring
6. **Resource Policies**: Complex allocation policies and priorities

The current implementation provides a solid foundation that can be extended based on specific requirements.
