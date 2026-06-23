# Docker Compose Port Configuration Fix

## Problem

Multiple Docker Compose stacks cannot run concurrently when they bind to the same host ports.

## Solution

All external ports are now parametrized via environment variables in `.env` file.

## Port Mappings

### Original Ports (Conflicting)

```
OTEL_COLLECTOR_GRPC_PORT=4317      # Conflicted with other stack
OTEL_COLLECTOR_HTTP_PORT=4318      # Conflicted with other stack
OTEL_COLLECTOR_METRICS_PORT=8888   # Conflicted with other stack
OTEL_COLLECTOR_HEALTH_PORT=13133   # Conflicted with other stack
```

### New Ports (Non-conflicting)

```
OTEL_COLLECTOR_GRPC_PORT=4417      # Changed: +100 from original
OTEL_COLLECTOR_HTTP_PORT=4418      # Changed: +100 from original
OTEL_COLLECTOR_METRICS_PORT=8988   # Changed: +100 from original
OTEL_COLLECTOR_HEALTH_PORT=13233   # Changed: +100 from original
```

## How It Works

### Docker Compose Port Mapping

Format: `"${HOST_PORT}:${CONTAINER_PORT}"`

Example:

```yaml
ports:
  - "${OTEL_COLLECTOR_GRPC_PORT:-4317}:4317"
```

This means:

- **Host Port**: `${OTEL_COLLECTOR_GRPC_PORT}` from .env (4417)
- **Container Port**: 4317 (fixed, internal to Docker network)

### Container Communication

Containers within the same Docker network communicate using:

- **Service name**: `otel-collector` (DNS resolution)
- **Internal port**: 4317 (not the host port!)

Example in mario-pizzeria app:

```yaml
environment:
  OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317 # Uses internal port
```

## Network Configuration Fix

Also fixed the network configuration issue where all compose files were declaring:

```yaml
networks:
  pyneuro-net:
    external: true # ❌ Required network to exist
```

Changed to:

```yaml
# Only in docker-compose.shared.yml:
networks:
  pyneuro-net:
    driver: bridge # ✅ Creates network if missing
    name: ${DOCKER_NETWORK_NAME:-pyneuro-net}
# Removed from individual sample compose files (mario, openbank, simple-ui, lab-resource-manager)
```

## Files Modified

1. **`.env`**: Updated OTEL collector external ports
2. **`docker-compose.shared.yml`**: Network configuration (external: false)
3. **`docker-compose.mario.yml`**: Removed duplicate network declaration
4. **`docker-compose.openbank.yml`**: Removed duplicate network declaration
5. **`docker-compose.simple-ui.yml`**: Removed duplicate network declaration
6. **`docker-compose.lab-resource-manager.yml`**: Removed duplicate network declaration

## Customization

To avoid port conflicts with other stacks, edit `.env` and change any conflicting ports:

```bash
# Example: If another stack uses 4417, change to 4517
OTEL_COLLECTOR_GRPC_PORT=4517
OTEL_COLLECTOR_HTTP_PORT=4518
OTEL_COLLECTOR_METRICS_PORT=9088
OTEL_COLLECTOR_HEALTH_PORT=13333
```

## Testing

```bash
# Start Mario's Pizzeria
./mario-pizzeria start

# Verify ports are accessible from host
curl http://localhost:4417  # Should connect to OTEL collector gRPC
curl http://localhost:13233/  # Should return collector health status
```

## Benefits

✅ Multiple Docker Compose stacks can run concurrently
✅ No port conflicts between stacks
✅ Easy port customization via .env file
✅ Container-to-container communication unaffected
✅ No application code changes needed

---

**Date**: November 7, 2025
**Author**: Bruno van de Werve
**Related Issue**: Docker Compose network and port conflicts
