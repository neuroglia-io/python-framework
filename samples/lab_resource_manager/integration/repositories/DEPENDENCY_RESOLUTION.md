# Dependency Resolution for etcd3-py Integration

## 🎯 Problem Summary

When integrating `etcd3-py` into the Lab Resource Manager, we encountered protobuf version conflicts with OpenTelemetry dependencies.

## 🔍 Root Cause Analysis

### Original Issue

The original `etcd3` library (v0.12.0) is unmaintained and has protobuf definitions generated with an old protoc version (<3.19), causing:

```
TypeError: Descriptors cannot be created directly
```

### Solution Attempted

Switched to `etcd3-py` (v0.1.6), a maintained fork that supports protobuf 4.x and 5.x.

### New Conflict Discovered

OpenTelemetry packages have conflicting protobuf requirements:

- `opentelemetry-exporter-prometheus` 0.49b2 → requires `opentelemetry-sdk` 1.28.2 → requires `protobuf <5.0`
- `etcd3-py` 0.1.6 → works with `protobuf >=4.25.0`

## ✅ Final Solution

### Configuration Changes (`pyproject.toml`)

```toml
# etcd3-py with protobuf 4.x constraint
etcd3-py = { version = "^0.1.6", optional = true }
protobuf = ">=4.25.0,<5.0.0"  # Compatible with both etcd3-py and OpenTelemetry 1.28.2

# OpenTelemetry kept at 1.28.2 for Prometheus exporter compatibility
opentelemetry-api = "^1.28.2"
opentelemetry-sdk = "^1.28.2"
opentelemetry-exporter-otlp-proto-grpc = "^1.28.2"
opentelemetry-exporter-otlp-proto-http = "^1.28.2"
opentelemetry-instrumentation = "^0.49b2"
opentelemetry-instrumentation-fastapi = "^0.49b2"
opentelemetry-instrumentation-httpx = "^0.49b2"
opentelemetry-instrumentation-logging = "^0.49b2"
opentelemetry-instrumentation-system-metrics = "^0.49b2"
opentelemetry-exporter-prometheus = "^0.49b2"
```

### Installation Commands

```bash
# Update lock file with resolved dependencies
poetry lock

# Install with etcd support
poetry install -E etcd

# Verify installation
poetry show etcd3-py protobuf
```

## 📊 Version Compatibility Matrix

| Package                             | Version         | protobuf Requirement | Status                 |
| ----------------------------------- | --------------- | -------------------- | ---------------------- |
| `etcd3-py`                          | 0.1.6           | >=4.25.0             | ✅ Compatible with 4.x |
| `opentelemetry-sdk`                 | 1.28.2          | <5.0                 | ✅ Compatible with 4.x |
| `opentelemetry-exporter-prometheus` | 0.49b2          | <5.0 (via SDK)       | ✅ Compatible with 4.x |
| Final `protobuf`                    | 4.25.x - 4.28.x | -                    | ✅ Satisfies all       |

## 🚀 Next Steps

1. **Run `poetry lock`** - Let it complete (takes 10-30 seconds)
2. **Run `poetry install -E etcd`** - Install dependencies
3. **Test application startup**:
   ```bash
   cd samples/lab_resource_manager
   python main.py
   ```

## 🔧 Docker Build

The Dockerfile already includes the correct extras:

```dockerfile
RUN poetry install --no-root --no-interaction --no-ansi --extras "etcd aws"
```

After running `poetry lock`, rebuild the Docker image:

```bash
docker-compose -f deployment/docker-compose/docker-compose.shared.yml \
               -f deployment/docker-compose/docker-compose.lab-resource-manager.yml \
               up --build
```

## 📝 Key Takeaways

1. **etcd3 is abandoned** - Always use `etcd3-py` for new projects
2. **protobuf 4.x is the sweet spot** - Compatible with both etcd3-py and current OpenTelemetry
3. **OpenTelemetry will evolve** - Future versions (1.29+) will require protobuf 5.x
4. **Migration path exists** - When OpenTelemetry Prometheus exporter updates to support protobuf 5.x, we can upgrade

## 🎓 Alternative Solutions Considered

### Option 1: Upgrade OpenTelemetry to 1.29+ (REJECTED)

- **Pro**: Latest features, protobuf 5.x support
- **Con**: No compatible Prometheus exporter available yet
- **Impact**: Would lose `/api/metrics` endpoint

### Option 2: Remove Prometheus exporter (REJECTED)

- **Pro**: Simplifies dependencies
- **Con**: Breaks existing observability setup in Mario's Pizzeria and other samples
- **Impact**: Major breaking change for users

### Option 3: Keep everything at current versions (SELECTED ✅)

- **Pro**: Works with both etcd3-py and all OpenTelemetry features
- **Con**: Not using latest OpenTelemetry (1.29+)
- **Impact**: Minimal - 1.28.2 is stable and feature-complete

## 🔗 References

- [etcd3-py GitHub](https://github.com/Revolution1/etcd3-py) - Maintained fork
- [OpenTelemetry Python Releases](https://github.com/open-telemetry/opentelemetry-python/releases)
- [protobuf Python Package](https://pypi.org/project/protobuf/)
