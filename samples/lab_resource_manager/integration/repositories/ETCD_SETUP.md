# Lab Resource Manager with etcd Setup Guide

## Quick Start

### 1. Install etcd Support

```bash
# Install Python dependencies with etcd support
poetry install -E etcd

# Or using pip
pip install etcd3
```

### 2. Start etcd with Docker Compose

```bash
# Start the full stack (includes etcd, MongoDB, Keycloak, observability)
cd deployment/docker-compose
docker-compose -f docker-compose.shared.yml -f docker-compose.lab-resource-manager.yml up -d

# Check etcd health
docker exec lab-resource-manager-etcd etcdctl endpoint health
```

### 3. Run the Application

```bash
# From project root
cd samples/lab_resource_manager
python main.py

# Or use Poetry
poetry run python samples/lab_resource_manager/main.py
```

### 4. Access the API

- **API Documentation**: http://localhost:8003/api/docs
- **etcd Client API**: http://localhost:2479 (exposed from container)
- **etcd Metrics**: Check with `etcdctl` commands

## etcd CLI Commands

```bash
# List all lab workers
etcdctl get /lab-resource-manager/lab-workers/ --prefix --keys-only

# Get a specific worker
etcdctl get /lab-resource-manager/lab-workers/worker-001

# Watch for changes (real-time)
etcdctl watch /lab-resource-manager/lab-workers/ --prefix

# Delete all resources (CAREFUL!)
etcdctl del /lab-resource-manager/ --prefix

# Compact history (free space)
etcdctl compact $(etcdctl endpoint status --write-out="json" | egrep -o '"revision":[0-9]*' | egrep -o '[0-9]*')
```

## Configuration

### Environment Variables

```bash
# Local development (.env)
ETCD_HOST=localhost
ETCD_PORT=2379
ETCD_PREFIX=/lab-resource-manager
ETCD_TIMEOUT=10

# Docker environment
ETCD_HOST=etcd
ETCD_PORT=2379
ETCD_PREFIX=/lab-resource-manager
```

### Docker Compose Ports

- **etcd Client**: 2479 (maps to container 2379)
- **etcd Peer**: 2480 (maps to container 2380)
- **Lab Resource Manager**: 8003 (maps to container 8080)

## Architecture

```
┌─────────────────┐
│ Lab Resource    │
│ Manager App     │ ──── HTTP API ──────► Port 8003
│ (FastAPI)       │
└────────┬────────┘
         │
         │ etcd3 client
         │
┌────────▼────────┐
│  etcd v3        │
│  (Port 2379)    │ ──── etcdctl ──────► Port 2479
│                 │
└─────────────────┘
```

## Features Enabled by etcd

### 1. Real-time Watch API

```python
# Watch for lab worker changes in real-time
def on_worker_change(event):
    print(f"Worker changed: {event.key}")

watch_id = repository.watch_workers(on_worker_change)
```

### 2. Strong Consistency

All reads reflect the latest writes immediately (linearizable reads).

### 3. Atomic Updates

```python
# Compare-and-swap for safe concurrent updates
success = await backend.compare_and_swap(
    name="worker-001",
    expected_value=current_worker,
    new_value=updated_worker
)
```

### 4. Label-based Queries

```python
# Find workers by label selector
workers = await repository.find_by_lab_track_async("comp-sci-101")
```

## Troubleshooting

### etcd not starting

```bash
# Check logs
docker logs lab-resource-manager-etcd

# Check if port is already in use
lsof -i :2479

# Restart etcd
docker-compose restart etcd
```

### Connection refused

```bash
# Check etcd health
docker exec lab-resource-manager-etcd etcdctl endpoint health

# Check if etcd is listening
docker exec lab-resource-manager-etcd netstat -tuln | grep 2379

# Check from application container
docker exec lab-resource-manager-app curl http://etcd:2379/health
```

### etcd out of space

```bash
# Check etcd status
etcdctl endpoint status --write-out=table

# Compact history
etcdctl compact <revision>

# Defragment
etcdctl defrag
```

## Testing

### Unit Tests

```bash
# Run repository tests
pytest tests/integration/test_etcd_lab_worker_repository.py -v
```

### Manual Testing with etcdctl

```bash
# Put a test resource
etcdctl put /lab-resource-manager/lab-workers/test-001 '{"metadata":{"name":"test-001"}}'

# Get it back
etcdctl get /lab-resource-manager/lab-workers/test-001

# List all
etcdctl get /lab-resource-manager/ --prefix --keys-only

# Clean up
etcdctl del /lab-resource-manager/lab-workers/test-001
```

## Monitoring

### Health Check

```bash
# Check etcd health
curl http://localhost:2479/health

# Or use etcdctl
etcdctl endpoint health
```

### Metrics

```bash
# Get etcd metrics
curl http://localhost:2479/metrics

# Key metrics to watch:
# - etcd_server_has_leader
# - etcd_server_leader_changes_seen_total
# - etcd_disk_wal_fsync_duration_seconds
# - etcd_network_peer_round_trip_time_seconds
```

## Production Considerations

### Clustering

For production, run etcd in a cluster (3 or 5 nodes):

```yaml
etcd-1:
  environment:
    - ETCD_INITIAL_CLUSTER=etcd-1=http://etcd-1:2380,etcd-2=http://etcd-2:2380,etcd-3=http://etcd-3:2380
```

### Backup & Restore

```bash
# Backup
etcdctl snapshot save backup.db

# Restore
etcdctl snapshot restore backup.db
```

### Security

```bash
# Enable TLS
ETCD_CLIENT_CERT_AUTH=true
ETCD_TRUSTED_CA_FILE=/path/to/ca.crt
ETCD_CERT_FILE=/path/to/server.crt
ETCD_KEY_FILE=/path/to/server.key
```

## Next Steps

1. **Implement LabInstance Repository**: Create etcd-based repository for lab instances
2. **Add Watch Handlers**: Implement real-time controllers using watch API
3. **Enable Clustering**: Configure etcd cluster for high availability
4. **Add Metrics**: Integrate Prometheus for etcd monitoring
5. **Implement TTL**: Use leases for temporary worker resources

## Resources

- **etcd Documentation**: https://etcd.io/docs/
- **etcd3 Python Client**: https://python-etcd3.readthedocs.io/
- **ETCD_IMPLEMENTATION.md**: Detailed architecture and implementation guide
- **Kubernetes Resource Patterns**: https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
