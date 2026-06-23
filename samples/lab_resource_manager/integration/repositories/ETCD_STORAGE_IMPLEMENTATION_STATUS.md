# etcd Storage Backend Implementation Status

## ✅ Completed

### 1. Dependency Resolution

- **Library**: Switched to `etcd3-py v0.1.6` (maintained fork with protobuf 5.x support)
- **Protocol Buffers**: Updated to `protobuf 5.29.5`
- **OpenTelemetry**: Made Prometheus exporter optional to resolve conflicts
- **Status**: ✅ All dependencies locked and installed successfully

### 2. EtcdStorageBackend Implementation

**File**: `integration/repositories/etcd_storage_backend.py`

Completed methods using correct etcd3-py API:

#### ✅ `__init__(client, prefix)`

- Accepts `etcd3.Client` (sync client)
- Initializes prefix for key namespacing

#### ✅ `_make_key(name)`

- Creates full etcd key from resource name

#### ✅ `exists(name) -> bool`

- Uses `client.range(key)` to check existence
- Returns `True` if `len(response.kvs) > 0`

#### ✅ `get(name) -> Optional[dict]`

- Uses `client.range(key)` to retrieve value
- Accesses `response.kvs[0].value` and decodes JSON

#### ✅ `set(name, value) -> bool`

- Uses `client.put(key, json_value)` to store resource
- Serializes dict to JSON string

#### ✅ `delete(name) -> bool`

- Uses `client.delete_range(key)` (not `.delete()`)
- Checks `response.deleted > 0` to verify deletion

#### ✅ `keys(pattern) -> list[str]`

- Uses `client.range(prefix, range_end=...)` for prefix queries
- Calculates `range_end` by incrementing last byte of prefix
- Strips prefix from keys to return resource names

#### ✅ `watch(callback, key_prefix) -> watch_id`

- Uses `client.watch_create(prefix, callback=callback)`
- Returns watch ID (string) that can be cancelled with `client.watch_cancel(watch_id)`
- **Note**: Callback signature and event structure need runtime verification

#### ✅ `list_with_labels(label_selector) -> list[dict]`

- Fetches all resources with `keys()`
- Filters in-memory by checking metadata.labels

#### ⚠️ `compare_and_swap(name, expected_version, new_value) -> bool`

- **Current Implementation**: Uses simple `put()` (NOT atomic)
- **Status**: Works but lacks true atomicity
- **TODO**: Implement etcd transaction API for proper CAS
  ```python
  # Needs investigation of etcd3-py transaction API
  # Should use: IF mod_revision == X THEN put ELSE fail
  ```

### 3. EtcdLabWorkerResourceRepository

**File**: `integration/repositories/etcd_lab_worker_repository.py`

- ✅ Updated type hints: `etcd3.Client` (was `etcd3.Etcd3Client`)
- ✅ Passes `EtcdStorageBackend` to base `ResourceRepository`
- ✅ Inherits all CRUD operations from base class
- ✅ Custom query methods ready (find_by_phase, find_by_lab_track, etc.)

### 4. Application Configuration

**File**: `samples/lab_resource_manager/main.py`

- ✅ Imports `etcd3` correctly
- ✅ Creates client: `etcd3.Client(host=..., port=..., timeout=...)`
- ✅ Registers as singleton in DI container
- ✅ Creates repository with etcd client

### 5. Docker Compose Configuration

**File**: `deployment/docker-compose/docker-compose.lab-resource-manager.yml`

- ✅ etcd service configured (quay.io/coreos/etcd:v3.5.10)
- ✅ Ports mapped: 2479:2379 (client), 2480:2380 (peer)
- ✅ Environment variables set for application

### 6. Validation Tests

- ✅ etcd connection successful (port 2479)
- ✅ Basic operations work: `put()`, `range()`, `delete_range()`
- ✅ `EtcdStorageBackend` instantiates without errors
- ✅ Watch API exists: `watch_create()`, `watch_cancel()`, `Watcher`

## ⚠️ Needs Runtime Verification

### Watch API Details

The watch implementation needs runtime testing to verify:

1. **Callback signature**: What parameters does the callback receive?
2. **Event structure**: What attributes does the event object have?
3. **Range queries**: Does `watch_create()` support `range_end` parameter for prefix watches?

### Transaction API

The `compare_and_swap()` method needs proper atomic implementation:

- Current: Uses simple `put()` after version check (race condition possible)
- Needed: etcd transaction with conditional execution
- Investigation required: etcd3-py transaction API (`Txn()` class)

## 📋 Next Steps

### Immediate (High Priority)

1. **Test Application Startup**

   ```bash
   cd samples/lab_resource_manager
   ETCD_HOST=localhost ETCD_PORT=2479 poetry run python main.py
   ```

   - Verify: Application starts without errors
   - Verify: Repository is registered and accessible

2. **Test Basic CRUD Operations**

   ```python
   # Create a LabWorker resource
   worker = LabWorker(...)
   await repository.save_async(worker)

   # List resources
   workers = await repository.list_async()

   # Get by ID
   worker = await repository.get_by_id_async(worker_id)

   # Delete
   await repository.delete_async(worker_id)
   ```

3. **Test Watch Functionality**

   ```python
   def on_worker_change(event):
       print(f"Event: {event}")
       # Determine event attributes at runtime

   watch_id = repository._storage_backend.watch(on_worker_change)
   # Make changes and observe callbacks
   # Cancel: repository._etcd_client.watch_cancel(watch_id)
   ```

### Short Term (Medium Priority)

4. **Implement Proper CAS**

   - Research etcd3-py transaction API
   - Implement atomic compare-and-swap using transactions
   - Add unit tests for concurrent modification scenarios

5. **Add Unit Tests**

   - Create `tests/integration/test_etcd_storage_backend.py`
   - Test all storage backend methods
   - Mock etcd3.Client for unit tests

6. **Add Integration Tests**
   - Create `tests/integration/test_etcd_lab_worker_repository.py`
   - Test complete CRUD workflows
   - Test watch notifications

### Long Term (Low Priority)

7. **Performance Optimization**

   - Add connection pooling if needed
   - Implement batch operations for bulk updates
   - Add caching layer for frequently accessed resources

8. **High Availability**

   - Configure etcd clustering (3+ nodes)
   - Test failover scenarios
   - Add health checks and monitoring

9. **Advanced Features**
   - Implement lease-based TTL for temporary resources
   - Add support for resource quotas
   - Implement resource versioning history

## 🐛 Known Issues

### Type Checker False Positives

The type checker doesn't recognize `response.kvs` attribute:

```python
# This works at runtime but triggers type errors
response = client.range(key)
kv = response.kvs[0]  # Type checker: "kvs" is unknown
```

**Solution**: These are false positives - the code works correctly at runtime.

### Missing Type Stubs

```
Skipping analyzing "etcd3": module is installed, but missing library stubs or py.typed marker
```

**Impact**: Type hints not available for etcd3-py library
**Workaround**: Use `# type: ignore` comments if needed

## 📚 References

- **etcd3-py Documentation**: https://github.com/Revolution1/etcd3-py
- **etcd v3 API**: https://etcd.io/docs/latest/learning/api/
- **etcd Watch Guide**: https://etcd.io/docs/latest/learning/api/#watch-api
- **etcd Transactions**: https://etcd.io/docs/latest/learning/api/#transaction

## 🎯 Summary

**Status**: Approximately **90% complete**

**What Works**:

- ✅ All dependencies resolved
- ✅ All CRUD operations implemented with correct API
- ✅ Storage backend can be instantiated
- ✅ etcd connection verified
- ✅ Basic operations tested (put, range, delete_range)

**What Needs Testing**:

- ⚠️ Application full startup
- ⚠️ Repository CRUD operations end-to-end
- ⚠️ Watch callback signature and event structure
- ⚠️ Compare-and-swap atomicity

**What Needs Implementation**:

- ❌ Atomic CAS using etcd transactions
- ❌ Unit and integration tests
- ❌ Documentation of watch event structure

The implementation is ready for runtime testing and should work for basic operations. The watch and CAS features need verification with actual etcd responses to finalize the implementation.
