# etcd Cheat Sheet for Beginners

## 📖 What is etcd?

**etcd** is a distributed, reliable key-value store that's used for storing configuration data, service discovery, and coordinating distributed systems. It's the same technology that powers Kubernetes for storing all cluster data.

**Key Features:**

- 🔍 **Strong consistency**: All nodes see the same data at the same time
- 👁️ **Watchable**: Get notified immediately when data changes
- ⚡ **Fast**: Optimized for read-heavy workloads
- 🔒 **Secure**: Supports TLS and authentication
- 🎯 **Simple**: HTTP/JSON API and easy-to-use CLI

---

## 🍎 Installing etcdctl on macOS

### Method 1: Using Homebrew (Recommended)

```bash
# Install etcd (includes etcdctl)
brew install etcd

# Verify installation
etcdctl version
```

Expected output:

```
etcdctl version: 3.5.10
API version: 3.5
```

### Method 2: Download Binary Directly

```bash
# Download etcd for macOS (ARM64 - Apple Silicon)
ETCD_VER=v3.5.10
curl -L https://github.com/etcd-io/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-darwin-arm64.zip -o etcd.zip

# Or for Intel Macs
curl -L https://github.com/etcd-io/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-darwin-amd64.zip -o etcd.zip

# Extract and install
unzip etcd.zip
cd etcd-${ETCD_VER}-darwin-*/
sudo cp etcdctl /usr/local/bin/

# Verify
etcdctl version
```

---

## 🐳 Connecting etcdctl to Docker Container

When etcd is running in a Docker container (like in the Lab Resource Manager stack), you need to configure `etcdctl` to connect to the correct endpoint.

### Quick Setup

```bash
# Set environment variables for your shell session
export ETCDCTL_API=3
export ETCDCTL_ENDPOINTS=http://localhost:2479

# Test connection
etcdctl endpoint health
```

Expected output:

```
http://localhost:2479 is healthy: successfully committed proposal: took = 2.456789ms
```

### Permanent Configuration

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# etcd configuration for Lab Resource Manager
export ETCDCTL_API=3
export ETCDCTL_ENDPOINTS=http://localhost:2479

# Optional: Create an alias
alias etcd-lab='etcdctl --endpoints=http://localhost:2479'
```

Then reload your shell:

```bash
source ~/.zshrc  # or ~/.bashrc
```

### Alternative: Using Docker Exec

If you don't want to install `etcdctl` locally, you can use it directly from the Docker container:

```bash
# Run etcdctl inside the container
docker exec lab-resource-manager-etcd etcdctl endpoint health

# Create an alias for convenience
alias etcdctl='docker exec lab-resource-manager-etcd etcdctl'

# Now you can use etcdctl as if it's installed locally
etcdctl version
```

---

## 🚀 Basic Commands

### Health & Status Checks

```bash
# Check if etcd is healthy
etcdctl endpoint health

# Get detailed endpoint status
etcdctl endpoint status

# Show status in table format
etcdctl endpoint status --write-out=table

# Get member list (for clusters)
etcdctl member list
```

### Writing Data (PUT)

```bash
# Store a simple key-value pair
etcdctl put /mykey "myvalue"

# Store JSON data
etcdctl put /users/john '{"name":"John Doe","email":"john@example.com"}'

# Store with a prefix (organizational structure)
etcdctl put /lab-resource-manager/lab-workers/worker-001 '{"status":"ready"}'
```

### Reading Data (GET)

```bash
# Get a single key
etcdctl get /mykey

# Get with value only (no key in output)
etcdctl get /mykey --print-value-only

# Get all keys with a prefix
etcdctl get /lab-resource-manager/lab-workers/ --prefix

# Get keys only (without values)
etcdctl get /lab-resource-manager/lab-workers/ --prefix --keys-only

# Get with detailed info (revision, version)
etcdctl get /mykey --write-out=json | jq

# Count keys with a prefix
etcdctl get /lab-resource-manager/lab-workers/ --prefix --keys-only | wc -l
```

### Deleting Data (DEL)

```bash
# Delete a single key
etcdctl del /mykey

# Delete all keys with a prefix (CAREFUL!)
etcdctl del /lab-resource-manager/lab-workers/ --prefix

# Delete and show deleted count
etcdctl del /mykey --prev-kv
```

---

## 👁️ Watching for Changes (Real-time Updates)

One of etcd's most powerful features is the ability to **watch** for changes in real-time.

### Basic Watch

```bash
# Watch a specific key
etcdctl watch /mykey

# Watch all keys with a prefix
etcdctl watch /lab-resource-manager/lab-workers/ --prefix

# Watch and show previous value on updates
etcdctl watch /mykey --prev-kv
```

### Watch in Action

Open **two terminals**:

**Terminal 1 (Watcher):**

```bash
etcdctl watch /lab-resource-manager/lab-workers/ --prefix
```

**Terminal 2 (Writer):**

```bash
etcdctl put /lab-resource-manager/lab-workers/worker-001 '{"phase":"ready"}'
etcdctl put /lab-resource-manager/lab-workers/worker-002 '{"phase":"pending"}'
etcdctl del /lab-resource-manager/lab-workers/worker-001
```

You'll see changes appear **immediately** in Terminal 1! This is how Kubernetes controllers work.

---

## 🔍 Lab Resource Manager Specific Commands

### List All Resources

```bash
# List all lab workers (keys only)
etcdctl get /lab-resource-manager/lab-workers/ --prefix --keys-only

# List all lab instances
etcdctl get /lab-resource-manager/lab-instances/ --prefix --keys-only

# List everything in the lab resource manager namespace
etcdctl get /lab-resource-manager/ --prefix --keys-only
```

### Get Resource Details

```bash
# Get a specific lab worker
etcdctl get /lab-resource-manager/lab-workers/worker-001

# Get with pretty JSON formatting (requires jq)
etcdctl get /lab-resource-manager/lab-workers/worker-001 --print-value-only | jq

# Get all workers and format as JSON array
etcdctl get /lab-resource-manager/lab-workers/ --prefix --print-value-only | jq -s '.'
```

### Watch Lab Workers in Real-time

```bash
# Watch all lab worker changes
etcdctl watch /lab-resource-manager/lab-workers/ --prefix

# Watch and format output
etcdctl watch /lab-resource-manager/lab-workers/ --prefix | while read -r line; do
    echo "$(date): $line"
done
```

### Testing & Development

```bash
# Create a test worker
etcdctl put /lab-resource-manager/lab-workers/test-worker-001 '{
  "metadata": {
    "name": "test-worker-001",
    "namespace": "default",
    "labels": {"env": "test"}
  },
  "spec": {
    "capacity": 10
  },
  "status": {
    "phase": "ready"
  }
}'

# Get it back
etcdctl get /lab-resource-manager/lab-workers/test-worker-001 --print-value-only | jq

# Delete test data
etcdctl del /lab-resource-manager/lab-workers/test-worker-001
```

---

## 🧹 Maintenance Commands

### Compaction (Free Up Space)

etcd keeps a history of all changes. Over time, this can grow large. Compaction removes old revisions.

```bash
# Get current revision
etcdctl endpoint status --write-out=json | jq -r '.[0].Status.header.revision'

# Compact up to current revision (keeps only latest)
REVISION=$(etcdctl endpoint status --write-out=json | jq -r '.[0].Status.header.revision')
etcdctl compact $REVISION

# Defragment to reclaim disk space
etcdctl defrag
```

### Backup & Restore

```bash
# Create a snapshot backup
etcdctl snapshot save backup-$(date +%Y%m%d-%H%M%S).db

# Check snapshot status
etcdctl snapshot status backup-20241102-143000.db

# Restore from snapshot (for disaster recovery)
etcdctl snapshot restore backup-20241102-143000.db --data-dir=/tmp/etcd-restore
```

### Clear All Data (Development Only!)

```bash
# ⚠️ WARNING: This deletes EVERYTHING! Use with caution!
etcdctl del "" --from-key=true

# Safer: Delete only lab-resource-manager data
etcdctl del /lab-resource-manager/ --prefix
```

---

## 🐛 Troubleshooting

### Connection Issues

```bash
# Test if etcd is accessible
curl http://localhost:2479/health

# Check if Docker container is running
docker ps | grep etcd

# Check container logs
docker logs lab-resource-manager-etcd

# Restart etcd container
docker restart lab-resource-manager-etcd
```

### Authentication Errors

```bash
# If you see "etcdserver: user name is empty"
# Make sure ETCDCTL_API=3 is set
export ETCDCTL_API=3

# If using auth, provide credentials
etcdctl --user=root:password get /mykey
```

### Performance Issues

```bash
# Check endpoint metrics
etcdctl endpoint status --write-out=table

# Check if compaction is needed
etcdctl endpoint status --write-out=json | jq -r '.[0].Status.dbSize'

# Monitor real-time metrics
watch -n 1 'etcdctl endpoint status --write-out=table'
```

---

## 💡 Advanced Tips & Tricks

### Using jq for JSON Formatting

```bash
# Pretty print a resource
etcdctl get /lab-resource-manager/lab-workers/worker-001 --print-value-only | jq '.'

# Extract specific field
etcdctl get /lab-resource-manager/lab-workers/worker-001 --print-value-only | jq -r '.status.phase'

# List all worker names
etcdctl get /lab-resource-manager/lab-workers/ --prefix --print-value-only | jq -r '.metadata.name'

# Filter by condition
etcdctl get /lab-resource-manager/lab-workers/ --prefix --print-value-only | jq 'select(.status.phase == "ready")'
```

### Scripting with etcdctl

```bash
#!/bin/bash
# Script to monitor worker count

while true; do
    COUNT=$(etcdctl get /lab-resource-manager/lab-workers/ --prefix --keys-only | wc -l)
    echo "$(date): Active workers: $COUNT"
    sleep 5
done
```

### Transactions (Atomic Operations)

```bash
# Atomic compare-and-swap
etcdctl txn <<EOF
compare:
  value("/mykey") = "old-value"

success:
  put /mykey "new-value"

failure:
  get /mykey
EOF
```

---

## 📚 Quick Reference Card

| Command                         | Description              |
| ------------------------------- | ------------------------ |
| `etcdctl put <key> <value>`     | Store a key-value pair   |
| `etcdctl get <key>`             | Retrieve a value         |
| `etcdctl get <prefix> --prefix` | Get all keys with prefix |
| `etcdctl del <key>`             | Delete a key             |
| `etcdctl watch <key>`           | Watch for changes        |
| `etcdctl endpoint health`       | Check etcd health        |
| `etcdctl endpoint status`       | Show cluster status      |
| `etcdctl compact <rev>`         | Compact old revisions    |
| `etcdctl defrag`                | Defragment database      |
| `etcdctl snapshot save <file>`  | Create backup            |

---

## 🔗 Additional Resources

- **Official etcd Documentation**: https://etcd.io/docs/
- **etcdctl Command Reference**: https://etcd.io/docs/latest/dev-guide/interacting_v3/
- **etcd Playground**: https://play.etcd.io/
- **Lab Resource Manager Implementation**: See `samples/lab_resource_manager/ETCD_IMPLEMENTATION.md`

---

## 🎓 Learning Path

1. **Start Here**: Install `etcdctl` and connect to Docker
2. **Basic Operations**: Practice PUT, GET, DELETE commands
3. **Watch API**: Experiment with real-time watching
4. **Lab Resource Manager**: Explore how the app uses etcd
5. **Advanced**: Learn about transactions, leases, and clustering

---

## ⚙️ Environment Variables Reference

```bash
# API version (always use v3)
export ETCDCTL_API=3

# Endpoint configuration
export ETCDCTL_ENDPOINTS=http://localhost:2479

# Authentication (if enabled)
export ETCDCTL_USER=root:password

# TLS configuration (for production)
export ETCDCTL_CACERT=/path/to/ca.crt
export ETCDCTL_CERT=/path/to/client.crt
export ETCDCTL_KEY=/path/to/client.key
```

---

**Happy etcd-ing! 🚀**
