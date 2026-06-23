# Prometheus /metrics Endpoint Fix

## Problem

The `/metrics` endpoint was not mounting in applications, preventing Prometheus from scraping OpenTelemetry metrics.

## Root Cause

The `opentelemetry-exporter-prometheus` package was removed from dependencies due to a previous protobuf 5.x incompatibility issue. The comment in `pyproject.toml` stated:

```toml
# Note: Prometheus exporter removed - incompatible with protobuf 5.x
# Use OTLP export to collector, then collector exports to Prometheus
prometheus-client = "^0.21.0"
```

However, the framework code still expected the Prometheus exporter to be available:

```python
# src/neuroglia/observability/metrics.py
from opentelemetry.exporter.prometheus import PrometheusMetricReader  # ImportError!
```

When the import failed, the `/metrics` endpoint would fall back to a minimal placeholder that doesn't expose actual metrics.

## Solution

Added `opentelemetry-exporter-prometheus` back to dependencies. The latest versions (0.49b2+) are now **fully compatible** with protobuf 5.x.

### Changes Made

#### 1. Updated `pyproject.toml`

**Before:**

```toml
opentelemetry-instrumentation-system-metrics = "^0.49b2"
# Note: Prometheus exporter removed - incompatible with protobuf 5.x
# Use OTLP export to collector, then collector exports to Prometheus
prometheus-client = "^0.21.0"
```

**After:**

```toml
opentelemetry-instrumentation-system-metrics = "^0.49b2"
opentelemetry-exporter-prometheus = "^0.49b2"  # Prometheus /metrics endpoint support
prometheus-client = "^0.21.0"  # Required by opentelemetry-exporter-prometheus
```

#### 2. Existing Code Already Handles This

The framework code in `src/neuroglia/observability/otel_sdk.py` already has proper handling:

```python
# Optional Prometheus import
try:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
except ImportError:
    PrometheusMetricReader = None

# Conditional Prometheus reader creation
if PrometheusMetricReader is not None:
    try:
        prometheus_reader = PrometheusMetricReader()
        readers.append(prometheus_reader)
        log.debug("📊 Prometheus metrics reader configured")
    except Exception as e:
        log.warning(f"⚠️ Prometheus reader setup failed: {e}")
else:
    log.info("ℹ️ Prometheus exporter not available - using OTLP metrics only")
```

## How It Works

### Dual Export Strategy

With this fix, applications now export metrics in **two ways**:

1. **OTLP Export to Collector** (gRPC/HTTP):

   ```
   App → OTEL Collector (port 4417) → Prometheus
   ```

2. **Direct Prometheus Scraping** (HTTP pull):

   ```
   Prometheus → App /metrics endpoint → Metrics in Prometheus format
   ```

### Architecture

```
┌─────────────────┐
│   Application   │
│                 │
│  Metrics:       │
│  - Counters     │
│  - Histograms   │
│  - Gauges       │
└────────┬────────┘
         │
         ├─────────────────────────┐
         │                         │
         │ OTLP Push               │ HTTP Pull (Prometheus)
         ▼                         ▼
┌──────────────────┐      ┌───────────────┐
│  OTEL Collector  │      │  /metrics     │
│  (port 4417)     │      │  endpoint     │
└────────┬─────────┘      └───────┬───────┘
         │                         │
         │ Remote Write            │ Scrape
         ▼                         ▼
┌──────────────────┐      ┌───────────────┐
│   Prometheus     │◄─────┤  Prometheus   │
│   (port 9090)    │      │  (port 9090)  │
└──────────────────┘      └───────────────┘
```

## Benefits

✅ **Full Prometheus Integration**: Applications can be scraped directly by Prometheus
✅ **Dual Export**: Metrics available via both OTLP push and Prometheus pull
✅ **Grafana Compatibility**: Works seamlessly with Prometheus data source
✅ **Standard Format**: Metrics exposed in standard Prometheus text format
✅ **Auto-discovery**: Service discovery tools can find `/metrics` endpoints

## Installation

After this change, install the updated dependencies:

```bash
# Install/update dependencies
poetry install

# For Docker-based deployments
docker-compose build --no-cache mario-pizzeria-app
```

## Verification

### 1. Check Metrics Endpoint

```bash
curl http://localhost:8080/metrics
```

Should return Prometheus format metrics:

```
# HELP mario_orders_created Total orders created
# TYPE mario_orders_created counter
mario_orders_created{status="pending"} 5.0
...
```

### 2. Check Prometheus Targets

Visit `http://localhost:9090/targets` and verify the application target is **UP**.

### 3. Check Grafana

1. Open Grafana: `http://localhost:3001`
2. Add Prometheus data source: `http://prometheus:9090`
3. Query metrics: `rate(mario_orders_created[5m])`

## Configuration

### Enable/Disable Metrics Endpoint

In application settings:

```python
# .env or settings file
OBSERVABILITY_METRICS_ENDPOINT=true
OBSERVABILITY_METRICS_PATH=/metrics
```

Or programmatically:

```python
from neuroglia.observability import Observability, ObservabilityConfig

config = ObservabilityConfig(
    metrics_endpoint=True,  # Enable /metrics
    metrics_path="/metrics"
)
Observability.configure(builder, config)
```

## Historical Context

### Timeline

1. **Initial State**: Prometheus exporter included in dependencies
2. **Problem Discovered**: Protobuf 5.x incompatibility with old opentelemetry-exporter-prometheus
3. **Temporary Fix**: Removed Prometheus exporter, relied on OTLP → Collector → Prometheus
4. **Upstream Fix**: OpenTelemetry updated to support protobuf 5.x (versions 0.49b2+)
5. **This Fix**: Re-enabled Prometheus exporter with compatible versions

### Related Issues

- Protobuf dependency conflicts between etcd3-py and opentelemetry packages
- Solution: Updated to protobuf 5.29.5 which is compatible with both

## Testing

The framework already has comprehensive OpenTelemetry integration. After installing dependencies:

```bash
# Run Mario's Pizzeria
./mario-pizzeria start

# Test metrics endpoint
curl http://localhost:8080/metrics | head -20

# Should see OpenTelemetry metrics in Prometheus format
```

---

**Date**: November 7, 2025
**Author**: Bruno van de Werve
**Version**: 0.6.3 (unreleased)
**Status**: ✅ Fixed and tested
