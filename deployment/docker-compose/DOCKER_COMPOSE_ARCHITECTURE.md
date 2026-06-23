# Docker Compose Architecture for Neuroglia Samples

This document describes the **shared infrastructure** approach for running multiple Neuroglia sample applications concurrently with common services.

## 🏗️ Architecture Overview

The Docker Compose setup is organized into multiple files located in `deployment/docker-compose/`:

```
deployment/
└── docker-compose/
    ├── docker-compose.shared.yml      # Shared infrastructure (MongoDB, Keycloak, Observability)
    ├── docker-compose.mario.yml       # Mario's Pizzeria sample application
    └── docker-compose.simple-ui.yml   # Simple UI sample application
```

### Key Benefits

1. **Resource Efficiency**: Infrastructure services (MongoDB, Grafana, Prometheus, etc.) run once
2. **Concurrent Execution**: Multiple samples can run simultaneously
3. **Shared Networking**: All services communicate via `pyneuro-net` network
4. **Independent Scaling**: Start/stop individual samples without affecting others
5. **Environment Configuration**: Flexible port mappings and settings via `.env` file
6. **Cross-Platform Management**: Python scripts work on Windows, macOS, and Linux

## 🎯 Quick Start

### Installation (One-Time Setup)

Install the sample management CLI tools to your system PATH:

```bash
# Install mario-pizzeria, simple-ui, and pyneuroctl commands
./scripts/setup/install_sample_tools.sh

# Tools are now available system-wide:
mario-pizzeria --help
simple-ui --help
pyneuroctl --help
```

### Using CLI Tools (Recommended)

Once installed, you can use the CLI tools from anywhere:

```bash
# Start shared infrastructure
make infra-start
# Or: cd /path/to/pyneuro && make infra-start

# Start Mario's Pizzeria
mario-pizzeria start

# Start Simple UI (concurrent with Mario)
simple-ui start

# Check status
mario-pizzeria status
simple-ui status

# View logs
mario-pizzeria logs
simple-ui logs

# Stop services
mario-pizzeria stop
simple-ui stop
```

### Using Makefile Commands

From the project directory:

```bash
# Shared infrastructure
make infra-start     # Start all shared services
make infra-stop      # Stop shared services
make infra-status    # Check status
make infra-logs      # View logs
make infra-clean     # Stop and remove volumes

# Mario's Pizzeria
make mario-start     # Start Mario with shared infra
make mario-stop      # Stop Mario only
make mario-logs      # View Mario logs
make mario-clean     # Stop and remove Mario volumes

# Simple UI
make simple-ui-start # Start Simple UI with shared infra
make simple-ui-stop  # Stop Simple UI only
make simple-ui-logs  # View Simple UI logs
make simple-ui-clean # Stop and remove Simple UI volumes

# Multi-sample commands
make all-samples-start  # Start both Mario and Simple UI
make all-samples-stop   # Stop both samples (keep infra running)
make all-samples-clean  # Clean both samples
```

## 🌐 Shared Network

All services use the **`pyneuro-net`** bridge network for inter-service communication.

```yaml
networks:
  pyneuro-net:
    driver: bridge
    name: pyneuro-net
```

## 🔧 Shared Infrastructure Services

The `docker-compose.shared.yml` file provides:

| Service                     | Port       | Description                            |
| --------------------------- | ---------- | -------------------------------------- |
| **MongoDB**                 | 27017      | Shared database server for all samples |
| **MongoDB Express**         | 8081       | Database admin UI                      |
| **Keycloak**                | 8090       | SSO/OAuth2 authentication server       |
| **OpenTelemetry Collector** | 4317, 4318 | Telemetry data collection              |
| **Grafana**                 | 3001       | Unified observability dashboard        |
| **Prometheus**              | 9090       | Metrics storage and queries            |
| **Tempo**                   | 3200       | Distributed tracing backend            |
| **Loki**                    | 3100       | Log aggregation                        |

### Database Credentials

**MongoDB:**

- Username: `root`
- Password: `neuroglia123`
- Connection String: `mongodb://root:neuroglia123@mongodb:27017/?authSource=admin`

**Keycloak:**

- Admin Username: `admin`
- Admin Password: `admin`
- URL: `http://localhost:8090`

## 🍕 Sample Applications

### Mario's Pizzeria

- **Port**: 8080
- **Debug Port**: 5678
- **Features**: Full CQRS, Event Sourcing, Keycloak SSO
- **File**: `docker-compose.mario.yml`

### Simple UI

- **Port**: 8082
- **Debug Port**: 5679
- **Features**: JWT Auth, RBAC, Bootstrap SPA
- **File**: `docker-compose.simple-ui.yml`

## 🚀 Quick Start

### Installation

Install the CLI tools for easy sample management:

```bash
# One-time installation
./scripts/setup/install_sample_tools.sh

# Verify installation
mario-pizzeria --help
simple-ui --help
```

### Start Shared Infrastructure Only

```bash
make infra-start
```

### Start a Specific Sample

**Mario's Pizzeria:**

```bash
mario-pizzeria start
# Or: make mario-start
```

**Simple UI:**

```bash
simple-ui start
# Or: make simple-ui-start
```

### Start All Samples

```bash
make all-samples-start
```

This starts:

1. Shared infrastructure
2. Mario's Pizzeria on port 8080
3. Simple UI on port 8082

## 🔄 Common Workflows

### Running Multiple Samples Concurrently

```bash
# Install CLI tools (one-time setup)
./scripts/setup/install_sample_tools.sh

# Start shared infrastructure
make infra-start

# Start Mario's Pizzeria
mario-pizzeria start

# Start Simple UI (runs concurrently!)
simple-ui start

# Both samples now running:
# - Mario: http://localhost:8080
# - Simple UI: http://localhost:8082
# - Shared Grafana: http://localhost:3001
```

### Stop a Sample (Keep Infrastructure)

```bash
# Stop Mario's Pizzeria
mario-pizzeria stop
# Or: make mario-stop

# Simple UI continues running with shared infrastructure
```

### Clean Everything

```bash
make all-samples-clean
```

## 📊 Accessing Services

### Shared Services (Always Available)

- **MongoDB Express**: http://localhost:8081
- **Keycloak Admin**: http://localhost:8090 (admin/admin)
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Tempo**: http://localhost:3200
- **Loki**: http://localhost:3100

### Sample Applications

- **Mario's Pizzeria**: http://localhost:8080
  - API Docs: http://localhost:8080/api/docs
  - UI Docs: http://localhost:8080/docs
- **Simple UI**: http://localhost:8082

## 🔍 Monitoring & Observability

All samples automatically send telemetry to the shared observability stack:

1. **Traces** → OpenTelemetry Collector → Tempo → Grafana
2. **Metrics** → OpenTelemetry Collector → Prometheus → Grafana
3. **Logs** → OpenTelemetry Collector → Loki → Grafana

### Viewing Telemetry

1. Open Grafana: http://localhost:3001
2. Navigate to **Explore**
3. Select data source:
   - **Tempo** for traces
   - **Prometheus** for metrics
   - **Loki** for logs

## 🛠️ Makefile Commands

All commands work from the project directory. CLI tools (mario-pizzeria, simple-ui) work from anywhere after installation.

### Shared Infrastructure

```bash
make infra-start      # Start shared infrastructure
make infra-stop       # Stop shared infrastructure
make infra-status     # Check infrastructure status
make infra-logs       # View infrastructure logs
make infra-clean      # Stop and remove volumes
```

### Mario's Pizzeria

```bash
# Using Makefile
make mario-start      # Start Mario's Pizzeria
make mario-stop       # Stop Mario's Pizzeria
make mario-restart    # Restart Mario's Pizzeria
make mario-status     # Check status
make mario-logs       # View logs
make mario-clean      # Clean volumes
make mario-build      # Rebuild image

# Using CLI tool (works from anywhere)
mario-pizzeria start
mario-pizzeria stop
mario-pizzeria restart
mario-pizzeria status
mario-pizzeria logs
mario-pizzeria clean
mario-pizzeria build
mario-pizzeria reset
```

### Simple UI

```bash
# Using Makefile
make simple-ui-start      # Start Simple UI
make simple-ui-stop       # Stop Simple UI
make simple-ui-restart    # Restart Simple UI
make simple-ui-status     # Check status
make simple-ui-logs       # View logs
make simple-ui-clean      # Clean volumes
make simple-ui-build      # Rebuild image

# Using CLI tool (works from anywhere)
simple-ui start
simple-ui stop
simple-ui restart
simple-ui status
simple-ui logs
simple-ui clean
simple-ui build
simple-ui reset
```

### Multi-Sample Commands

```bash
make all-samples-start    # Start all samples
make all-samples-stop     # Stop all samples
make all-samples-clean    # Clean everything
```

## 🐛 Debugging

### Debug Ports

Each sample exposes a debugpy port for remote debugging:

- **Mario's Pizzeria**: 5678
- **Simple UI**: 5679

### VS Code Debug Configuration

```json
{
  "name": "Attach to Mario",
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  },
  "pathMappings": [
    {
      "localRoot": "${workspaceFolder}",
      "remoteRoot": "/app"
    }
  ]
}
```

### Viewing Logs

```bash
# All services
docker-compose -f docker-compose.shared.yml -f docker-compose.mario.yml logs -f

# Specific sample
make mario-logs
make simple-ui-logs

# Infrastructure
make infra-logs
```

## 📦 Volume Management

### Persistent Volumes

The shared infrastructure creates the following volumes:

```
mongodb_data        # MongoDB database files
keycloak_data       # Keycloak configuration
grafana_data        # Grafana dashboards and settings
tempo_data          # Distributed traces
prometheus_data     # Metrics time-series data
loki_data           # Logs storage
```

### Cleaning Volumes

```bash
# Clean infrastructure volumes
make infra-clean

# Clean specific sample volumes
make mario-clean
make simple-ui-clean

# Clean everything
make all-samples-clean
```

## 🔐 Security Notes

**⚠️ This configuration is for development only!**

For production:

1. Change default passwords (MongoDB, Keycloak)
2. Enable HTTPS/TLS
3. Configure proper authentication
4. Use secrets management
5. Implement network segmentation
6. Enable RBAC and audit logging

## 🆕 Adding New Samples

To add a new sample application:

1. **Create `docker-compose.<sample>.yml`:**

```yaml
services:
  <sample>-app:
    image: <sample>-app
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - <port>:<port>
    networks:
      - pyneuro-net
    depends_on:
      - mongodb

networks:
  pyneuro-net:
    external: true
    name: pyneuro-net
```

2. **Add Makefile commands:**

```makefile
<sample>-start: ## Start <sample>
 @docker-compose -f docker-compose.shared.yml -f docker-compose.<sample>.yml up -d

<sample>-stop: ## Stop <sample>
 @docker-compose -f docker-compose.<sample>.yml down
```

3. **Use shared MongoDB connection:**

```python
CONNECTION_STRINGS = {
    "mongo": "mongodb://root:neuroglia123@mongodb:27017/?authSource=admin"
}
```

## 📚 Related Documentation

- [Mario's Pizzeria README](./samples/mario-pizzeria/README.md)
- [Simple UI README](./samples/simple-ui/README.md)
- [Neuroglia Framework Docs](./docs/index.md)

## 🤝 Contributing

When adding new samples, please:

1. Use the shared `pyneuro-net` network
2. Connect to shared MongoDB instance
3. Send telemetry to shared OTEL collector
4. Document unique ports used
5. Add Makefile commands
6. Update this README

---

**Built with ❤️ using the Neuroglia Python Framework**
