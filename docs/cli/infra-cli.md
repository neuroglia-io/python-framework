# Shared Infrastructure CLI Tool

The `infra` CLI tool provides a consistent, portable way to manage the shared infrastructure services used by all Neuroglia sample applications.

## Overview

The shared infrastructure includes:

- **🗄️ MongoDB** - NoSQL database (port 27017)
- **📊 MongoDB Express** - Database web UI (port 8081)
- **🔐 Keycloak** - Identity & Access Management (port 8090)
- **📈 Prometheus** - Metrics collection (port 9090)
- **📊 Grafana** - Observability dashboards (port 3001)
- **📝 Loki** - Log aggregation (port 3100)
- **🔍 Tempo** - Distributed tracing (port 3200)
- **🔌 OpenTelemetry Collector** - Telemetry pipeline (port 4317)
- **🎬 Event Player** - Event testing tool (port 8085)

## Usage

### Direct CLI Usage

```bash
# Start all infrastructure services
./infra start

# Check status
./infra status

# View logs (all services)
./infra logs

# View logs (specific service)
./infra logs mongodb

# Health check
./infra health

# Stop infrastructure
./infra stop

# Clean (removes all data)
./infra clean

# Complete reset
./infra reset
```

### Using Python Directly

```bash
python src/cli/infra.py start
python src/cli/infra.py status
```

### Using Make

```bash
make infra-start
make infra-status
make infra-logs
make infra-health
make infra-stop
make infra-clean
```

## Commands

### Basic Operations

- **`start`** - Start all shared infrastructure services
  - Automatically removes orphaned containers
  - Creates Docker network if needed
  - Shows all service access points after startup
- **`stop`** - Stop all infrastructure services
  - Preserves volumes (data is kept)
  - Safe to run, can restart later
- **`restart [service]`** - Restart all or specific service
  - Can target individual services like `mongodb`, `grafana`
  - Restarts all if no service specified
  - **Note**: Does NOT reload environment variables!
- **`recreate [service]`** - Recreate service(s) with fresh containers

  - Forces Docker to create new containers (picks up env var changes)
  - Can target specific service or recreate all
  - Options:
    - `--delete-volumes`: Also delete and recreate volumes (⚠️ data loss!)
    - `--no-remove-orphans`: Don't remove orphan containers
    - `-y, --yes`: Skip confirmation prompts
  - Use this when:
    - Environment variables changed in docker-compose.yml
    - Configuration needs to be reloaded
    - Service behaves incorrectly after config changes
  - Examples:

    ```bash
    # Recreate Keycloak (preserve data)
    ./infra recreate keycloak

    # Recreate Keycloak with fresh data volumes
    ./infra recreate keycloak --delete-volumes

    # Recreate all services with fresh volumes (no confirmation)
    ./infra recreate --delete-volumes -y
    ```

### Monitoring & Debugging

- **`status`** - Show running services
  - Lists all containers with their status
- **`logs [service]`** - View logs

  - Follow logs in real-time by default
  - Use `--tail N` to limit lines
  - Use `--no-follow` to exit immediately
  - Examples:

    ```bash
    ./infra logs mongodb --tail 50
    ./infra logs grafana --no-follow
    ```

- **`ps`** - List all infrastructure containers
  - Shows detailed container information
- **`health`** - Comprehensive health check
  - Shows status of all services
  - Indicates healthy/unhealthy states
  - Color-coded output

### Maintenance

- **`build`** - Rebuild Docker images
  - Rarely needed, infrastructure uses standard images
- **`clean`** - Remove all data and volumes
  - ⚠️ **WARNING**: This destroys all database data, configurations, etc.
  - Asks for confirmation unless `--yes` flag is used
  - Example: `./infra clean --yes`
- **`reset`** - Complete reset
  - Runs `clean` then `start`
  - Useful for starting fresh

## Options

- **`--no-follow`** - Don't follow logs (exit immediately)
- **`--tail N`** - Show last N log lines (default: 100)
- **`--yes`, `-y`** - Skip confirmation prompts
- **`--no-remove-orphans`** - Don't remove orphaned containers on start

## Examples

### Starting Infrastructure for Development

```bash
# Start everything
./infra start

# Check that all services are healthy
./infra health

# View specific service logs if needed
./infra logs mongodb --tail 100
```

### Debugging a Service

```bash
# Check overall status
./infra status

# View real-time logs for problematic service
./infra logs keycloak

# Restart the service
./infra restart keycloak
```

### Cleaning Up for Fresh Start

```bash
# Stop and remove all data
./infra clean

# Or use reset for clean + start
./infra reset
```

### Monitoring Multiple Services

```bash
# View all logs together
./infra logs

# Or check health status
./infra health
```

## Service-Specific Access

After starting infrastructure, access services at:

- **Grafana Dashboards**: http://localhost:3001 (admin/admin)
- **Keycloak Admin**: http://localhost:8090 (admin/admin)
- **MongoDB Express**: http://localhost:8081
- **Event Player**: http://localhost:8085
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100
- **Tempo**: http://localhost:3200

## Integration with Sample Apps

All sample applications (Mario's Pizzeria, OpenBank, Simple UI) depend on this shared infrastructure:

```bash
# Start infrastructure first
./infra start

# Then start your sample app
./mario-pizzeria start
./openbank start
./simple-ui start
```

## Troubleshooting

### Orphaned Containers Warning

If you see warnings about orphaned containers:

```bash
# The CLI automatically handles this on start
./infra start

# Or manually remove them first
docker stop pyneuro-old-container-1
docker rm pyneuro-old-container-1
```

### Port Conflicts

If services fail to start due to port conflicts:

```bash
# Check what's using the port
lsof -i :27017  # MongoDB
lsof -i :3001   # Grafana
lsof -i :8090   # Keycloak

# Stop conflicting services or change ports in docker-compose.shared.yml
```

### Services Not Healthy

```bash
# Check health status
./infra health

# View logs for failing service
./infra logs <service-name>

# Try restarting the service
./infra restart <service-name>

# Last resort: reset everything
./infra reset
```

## Architecture

The CLI tool wraps Docker Compose operations for `docker-compose.shared.yml`:

```
infra CLI
    ↓
src/cli/infra.py (Python)
    ↓
docker-compose -f deployment/docker-compose/docker-compose.shared.yml
    ↓
Docker containers for shared services
```

## Development

The CLI is built following the same pattern as other sample CLIs:

- **Python CLI**: `src/cli/infra.py` - Core logic
- **Shell Wrapper**: `infra` - Executable wrapper for convenience
- **Makefile Integration**: Targets prefixed with `infra-*`

To modify or extend:

1. Edit `src/cli/infra.py` for new commands
2. Update help text and examples
3. Test with `python src/cli/infra.py <command>`
4. Add corresponding Makefile targets if needed
