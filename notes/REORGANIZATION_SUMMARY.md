# Docker Compose & Sample Management Reorganization Summary

## Overview

This document summarizes the comprehensive reorganization of the Docker Compose infrastructure and sample application management for the Neuroglia Python framework. The changes improve portability, maintainability, and concurrent execution of sample applications.

## Key Changes

### 1. Docker Compose File Reorganization

**Previous Structure:**

```
├── docker-compose.shared.yml
├── docker-compose.mario.yml
└── docker-compose.simple-ui.yml
```

**New Structure:**

```
deployment/
├── docker-compose/
│   ├── docker-compose.shared.yml
│   ├── docker-compose.mario.yml
│   └── docker-compose.simple-ui.yml
└── keycloak/
    ├── mario-pizzeria-realm-export.json
    └── pyneuro-realm-export.json (NEW - unified realm)
```

**Rationale:** Centralized deployment artifacts alongside infrastructure configuration (Keycloak, OTEL, MongoDB, etc.)

### 2. Unified Keycloak Realm

**Previous:** Separate realms for each sample application

- `mario-pizzeria` realm for Mario's Pizzeria
- No realm for Simple UI (planned separate realm)

**New:** Single unified `pyneuro` realm for all sample applications

- Realm: `pyneuro`
- Clients:
  - `pyneuro-app` (confidential) - Backend applications
  - `pyneuro-public-app` (public) - Frontend/SPA applications
- Roles: `admin`, `manager`, `chef`, `driver`, `user`, `customer`
- Demo Users:
  - admin/test (admin role)
  - manager/test (manager role)
  - chef/test (chef role)
  - driver/test (driver role)
  - customer/test (customer role)
  - user/test (user role)
- Redirect URIs: `localhost:8080/*`, `localhost:8082/*`, `localhost:8085/*`

**Benefits:**

- Single sign-on across all sample applications
- Consistent authentication/authorization
- Simplified configuration
- Easier testing and development

### 3. Environment Variable Configuration

**New `.env` File Structure:**

```env
# Sample Application Ports
MARIO_PORT=8080
MARIO_DEBUG_PORT=5678
SIMPLE_UI_PORT=8082
SIMPLE_UI_DEBUG_PORT=5679

# Shared Infrastructure Ports
MONGODB_PORT=27017
MONGODB_EXPRESS_PORT=8081
KEYCLOAK_PORT=8090
EVENT_PLAYER_PORT=8085
GRAFANA_PORT=3001
PROMETHEUS_PORT=9090
OTEL_GRPC_PORT=4317
OTEL_HTTP_PORT=4318
TEMPO_PORT=3200
LOKI_PORT=3100

# Database Credentials
MONGODB_USER=root
MONGODB_PASSWORD=neuroglia123

# Keycloak Configuration
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KEYCLOAK_REALM=pyneuro
KEYCLOAK_IMPORT_FILE=/opt/keycloak/data/import/pyneuro-realm-export.json

# Docker Configuration
DOCKER_NETWORK_NAME=pyneuro-net

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

**Benefits:**

- Flexible port configuration for avoiding conflicts
- Easy customization for different environments
- Concurrent sample execution without port conflicts
- Centralized configuration management

### 4. Cross-Platform Python Management Scripts

**Previous:** Bash scripts (`mario-pizzeria.sh`, `simple-ui.sh`)

- Platform-specific (Unix/Linux only)
- Limited Windows support
- Shell-specific syntax issues

**New:** Python scripts with portable shell wrappers

- **Python scripts**: `src/cli/mario-pizzeria.py`, `src/cli/simple-ui.py`
- **Shell wrappers**: `mario-pizzeria`, `simple-ui` (in project root)
- **Installation script**: `scripts/setup/install_sample_tools.sh`
- **System-wide access**: Tools installed to `~/.local/bin/`
- Cross-platform (Windows, macOS, Linux)
- Consistent interface across samples
- Better error handling
- Type-safe argument parsing

**Script Features:**

```bash
# Install tools (one-time setup)
./scripts/setup/install_sample_tools.sh

# Common commands available for both tools:
mario-pizzeria start      # Start with shared infrastructure
mario-pizzeria stop       # Stop sample (keep infra running)
mario-pizzeria restart    # Restart sample application
mario-pizzeria status     # Check service status
mario-pizzeria logs       # View logs (with follow)
mario-pizzeria clean      # Stop and remove volumes
mario-pizzeria build      # Rebuild Docker images
mario-pizzeria reset      # Complete reset (clean + start)

# Simple UI uses same commands:
simple-ui start
simple-ui stop
simple-ui restart
simple-ui status
simple-ui logs
simple-ui clean
simple-ui build
simple-ui reset

# Tools work from anywhere after installation!
cd ~/my-project
mario-pizzeria status    # Works!
```

### 5. CLI Tools Organization & Installation

**New Directory Structure:**

```
src/
└── cli/
    ├── mario-pizzeria.py     # Python implementation
    ├── simple-ui.py          # Python implementation
    └── pyneuroctl.py         # Framework CLI tool

Root directory:
├── mario-pizzeria            # Portable shell wrapper
├── simple-ui                 # Portable shell wrapper
├── pyneuroctl                # Portable shell wrapper
└── scripts/
    └── setup/
        └── install_sample_tools.sh  # Installation script
```

**Shell Wrapper Features:**

- **Portable:** Works on Windows (Git Bash/WSL), macOS, Linux
- **Python Detection:** Automatically finds Python (venv, Poetry, or system)
- **Path Resolution:** Handles symlinks and relative paths
- **Error Handling:** Clear error messages for missing dependencies
- **Consistent Interface:** Same pattern across all CLI tools

**Installation Script (`install_sample_tools.sh`):**

- Creates symlinks in `~/.local/bin/` for system-wide access
- Adds `~/.local/bin/` to PATH if not already present
- Updates shell configuration (`.bashrc`, `.zshrc`, `.bash_profile`)
- Tests all installations automatically
- Provides usage examples and verification commands
- Works from any directory after installation

**Benefits:**

- **Developer Experience:** Tools work from anywhere after installation
- **Consistency:** Same commands regardless of shell or OS
- **Maintainability:** Python logic separate from shell wrappers
- **Extensibility:** Easy to add new CLI tools following the same pattern

### 6. Updated Makefile Commands

**All Makefile commands now delegate to shell wrappers:**

```makefile
# Shared Infrastructure (still uses docker-compose directly)
make infra-start    # Start shared services
make infra-stop     # Stop shared services
make infra-status   # Check status
make infra-logs     # View logs

# Mario's Pizzeria - Delegates to ./mario-pizzeria wrapper
make mario-start    # Calls: ./mario-pizzeria start
make mario-stop     # Calls: ./mario-pizzeria stop
make mario-restart  # Calls: ./mario-pizzeria restart
make mario-status   # Calls: ./mario-pizzeria status
make mario-logs     # Calls: ./mario-pizzeria logs
make mario-clean    # Calls: ./mario-pizzeria clean
make mario-build    # Calls: ./mario-pizzeria build
make mario-reset    # Calls: ./mario-pizzeria reset

# Simple UI - Delegates to ./simple-ui wrapper
make simple-ui-start    # Calls: ./simple-ui start
make simple-ui-stop     # Calls: ./simple-ui stop
make simple-ui-restart  # Calls: ./simple-ui restart
make simple-ui-status   # Calls: ./simple-ui status
make simple-ui-logs     # Calls: ./simple-ui logs
make simple-ui-clean    # Calls: ./simple-ui clean
make simple-ui-build    # Calls: ./simple-ui build
make simple-ui-reset    # Calls: ./simple-ui reset

# Convenience Commands
make all-samples-start  # Start all samples
make all-samples-stop   # Stop all samples
make all-samples-clean  # Clean all samples
```

## Docker Compose Architecture

### Shared Infrastructure (`docker-compose.shared.yml`)

**Services:**

- **MongoDB** (port 27017) - Shared database
- **MongoDB Express** (port 8081) - Database UI
- **Keycloak** (port 8090) - Authentication/Authorization
- **Event Player** (port 8085) - Event visualization (Mario-specific, but shared)
- **OTEL Collector** (ports 4317, 4318) - Telemetry collection
- **Grafana** (port 3001) - Observability dashboards
- **Tempo** (port 3200) - Distributed tracing
- **Prometheus** (port 9090) - Metrics collection
- **Loki** (port 3100) - Log aggregation

**Network:** `pyneuro-net` (external, created once)

### Sample-Specific Compose Files

**Mario's Pizzeria (`docker-compose.mario.yml`):**

- UI Builder (Parcel watch mode)
- Mario Pizzeria App (port ${MARIO_PORT:-8080})
- Debug port ${MARIO_DEBUG_PORT:-5678}

**Simple UI (`docker-compose.simple-ui.yml`):**

- UI Builder (Parcel watch mode)
- Simple UI App (port ${SIMPLE_UI_PORT:-8082})
- Debug port ${SIMPLE_UI_DEBUG_PORT:-5679}

## Usage Examples

### Installation (One-Time Setup)

```bash
# Install CLI tools to your PATH
./scripts/setup/install_sample_tools.sh

# Verify installation
mario-pizzeria --help
simple-ui --help
pyneuroctl --help
```

### Starting Everything for the First Time

**Using CLI Tools (Recommended):**

```bash
# 1. Start shared infrastructure (auto-creates network)
make infra-start

# 2. Start Mario's Pizzeria
mario-pizzeria start

# 3. Start Simple UI (concurrent with Mario)
simple-ui start
```

**Using Makefile:**

```bash
# 1. Start shared infrastructure
make infra-start

# 2. Start Mario's Pizzeria
make mario-start

# 3. Start Simple UI (concurrent with Mario)
make simple-ui-start
```

### Access Points

**Access Points:**

- Application: http://localhost:8080
- API Docs: http://localhost:8080/api/docs
- Debug: Port 5678
- CLI: `mario-pizzeria {start|stop|restart|status|logs|clean|build|reset}`
- Makefile: `make {mario-start|mario-stop|mario-restart|mario-status|mario-logs|mario-clean|mario-build|mario-reset}`

**Simple UI:**

- Application: http://localhost:8082
- Debug: Port 5679
- CLI: `simple-ui {start|stop|restart|status|logs|clean|build|reset}`
- Makefile: `make {simple-ui-start|simple-ui-stop|simple-ui-restart|simple-ui-status|simple-ui-logs|simple-ui-clean|simple-ui-build|simple-ui-reset}`

**Shared Services:**

- Keycloak: http://localhost:8090 (admin/admin)
- MongoDB Express: http://localhost:8081
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090
- Event Player: http://localhost:8085

### Authentication

**All samples use the same Keycloak realm (`pyneuro`):**

Demo Users (all with password "test"):

- admin/test - Full admin access
- manager/test - Management role
- chef/test - Chef operations (Mario-specific)
- driver/test - Delivery driver (Mario-specific)
- customer/test - Customer role
- user/test - Standard user

### Concurrent Execution

Both samples can run simultaneously without conflicts:

```bash
# Start both samples
make all-samples-start

# Check status of both
make mario-status
make simple-ui-status

# View logs from both
make mario-logs &
make simple-ui-logs &

# Stop both samples (infrastructure keeps running)
make all-samples-stop

# Or stop everything including infrastructure
make mario-clean
make simple-ui-clean
make infra-clean
```

### Customizing Ports

Edit `.env` file to change ports:

```env
# Change Mario's port to 8090
MARIO_PORT=8090

# Change Simple UI port to 8092
SIMPLE_UI_PORT=8092

# Change Keycloak port to 9090
KEYCLOAK_PORT=9090
```

Then restart services:

```bash
make mario-stop
make mario-start
```

## Migration Guide

### For Existing Users

If you have existing Docker containers running:

```bash
# 1. Stop old containers
docker-compose -f docker-compose.shared.yml down
docker-compose -f docker-compose.mario.yml down
docker-compose -f docker-compose.simple-ui.yml down

# 2. Remove old volumes (optional - will lose data)
docker-compose -f docker-compose.shared.yml down -v
docker-compose -f docker-compose.mario.yml down -v
docker-compose -f docker-compose.simple-ui.yml down -v

# 3. Use new commands
make infra-start
make mario-start
make simple-ui-start
```

### For Developers

**Update your workflow to use CLI tools:**

1. **One-time installation:**

   ```bash
   ./scripts/setup/install_sample_tools.sh
   ```

2. **Use CLI tools (recommended):**

   ```bash
   mario-pizzeria start
   simple-ui start
   ```

3. **Or use Makefile (alternative):**
   ```bash
   make mario-start
   make simple-ui-start
   ```

**Update application code:**

```python
# Update Keycloak configuration to use unified realm
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "pyneuro")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "pyneuro-app")
```

**Key Changes:**

- **File locations:** `deployment/docker-compose/`
- **Python scripts:** `src/cli/mario-pizzeria.py`, `src/cli/simple-ui.py`
- **Shell wrappers:** `mario-pizzeria`, `simple-ui` (in project root)
- **Unified realm:** `pyneuro` (replaced `mario-pizzeria` realm)
- **Environment config:** All configuration in `.env` file
- **CLI access:** System-wide after running `install_sample_tools.sh`

## Benefits Summary

### 1. **Portability**

- Python scripts work on Windows, macOS, and Linux
- No shell-specific syntax issues
- Consistent developer experience across platforms

### 2. **Maintainability**

- Centralized configuration in `.env` file
- Shared infrastructure reduces duplication
- Unified authentication simplifies testing

### 3. **Concurrent Execution**

- Multiple samples can run simultaneously
- Configurable ports avoid conflicts
- Shared infrastructure reduces resource usage
- CLI tools allow independent sample management

### 4. **Developer Experience**

- **Simple, intuitive commands:** `mario-pizzeria start` vs `python3 mario-pizzeria.py start`
- **System-wide access:** Tools work from any directory after installation
- **Consistent interface:** Same commands across all samples
- **Better error messages:** Clear feedback from Python implementation
- **Automatic dependency management:** Shared infra starts automatically
- **Cross-platform:** Works on Windows, macOS, and Linux

### 5. **Production Readiness**

- Environment-based configuration
- Proper secrets management via `.env`
- OpenTelemetry observability
- Centralized authentication

## Testing Checklist

Use this checklist to verify the reorganization:

- [ ] Create network: `docker network create pyneuro-net`
- [ ] Start infrastructure: `make infra-start`
- [ ] Verify MongoDB Express: http://localhost:8081
- [ ] Verify Keycloak: http://localhost:8090 (admin/admin)
- [ ] Import pyneuro realm (should be automatic)
- [ ] Start Mario: `make mario-start`
- [ ] Access Mario: http://localhost:8080
- [ ] Login to Mario with admin/test
- [ ] Start Simple UI: `make simple-ui-start`
- [ ] Access Simple UI: http://localhost:8082
- [ ] Login to Simple UI with admin/test
- [ ] Verify concurrent execution (both apps running)
- [ ] Check Grafana dashboards: http://localhost:3001
- [ ] View logs: `make mario-logs` and `make simple-ui-logs`
- [ ] Stop samples: `make all-samples-stop`
- [ ] Verify infrastructure still running: `make infra-status`
- [ ] Clean everything: `make all-samples-clean` and `make infra-clean`

## Troubleshooting

### Port Conflicts

**Problem:** Port already in use
**Solution:** Edit `.env` file to change ports:

```env
MARIO_PORT=8090  # Changed from 8080
SIMPLE_UI_PORT=8092  # Changed from 8082
```

### Network Not Found

**Problem:** `ERROR: Network pyneuro-net declared as external, but could not be found`
**Solution:** Create the network manually:

```bash
docker network create pyneuro-net
```

### Keycloak Realm Not Imported

**Problem:** Keycloak realm not imported automatically
**Solution:** Import manually via Keycloak Admin UI or restart Keycloak:

```bash
make infra-stop
make infra-start
```

### MongoDB Connection Failed

**Problem:** Cannot connect to MongoDB
**Solution:** Check MongoDB is running and credentials are correct:

```bash
make infra-status
# Check MongoDB container
docker logs mongodb
```

### Python Script Not Found

**Problem:** `python3: command not found`
**Solution:** Ensure Python 3 is installed:

```bash
# macOS/Linux
which python3

# Windows
where python

# Or use python instead of python3
python mario-pizzeria.py start
```

## Future Enhancements

Potential improvements for future versions:

1. **Health Checks:** Add health check endpoints to management scripts
2. **Dependency Validation:** Validate required services before starting samples
3. **Backup/Restore:** Add commands for backing up and restoring MongoDB data
4. **Environment Validation:** Validate `.env` file values before starting
5. **Docker Compose Override:** Support `docker-compose.override.yml` for local customization
6. **Automated Tests:** Integration tests for sample startup/shutdown
7. **Documentation Generator:** Auto-generate sample documentation from code
8. **Resource Monitoring:** Add resource usage monitoring to management scripts

## Related Documentation

- [Docker Compose Architecture](./DOCKER_COMPOSE_ARCHITECTURE.md)
- [Mario's Pizzeria Tutorial](./docs/guides/mario-pizzeria-tutorial.md)
- [Simple UI Guide](./docs/guides/simple-ui-guide.md)
- [Keycloak Configuration](./deployment/keycloak/README.md)
- [Local Development Guide](./docs/guides/local-development.md)

## Conclusion

This reorganization provides a solid foundation for running multiple sample applications concurrently with shared infrastructure. The use of Python management scripts ensures cross-platform compatibility, while the unified Keycloak realm simplifies authentication across all samples. Environment variable configuration enables flexible deployment scenarios and easy customization.
