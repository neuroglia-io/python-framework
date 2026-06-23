# 🔭 OpenTelemetry Integration Guide

_Infrastructure setup and deployment guide for production observability_

## 📋 Overview

This guide covers the comprehensive OpenTelemetry (OTEL) integration for the Neuroglia framework and Mario's Pizzeria application, providing full observability through distributed tracing, metrics, and structured logging.

### 📚 Documentation Map

This guide focuses on **infrastructure provisioning and deployment**. For a complete observability learning path:

1. **Start here** for infrastructure setup (Docker Compose, Kubernetes)
2. **[Observability Feature Guide](../features/observability.md)** - Developer instrumentation and API reference
3. **[Tutorial: Mario's Pizzeria Observability](../tutorials/mario-pizzeria-08-observability.md)** - Step-by-step implementation
4. **[Mario's Pizzeria Sample](../mario-pizzeria.md)** - Complete working example

### 🎯 What This Guide Covers

- ✅ Complete observability stack architecture
- ✅ Docker Compose configuration for all components
- ✅ OTEL Collector setup and configuration
- ✅ Grafana, Tempo, Prometheus, and Loki integration
- ✅ Multi-application instrumentation patterns
- ✅ Production deployment considerations
- ✅ Troubleshooting and verification steps

### 📝 What This Guide Does NOT Cover

See the **[Observability Feature Guide](../features/observability.md)** for:

- Code instrumentation patterns (controllers, handlers, repositories)
- Choosing metric types (counter, gauge, histogram)
- Tracing decorators and manual instrumentation
- Data flow from application to dashboard
- Layer-specific implementation guidance
- API reference and configuration options

## 🎯 Observability Pillars

### 1. **Distributed Tracing** 🔍

- **Purpose**: Track requests across services and layers
- **Backend**: Tempo (Grafana's distributed tracing system)
- **Benefits**: Understand request flow, identify bottlenecks, debug distributed systems

### 2. **Metrics** 📊

- **Purpose**: Quantitative measurements of application performance
- **Backend**: Prometheus (time-series database)
- **Benefits**: Monitor performance trends, set alerts, capacity planning

### 3. **Logging** 📝

- **Purpose**: Structured event records with trace correlation
- **Backend**: Loki (Grafana's log aggregation system)
- **Benefits**: Debug issues, audit trails, correlated with traces

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Mario Pizzeria App                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  OpenTelemetry SDK (Python)                          │  │
│  │  - TracerProvider (traces)                           │  │
│  │  - MeterProvider (metrics)                           │  │
│  │  - LoggerProvider (logs)                             │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │ OTLP/gRPC (4317) or HTTP (4318)        │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│            OpenTelemetry Collector (All-in-One)              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Receivers:  OTLP (gRPC 4317, HTTP 4318)             │  │
│  │  Processors: Batch, Memory Limiter, Resource         │  │
│  │  Exporters:  Tempo, Prometheus, Loki, Console        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────┬─────────────┬─────────────┬─────────────────────────┘
          │             │             │
          ▼             ▼             ▼
    ┌─────────┐   ┌──────────┐  ┌──────────┐
    │  Tempo  │   │Prometheus│  │   Loki   │
    │ (Traces)│   │(Metrics) │  │  (Logs)  │
    └────┬────┘   └─────┬────┘  └─────┬────┘
         │              │             │
         └──────────────┼─────────────┘
                        │
                        ▼
                 ┌─────────────┐
                 │   Grafana   │
                 │ (Dashboard) │
                 └─────────────┘
```

## 📦 Components

### OpenTelemetry Collector (All-in-One)

- **Image**: `otel/opentelemetry-collector-contrib:latest`
- **Purpose**: Central hub for receiving, processing, and exporting telemetry
- **Ports**:
  - `4317`: OTLP gRPC receiver
  - `4318`: OTLP HTTP receiver
  - `8888`: Prometheus metrics about the collector itself
  - `13133`: Health check endpoint

### Grafana Tempo

- **Image**: `grafana/tempo:latest`
- **Purpose**: Distributed tracing backend
- **Ports**: `3200` (HTTP API), `9095` (gRPC), `4317` (OTLP gRPC)
- **Storage**: Local filesystem (configurable to S3, GCS, etc.)

### Prometheus

- **Image**: `prom/prometheus:latest`
- **Purpose**: Metrics storage and querying
- **Ports**: `9090` (Web UI and API)
- **Scrape Interval**: 15s

### Grafana Loki

- **Image**: `grafana/loki:latest`
- **Purpose**: Log aggregation and querying
- **Ports**: `3100` (HTTP API)
- **Storage**: Local filesystem

### Grafana

- **Image**: `grafana/grafana:latest`
- **Purpose**: Unified dashboard for traces, metrics, and logs
- **Ports**: `3001` (Web UI)
- **Default Credentials**: admin/admin (change on first login)

## 🔧 Implementation Components

### 1. Framework Module: `neuroglia.observability`

**Purpose**: Provide reusable OpenTelemetry integration for all Neuroglia applications

**Key Features**:

- Automatic instrumentation setup (FastAPI, HTTPX, logging)
- TracerProvider and MeterProvider initialization
- Context propagation configuration
- Resource detection (service name, version, host)
- Configurable exporters (OTLP, Console, Jaeger compatibility)

**Public API**:

```python
from neuroglia.observability import (
    configure_opentelemetry,
    get_tracer,
    get_meter,
    trace_async,  # Decorator for automatic tracing
    record_metric,
)

# Initialize OTEL (call once at startup)
configure_opentelemetry(
    service_name="mario-pizzeria",
    service_version="1.0.0",
    otlp_endpoint="http://otel-collector:4317",
    enable_console_export=False,
)

# Get tracer for manual instrumentation
tracer = get_tracer(__name__)

# Automatic tracing decorator
@trace_async()
async def process_order(order_id: str):
    # Automatically creates a span
    pass
```

### 2. Tracing Middleware

**Layers Instrumented**:

- ✅ HTTP Requests (automatic via FastAPI instrumentation)
- ✅ Commands (CQRSTracingMiddleware)
- ✅ Queries (CQRSTracingMiddleware)
- ✅ Event Handlers (EventHandlerTracingMiddleware)
- ✅ Repository Operations (RepositoryTracingMixin)
- ✅ External HTTP Calls (automatic via HTTPX instrumentation)

**Span Attributes**:

- `command.type`: Command class name
- `query.type`: Query class name
- `event.type`: Event class name
- `aggregate.id`: Aggregate identifier
- `repository.operation`: get/save/update/delete
- `http.method`, `http.url`, `http.status_code`

### 3. Metrics Collection

**Business Metrics**:

- `mario.orders.created` (counter): Total orders placed
- `mario.orders.completed` (counter): Total orders delivered
- `mario.orders.cancelled` (counter): Total cancelled orders
- `mario.pizzas.ordered` (counter): Total pizzas ordered
- `mario.orders.value` (histogram): Order value distribution

**Technical Metrics**:

- `neuroglia.command.duration` (histogram): Command execution time
- `neuroglia.query.duration` (histogram): Query execution time
- `neuroglia.event.processing.duration` (histogram): Event handler time
- `neuroglia.repository.operation.duration` (histogram): Repository operation time
- `neuroglia.http.request.duration` (histogram): HTTP request duration

**Labels/Attributes**:

- `service.name`: "mario-pizzeria"
- `command.type`: Command class name
- `query.type`: Query class name
- `event.type`: Event class name
- `repository.type`: Repository class name
- `status`: "success" | "error"

### 4. Structured Logging

**Features**:

- JSON structured logs with trace context
- Automatic trace_id and span_id injection
- Log level filtering
- OTLP log export to Loki via collector

**Log Format**:

```json
{
  "timestamp": "2025-10-24T10:15:30.123Z",
  "level": "INFO",
  "message": "Order placed successfully",
  "service.name": "mario-pizzeria",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "order_id": "61a61887-4200-4d0c-85d3-45c2cdd9cc08",
  "customer_id": "cust_123",
  "total_amount": 25.5
}
```

## ⚙️ FastAPI Multi-Application Instrumentation

### 🚨 Critical Configuration for Multi-App Architectures

When building applications with multiple mounted FastAPI apps (main app + sub-apps), **proper OpenTelemetry instrumentation configuration is crucial** to avoid duplicate metrics warnings and ensure complete observability coverage.

#### **The Problem: Duplicate Instrumentation**

**❌ WRONG - Causes duplicate metric warnings:**

```python
# This creates duplicate HTTP metrics instruments
from neuroglia.observability import instrument_fastapi_app

# Main application
app = FastAPI(title="Mario's Pizzeria")

# Sub-applications
api_app = FastAPI(title="API")
ui_app = FastAPI(title="UI")

# ❌ DON'T DO THIS - Causes warnings
instrument_fastapi_app(app, "main-app")
instrument_fastapi_app(api_app, "api-app")    # ⚠️ Duplicate metrics
instrument_fastapi_app(ui_app, "ui-app")      # ⚠️ Duplicate metrics

# Mount sub-apps
app.mount("/api", api_app)
app.mount("/", ui_app)
```

**Error Messages You'll See:**

```
WARNING  An instrument with name http.server.duration, type Histogram...
has been created already.
WARNING  An instrument with name http.server.request.size, type Histogram...
has been created already.
```

#### **✅ CORRECT - Single Main App Instrumentation**

**The solution: Only instrument the main app that contains mounted sub-apps**

```python
from neuroglia.observability import configure_opentelemetry, instrument_fastapi_app

# 1. Initialize OpenTelemetry first (once per application)
configure_opentelemetry(
    service_name="mario-pizzeria",
    service_version="1.0.0",
    otlp_endpoint="http://otel-collector:4317"
)

# 2. Create applications
app = FastAPI(title="Mario's Pizzeria")
api_app = FastAPI(title="API")
ui_app = FastAPI(title="UI")

# 3. Define endpoints BEFORE mounting (important for health checks)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 4. Mount sub-applications
app.mount("/api", api_app, name="api")
app.mount("/", ui_app, name="ui")

# 5. ✅ ONLY instrument the main app
instrument_fastapi_app(app, "mario-pizzeria-main")
```

#### **📊 Complete Coverage Verification**

This single instrumentation captures **ALL endpoints across all mounted applications**:

**Example Tracked Endpoints:**

```python
# All these endpoints are automatically instrumented:
✅ /health                (main app)
✅ /                      (UI sub-app root)
✅ /menu                  (UI sub-app)
✅ /orders                (UI sub-app)
✅ /api/menu/             (API sub-app)
✅ /api/orders/           (API sub-app)
✅ /api/kitchen/status    (API sub-app)
✅ /api/docs              (API sub-app)
✅ /api/metrics           (API sub-app)
```

**HTTP Status Codes Tracked:**

```python
✅ 200 OK                (successful requests)
✅ 307 Temporary Redirect (FastAPI automatic redirects)
✅ 404 Not Found          (missing endpoints)
✅ 401 Unauthorized       (auth failures)
✅ 500 Internal Error     (application errors)
```

#### **🔍 How It Works**

1. **Request Flow**: All HTTP requests reach the main app first
2. **Middleware Order**: OpenTelemetry middleware intercepts requests before routing
3. **Sub-App Processing**: Requests are then routed to appropriate mounted sub-apps
4. **Metric Collection**: Single point of HTTP metric collection with complete coverage

```
HTTP Request → Main App (instrumented) → Mounted Sub-App → Response
                  ↑
            Metrics captured here
```

#### **🎯 Best Practices**

1. **Single Instrumentation Point**: Only instrument the main FastAPI app
2. **Timing Matters**: Mount sub-apps before instrumenting the main app
3. **Health Endpoints**: Define main app endpoints before mounting to avoid 404s
4. **Service Naming**: Use descriptive names for the instrumented app
5. **Verification**: Check `/metrics` endpoint to confirm all routes are tracked

#### **🚨 Common Pitfalls**

1. **Instrumenting Sub-Apps**: Never instrument mounted sub-applications directly
2. **Order of Operations**: Don't instrument before mounting sub-apps
3. **Missing Routes**: Define health/metrics endpoints on main app, not sub-apps
4. **Duplicate Names**: Use unique service names for different instrumentation calls

#### **📈 Metrics Verification**

Verify your instrumentation is working correctly:

```bash
# Check all tracked endpoints
curl -s "http://localhost:8080/api/metrics" | \
  grep 'http_target=' | \
  sed 's/.*http_target="\([^"]*\)".*/\1/' | \
  sort | uniq

# Expected output:
# /
# /api/menu/
# /api/orders/
# /health
# /api/metrics
```

#### **📋 Integration Checklist**

- [ ] ✅ Initialize OpenTelemetry once at startup
- [ ] ✅ Create all FastAPI apps (main + sub-apps)
- [ ] ✅ Define main app endpoints (health, metrics)
- [ ] ✅ Mount all sub-applications to main app
- [ ] ✅ Instrument ONLY the main app
- [ ] ✅ Verify no duplicate metric warnings in logs
- [ ] ✅ Confirm all endpoints appear in metrics
- [ ] ✅ Test trace propagation across all routes

This configuration ensures **complete observability coverage** without duplicate instrumentation warnings, providing clean metrics collection across your entire multi-application architecture.

## 🚀 Key Benefits

### For Development

1. **Debug Distributed Systems**: See exact request flow across layers
2. **Identify Bottlenecks**: Visualize which components are slow
3. **Understand Dependencies**: See how services interact
4. **Root Cause Analysis**: Correlate logs with traces for faster debugging

### For Operations

1. **Performance Monitoring**: Track response times and throughput
2. **Alerting**: Set alerts on SLIs (latency, error rate, saturation)
3. **Capacity Planning**: Understand resource usage trends
4. **Incident Response**: Quickly isolate and diagnose issues

### For Business

1. **User Experience**: Monitor actual user-facing performance
2. **Feature Usage**: Track which features are used most
3. **Business Metrics**: Orders, revenue, conversion rates
4. **SLA Compliance**: Measure and report on service level objectives

## 🎨 Grafana Dashboards

### 1. Overview Dashboard

- Request rate (requests/sec)
- Error rate (%)
- P50, P95, P99 latency
- Active services
- Top endpoints by traffic

### 2. Traces Dashboard (Tempo)

- Trace search by operation, duration, tags
- Service dependency graph
- Span flamegraphs
- Trace-to-logs correlation

### 3. Metrics Dashboard (Prometheus)

- Command execution time (histogram)
- Query execution time (histogram)
- Event processing time (histogram)
- Repository operation time (histogram)
- Business metrics (orders, pizzas, revenue)

### 4. Logs Dashboard (Loki)

- Log stream viewer
- Log filtering by trace_id, service, level
- Log rate over time
- Error log aggregation

### 5. Mario's Pizzeria Business Dashboard

- Orders per hour
- Average order value
- Popular pizzas
- Order status distribution
- Delivery time metrics

## 📊 Trace Context Propagation

OpenTelemetry uses W3C Trace Context for propagating trace information:

**HTTP Headers**:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
tracestate: vendor1=value1,vendor2=value2
```

**Propagation Flow**:

1. Incoming HTTP request with traceparent header
2. FastAPI auto-instrumentation extracts context
3. Context propagated to commands, queries, events
4. Context included in outgoing HTTP calls
5. Context correlated in logs and metrics

## 🔒 Security Considerations

1. **Network Isolation**: OTEL collector not exposed to public internet
2. **Authentication**: Grafana requires login (admin/admin default)
3. **Data Retention**: Configure retention policies for traces/logs/metrics
4. **PII Handling**: Avoid logging sensitive customer data
5. **Resource Limits**: Configure memory/CPU limits for collector

## ⚡ Performance Considerations

1. **Sampling**: Use tail-based sampling for high-volume services
2. **Batch Processing**: Collector batches telemetry before export
3. **Async Export**: Telemetry export is non-blocking
4. **Resource Detection**: Done once at startup
5. **Memory Limits**: Configure collector memory_limiter processor

**Typical Overhead**:

- Tracing: < 1-2% CPU overhead
- Metrics: < 1% CPU overhead
- Logging: < 5% CPU overhead (structured logging)

## 🧪 Testing OTEL Integration

### Manual Testing

```bash
# 1. Start services
./mario-docker.sh start

# 2. Generate some traffic
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_123",
    "items": [{"pizza_id": "margherita", "quantity": 2}]
  }'

# 3. Check OTEL collector health
curl http://localhost:13133/

# 4. View Grafana dashboards
open http://localhost:3001
# Login: admin/admin
# Navigate: Explore → Tempo (traces)
# Navigate: Explore → Prometheus (metrics)
# Navigate: Explore → Loki (logs)

# 5. Check collector logs
docker logs mario-pizzeria-otel-collector-1
```

### Verify Trace Flow

1. **In Application**: Check logs for trace_id in output
2. **In Collector**: Check collector logs for received spans
3. **In Tempo**: Search for traces in Grafana Explore
4. **In Grafana**: View trace waterfall and span details

### Verify Metrics Flow

1. **In Application**: Metrics recorded and exported
2. **In Collector**: Metrics forwarded to Prometheus
3. **In Prometheus**: Query metrics with PromQL
4. **In Grafana**: Visualize metrics on dashboards

### Verify Logs Flow

1. **In Application**: Structured logs with trace context
2. **In Collector**: Logs forwarded to Loki
3. **In Loki**: Query logs with LogQL
4. **In Grafana**: View correlated logs with traces

## 🔗 Related Documentation

### Neuroglia Framework

- **[Observability Feature Guide](../features/observability.md)** - Comprehensive developer guide and API reference
- **[Tutorial: Mario's Pizzeria Observability](../tutorials/mario-pizzeria-08-observability.md)** - Step-by-step implementation
- **[Mario's Pizzeria Sample](../mario-pizzeria.md)** - Complete working example
- **[CQRS & Mediation](../features/simple-cqrs.md)** - Automatic handler tracing
- **[Getting Started](../getting-started.md)** - Framework setup

### External Resources

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Grafana Tempo Documentation](https://grafana.com/docs/tempo/latest/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [OTEL Framework Integration Analysis](otel-framework-integration-analysis.md) - Internal design notes

## 🎓 Learning Resources

### Concepts

- [Observability vs Monitoring](https://www.honeycomb.io/blog/observability-vs-monitoring)
- [Distributed Tracing Guide](https://opentelemetry.io/docs/concepts/signals/traces/)
- [Metrics Best Practices](https://prometheus.io/docs/practices/naming/)

### Tutorials

- [Getting Started with OpenTelemetry](https://opentelemetry.io/docs/instrumentation/python/getting-started/)
- [Grafana Fundamentals](https://grafana.com/tutorials/grafana-fundamentals/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## 📝 Next Steps

After completing the OTEL integration:

1. **Baseline Performance**: Establish baseline metrics for all operations
2. **Set SLOs**: Define Service Level Objectives (e.g., P95 < 500ms)
3. **Create Alerts**: Configure alerts for SLO violations
4. **Document Runbooks**: Create troubleshooting guides using traces
5. **Optimize Hot Paths**: Use trace data to identify and optimize slow operations
6. **Custom Dashboards**: Build domain-specific dashboards for your team
7. **Team Training**: Train team on using Grafana for debugging and monitoring

---

**Status**: Implementation in progress - see TODO list for detailed task breakdown
