# 📊 Mario's Pizzeria - Observability Architecture Guide

**For Developers New to Telemetry & Observability**

---

## 🎯 What is Observability?

**Observability** is the ability to understand what's happening inside your application by examining its external outputs. Think of it like having X-ray vision into your software - you can see:

- **How fast** things are working (performance)
- **What went wrong** when errors occur (debugging)
- **Where bottlenecks** are happening (optimization)
- **How users** are actually using your app (behavior)

It's like having a dashboard in your car that shows speed, fuel level, engine temperature, and warning lights.

---

## 🏗️ Architecture Overview

Mario's Pizzeria uses **OpenTelemetry** - an industry standard for collecting telemetry data. Here's the complete setup:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Mario's Pizzeria Application                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Main App      │  │    API App      │  │    UI App       │     │
│  │  (FastAPI)      │  │   (FastAPI)     │  │   (FastAPI)     │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│           │                     │                     │             │
│           └─────────────────────┼─────────────────────┘             │
│                                 │                                   │
│                          HTTP Metrics                               │
│                        (/api/metrics)                               │
└─────────────────────────────────┼─────────────────────────────────┘
                                  │
                     ┌────────────┼────────────┐
                     │                         │
            Direct Scraping              OTEL Export
                     │                         │
                     ▼                         ▼
        ┌─────────────────────┐  ┌─────────────────────────┐
        │     Prometheus      │  │   OpenTelemetry         │
        │  (Metrics Storage)  │  │     Collector           │
        │                     │  │   (Data Pipeline)       │
        └─────────────────────┘  └─────────────────────────┘
                     │                         │
                     │            ┌────────────┼────────────┐
                     │            │            │            │
                     │            ▼            ▼            ▼
                     │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                     │  │ Prometheus  │ │   Tempo     │ │    Loki     │
                     │  │ (Metrics)   │ │  (Traces)   │ │   (Logs)    │
                     │  └─────────────┘ └─────────────┘ └─────────────┘
                     │            │            │            │
                     └────────────┼────────────┼────────────┘
                                  │            │
                                  ▼            ▼
                          ┌─────────────────────────┐
                          │       Grafana           │
                          │   (Visualization)       │
                          │                         │
                          │  📊 HTTP Performance    │
                          │  📈 Infrastructure      │
                          │  🔍 Business Metrics    │
                          └─────────────────────────┘
```

---

## 🔄 Data Flow Explained (Step by Step)

### Step 1: Data Generation 🏭

**What happens**: Your FastAPI application automatically generates telemetry data while handling requests.

**Technical details**:

- Every HTTP request creates metrics (response time, status code, endpoint)
- OpenTelemetry FastAPI instrumentation automatically captures this
- No code changes needed - it's automatic once configured

**Real example**: When someone visits `/api/menu/`, the system records:

- Request duration: 45ms
- Status code: 200 (success)
- Endpoint: /api/menu/
- HTTP method: GET

### Step 2: Data Export 📤

**What happens**: The application makes this data available in two ways:

**A) Direct Prometheus Export**

- Creates `/api/metrics` endpoint
- Serves data in Prometheus format (human-readable text)
- Example snippet:

```
http_server_duration_milliseconds_count{method="GET",endpoint="/api/menu/"} 142
http_server_duration_milliseconds_sum{method="GET",endpoint="/api/menu/"} 6420.5
```

**B) OpenTelemetry Pipeline**

- Sends data to OTEL Collector via OTLP protocol
- More advanced processing capabilities
- Can enrich, filter, or transform data

### Step 3: Data Collection 🗂️

**What happens**: Specialized databases store different types of data:

**Prometheus** (Metrics Database):

- Stores time-series metrics (numbers over time)
- Scrapes `/api/metrics` endpoint every 15 seconds
- Perfect for: request rates, response times, error counts

**Tempo** (Tracing Database):

- Stores distributed traces (request journeys)
- Shows how requests flow through different services
- Perfect for: debugging complex workflows

**Loki** (Logging Database):

- Stores application logs with trace correlation
- Links log messages to specific requests
- Perfect for: debugging specific issues

### Step 4: Data Visualization 📊

**What happens**: Grafana creates dashboards from the collected data.

**HTTP Performance Dashboard** shows:

- Request rate: How many requests per second
- Response times: How fast your API responds (p50, p95, p99)
- Error rate: Percentage of failed requests
- Active requests: Current concurrent load
- Per-endpoint breakdown: Which APIs are slowest

---

## 🛠️ Technical Requirements

### Core Dependencies

**Python Packages** (already installed):

```toml
# OpenTelemetry core
opentelemetry-api = "^1.28.2"
opentelemetry-sdk = "^1.28.2"

# Exporters
opentelemetry-exporter-otlp-proto-grpc = "^1.28.2"
opentelemetry-exporter-prometheus = "^0.49b2"

# Auto-instrumentation
opentelemetry-instrumentation-fastapi = "^0.49b2"
opentelemetry-instrumentation-httpx = "^0.49b2"

# Prometheus client
prometheus-client = "^0.21.0"
```

**Docker Services** (via docker-compose.mario.yml):

```yaml
# Application
mario-pizzeria-app:8080      # Your FastAPI app with /api/metrics

# Observability Stack
otel-collector:4317/4318     # OpenTelemetry Collector (OTLP receivers)
prometheus:9090              # Metrics storage and query engine
grafana:3001                 # Dashboard and visualization
tempo:3200                   # Distributed tracing backend
loki:3100                    # Log aggregation system
```

### Network Configuration

**Docker Network**: `mario-pizzeria_mario-net` (bridge)

- All containers on same network for internal communication
- Service discovery via container names (e.g., `mario-pizzeria-app:8080`)
- External access via localhost ports

**Prometheus Scraping Configuration**:

```yaml
# Direct app scraping
- job_name: "mario-pizzeria-app"
  static_configs:
    - targets: ["mario-pizzeria-app:8080"]
  metrics_path: "/api/metrics"

# OTEL collector scraping
- job_name: "mario-pizzeria-metrics"
  static_configs:
    - targets: ["otel-collector:8889"]
```

---

## ⚙️ Configuration Details

### 1. FastAPI Application Setup

**Location**: `samples/mario-pizzeria/main.py`

```python
# Import observability functions
from neuroglia.observability import (
    configure_opentelemetry,
    instrument_fastapi_app,
    add_metrics_endpoint
)

# Initialize OpenTelemetry
configure_opentelemetry(
    service_name="mario-pizzeria",
    service_version="1.0.0"
)

# Instrument all FastAPI apps for HTTP metrics
instrument_fastapi_app(app, "main-app")
instrument_fastapi_app(api_app, "api-app")
instrument_fastapi_app(ui_app, "ui-app")

# Add Prometheus metrics endpoint
add_metrics_endpoint(api_app, "/metrics")
```

### 2. OpenTelemetry Configuration

**Location**: `src/neuroglia/observability/config.py`

**What it does**:

- Creates TracerProvider for distributed tracing
- Creates MeterProvider for metrics collection
- Configures OTLP exporters to send data to collector
- Sets up PrometheusMetricReader for `/metrics` endpoint
- Enables automatic FastAPI instrumentation

**Key settings**:

```python
@dataclass
class OpenTelemetryConfig:
    service_name: str = "mario-pizzeria"
    otlp_endpoint: str = "http://otel-collector:4317"
    enable_fastapi_instrumentation: bool = True
    metric_export_interval_millis: int = 60000  # 1 minute
```

### 3. Prometheus Configuration

**Location**: `deployment/prometheus/prometheus.yml`

**Scrape jobs**:

- `mario-pizzeria-app`: Direct metrics from FastAPI app
- `mario-pizzeria-metrics`: Metrics via OTEL collector
- `prometheus`, `grafana`, `loki`, `tempo`: Infrastructure metrics

**Global settings**:

```yaml
global:
  scrape_interval: 15s # Collect data every 15 seconds
  evaluation_interval: 15s # Evaluate alerting rules every 15 seconds
```

### 4. Grafana Dashboard Configuration

**Location**: `deployment/grafana/dashboards/json/mario-http-performance.json`

**Dashboard Features**:

- **Request Rate**: `sum(rate(http_server_duration_milliseconds_count[5m]))`
- **Response Time**: `sum(rate(http_server_duration_milliseconds_sum[5m])) / sum(rate(http_server_duration_milliseconds_count[5m]))`
- **Error Rate**: `sum(rate(http_server_duration_milliseconds_count{http_status_code=~"[45].*"}[5m]))`
- **Percentiles**: `histogram_quantile(0.95, sum(rate(http_server_duration_milliseconds_bucket[5m])))`

**Provisioning**:

```yaml
# deployment/grafana/dashboards/dashboards.yaml
providers:
  - name: "Mario Pizzeria Dashboards"
    folder: "Mario Pizzeria"
    path: /etc/grafana/provisioning/dashboards/json
    updateIntervalSeconds: 30
```

---

## 📈 Available Metrics

### HTTP Performance Metrics

**Request Rate**:

- `http_server_duration_milliseconds_count` - Total requests
- Broken down by: endpoint, method, status_code

**Response Time**:

- `http_server_duration_milliseconds_sum` - Total response time
- `http_server_duration_milliseconds_bucket` - Response time distribution
- Available percentiles: p50, p95, p99

**Active Requests**:

- `http_server_active_requests` - Current concurrent requests

**Request/Response Size**:

- `http_server_request_size` - Incoming request payload sizes
- `http_server_response_size` - Outgoing response payload sizes

### System Metrics (via OTEL Collector)

**Process Metrics**:

- `process_runtime_py_cpu_time` - CPU usage
- `process_runtime_py_memory` - Memory usage
- `process_runtime_py_gc_count` - Garbage collection stats

**Python Runtime**:

- `python_gc_objects_collected` - GC collection stats
- `python_info` - Python version information

---

## 🚀 Getting Started

### 1. Start the Full Stack

```bash
make mario-start
```

### 2. Access the Dashboards

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Mario App**: http://localhost:8080

### 3. Generate Test Data

```bash
# Make some API calls to generate metrics
curl http://localhost:8080/api/menu/
curl http://localhost:8080/api/orders/
```

### 4. View Metrics

- **Raw Metrics**: http://localhost:8080/api/metrics
- **Prometheus Query**: http://localhost:9090/graph
- **HTTP Dashboard**: http://localhost:3001/d/944f7a30-4637-4cf0-9473-4ddccd020af9/mario-s-pizzeria-http-performance

---

## 🔍 Troubleshooting

### Common Issues

**Metrics endpoint returns 404**:

- Check if `add_metrics_endpoint()` was called
- Verify the endpoint path: `/api/metrics` not `/metrics`

**No data in Grafana**:

- Check Prometheus targets: http://localhost:9090/targets
- Verify both `mario-pizzeria-app` jobs are "UP"
- Generate test traffic with curl commands

**Container networking issues**:

- All containers must be on `mario-pizzeria_mario-net` network
- Check with: `docker network inspect mario-pizzeria_mario-net`
- Restart containers if needed: `make mario-stop && make mario-start`

**Dashboard not loading**:

- Check Grafana logs: `docker logs mario-pizzeria-grafana-1`
- Restart Grafana: `docker restart mario-pizzeria-grafana-1`

### Validation Commands

```bash
# Check if metrics endpoint works
curl -s http://localhost:8080/api/metrics | grep http_server

# Check Prometheus is scraping
curl -s "http://localhost:9090/api/v1/targets" | grep mario

# Check if HTTP metrics are in Prometheus
curl -s "http://localhost:9090/api/v1/query?query=http_server_duration_milliseconds_count"

# Check container status
docker ps | grep mario
```

---

## 📚 Next Steps

This setup provides the foundation for:

1. **CQRS Code-Level Metrics** - Add command/query execution tracking
2. **Business Metrics** - Track orders placed, pizzas made, revenue
3. **Custom Dashboards** - Create domain-specific visualizations
4. **Alerting** - Set up alerts for high error rates or slow responses
5. **Distributed Tracing** - Track requests across multiple services

The observability stack is designed to grow with your application complexity while maintaining performance and reliability.

---

## 🏷️ Tags

- OpenTelemetry
- Prometheus
- Grafana
- FastAPI
- HTTP Metrics
- Docker
- Monitoring
- Observability

**Last Updated**: October 2025  
**Status**: ✅ Production Ready
