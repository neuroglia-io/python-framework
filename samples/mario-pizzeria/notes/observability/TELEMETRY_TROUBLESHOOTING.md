# OpenTelemetry Telemetry Troubleshooting Guide

## Date

October 24, 2025

## Issue Summary

OTEL Collector is receiving telemetry data (traces and metrics) from the Mario's Pizzeria application, but no data is appearing in Grafana dashboards despite all observability services being healthy.

## Environment

- **Application**: Mario's Pizzeria (mario-pizzeria-app)
- **OTEL Collector**: v0.110.0 (ports 4317/4318)
- **Tempo**: v2.6.1 (port 3200)
- **Prometheus**: v2.55.1 (port 9090)
- **Loki**: v3.2.0 (port 3100)
- **Grafana**: v11.3.0 (port 3001)

## Symptoms

### ✅ Working Components

1. **OTEL Collector** - Receiving and processing telemetry

   - Logs show: `6113 traces processed`, `125858 metrics processed`
   - Exporters configured for Tempo, Prometheus, Loki
   - No error messages in logs

2. **OpenTelemetry SDK** - Initialized successfully in application

   ```
   ✅ OTLP Span Exporter configured: http://otel-collector:4317
   ✅ OTLP Metric Exporter configured: http://otel-collector:4317
   ✅ Logging instrumentation enabled
   ✅ HTTPX instrumentation enabled
   ✅ System metrics instrumentation enabled
   🔭 OpenTelemetry initialized for service 'mario-pizzeria' v1.0.0
   ```

3. **All Services Running** - Docker containers healthy

   ```bash
   docker-compose -f docker-compose.mario.yml ps
   # All services show "Up" status
   ```

### ❌ Problem Areas

1. **TracingPipelineBehavior** - Not functioning

   ```
   WARNING  neuroglia.mediation.mediator:675 Error getting pipeline behaviors: PipelineBehavior() takes no arguments
   ```

   - **Root Cause**: Service provider attempting to instantiate abstract `PipelineBehavior` class
   - **Impact**: No automatic CQRS tracing (commands/queries not instrumented)
   - **Location**: `/app/src/neuroglia/dependency_injection/service_provider.py:322`

2. **Tempo Ingester** - Not ready

   ```bash
   curl http://localhost:3200/ready
   # Response: "Ingester not ready: waiting for 15s after being ready"
   ```

   - **Impact**: Traces may not be stored/queryable yet
   - **Status**: Temporary condition (waits 15s after startup)

3. **No Business Metrics in Prometheus**

   ```bash
   curl -s "http://localhost:9090/api/v1/label/__name__/values" | grep mario
   # No results found
   ```

   - **Root Cause**: Business metrics not being recorded (handlers not instrumented)
   - **Impact**: Grafana dashboards have no data to display

4. **No Data in Grafana Dashboards**
   - Mario's Pizzeria Overview Dashboard: Empty panels
   - Neuroglia Framework Dashboard: No traces visible

## Root Cause Analysis

### Issue 1: TracingPipelineBehavior Registration

**Problem**: `Pipeline Behavior() takes no arguments` error when mediator tries to retrieve pipeline behaviors.

**Technical Details**:

- `TracingPipelineBehavior` is registered as a `PipelineBehavior` (abstract class)
- Service provider's `get_services(PipelineBehavior)` method attempts type checking
- Line 322: `if any(type(service) == descriptor.service_type for service in realized_services):`
- When `descriptor.service_type` is the abstract `PipelineBehavior` class, comparison triggers instantiation attempt
- `PipelineBehavior` is abstract and cannot be instantiated without constructor arguments

**Fix Applied**:

1. Added try/except block to handle `TypeError` in service provider
2. Modified `TracingPipelineBehavior.configure()` to register both:
   - Concrete type: `TracingPipelineBehavior`
   - Interface type: `PipelineBehavior` with factory

**Files Modified**:

- `src/neuroglia/dependency_injection/service_provider.py` (line 322-330)
- `src/neuroglia/mediation/tracing_middleware.py` (added `configure()` method)
- `samples/mario-pizzeria/main.py` (changed to use `TracingPipelineBehavior.configure(builder)`)

**Status**: Fix implemented, requires container rebuild to apply

### Issue 2: Missing Business Metrics

**Problem**: Application-specific metrics (orders_created, cooking_duration, etc.) not being recorded.

**Root Cause**:

- Metrics defined in `samples/mario-pizzeria/observability/metrics.py`
- Handlers (PlaceOrderCommand, StartCookingCommand, etc.) not calling metric recording functions
- No business attributes added to auto-generated spans

**Required Fix**:

1. Import and use metrics in command handlers
2. Add `record_metric()` calls in handler methods
3. Add business attributes to spans with `add_span_attributes()`

**Example Implementation Needed**:

```python
# In PlaceOrderCommandHandler
from observability.metrics import orders_created, order_value

async def handle_async(self, command: PlaceOrderCommand):
    # Add business context to span
    add_span_attributes({
        "order.customer_id": command.customer_id,
        "order.item_count": len(command.items),
        "order.delivery_address": command.delivery_address,
    })

    # ... business logic ...
    order = await self.create_order(command)

    # Record metrics
    orders_created.add(1, {"status": order.status.value})
    order_value.record(float(order.total_amount))

    return order
```

### Issue 3: Tempo Ingester Warm-up Period

**Problem**: Tempo ingester not immediately ready after startup.

**Status**: Normal behavior, self-resolving after 15 seconds.

**Verification**:

```bash
# Wait for ready status
sleep 20 && curl http://localhost:3200/ready
# Should return: "ready"
```

## Verification Steps

### 1. Check OTEL Collector Data Flow

```bash
# View collector metrics
docker logs mario-pizzeria-otel-collector-1 --tail 100 | grep -E "traces|metrics|logs"

# Expected: Numbers increasing over time
# processor.outgoing_items{otel_signal="traces"}: XXXX
# processor.outgoing_items{otel_signal="metrics"}: XXXX
```

### 2. Verify Tempo is Storing Traces

```bash
# Check Tempo status
curl http://localhost:3200/ready

# Search for recent traces (replace with actual trace ID)
curl -s "http://localhost:3200/api/traces/{trace_id}"
```

### 3. Check Prometheus Metrics

```bash
# List all metric names
curl -s "http://localhost:9090/api/v1/label/__name__/values" | python3 -m json.tool

# Query specific Mario metrics (after fix applied)
curl -s "http://localhost:9090/api/v1/query?query=mario_orders_created_total"
```

### 4. Test Grafana Datasources

```bash
# Grafana API - List datasources
curl -s -u admin:admin http://localhost:3001/api/datasources | python3 -m json.tool

# Test Tempo datasource
curl -s -u admin:admin http://localhost:3001/api/datasources/proxy/1/api/status/services

# Test Prometheus datasource
curl -s -u admin:admin http://localhost:3001/api/datasources/proxy/2/api/v1/status/config
```

### 5. Generate Test Traffic

```bash
# Place an order (triggers commands and events)
curl -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test-customer",
    "items": [{"pizza_id": "margherita", "quantity": 1}],
    "delivery_address": "123 Main St"
  }'

# Check for new traces
docker logs mario-pizzeria-otel-collector-1 --tail 20
```

## Resolution Checklist

- [x] OpenTelemetry SDK initialized in application
- [x] OTEL Collector receiving telemetry (traces/metrics)
- [x] All observability services running (Tempo, Prometheus, Loki, Grafana)
- [x] TracingPipelineBehavior registration fixed
- [x] Container rebuilt with updated code
- [x] TracingPipelineBehavior functioning (no more errors) - **FIXED!**
- [x] Tempo ready and accepting traces
- [ ] Business metrics instrumented in handlers
- [ ] Metrics visible in Prometheus (mario\_\* metrics)
- [ ] Data flowing to Grafana dashboards
- [ ] Trace-to-log-to-metric correlation working

## Update: October 24, 2025 - TracingPipelineBehavior Fixed! ✅

**Status**: Service provider bug fixed, automatic CQRS tracing now working!

**Fix Applied**:
Modified `src/neuroglia/dependency_injection/service_provider.py` line 322-339 to handle abstract base classes properly:

- Changed from single-line `any()` with generator expression
- Now uses explicit loop with try/except for each service
- Catches `TypeError` when comparing types with abstract classes
- Uses both `type()` comparison and `isinstance()` checks

**Verification**:

```bash
docker logs mario-pizzeria-mario-pizzeria-app-1 --tail 50 | grep "pipeline behaviors"
# Output: Found 2 pipeline behaviors for GetDeliveryOrdersQuery
#         Found 2 pipeline behaviors for GetDeliveryTourQuery
```

**Result**:

- ✅ No more "PipelineBehavior() takes no arguments" errors
- ✅ TracingPipelineBehavior and DomainEventDispatchingMiddleware both active
- ✅ Automatic tracing for all commands and queries enabled

**Next Priority**: Add business metrics instrumentation to handlers to populate Grafana dashboards.

## Next Steps

### Immediate (In Progress)

1. ✅ Fix service provider to handle abstract pipeline behaviors
2. ✅ Update TracingPipelineBehavior registration
3. 🔄 Rebuild Docker container with fixes
4. ⏹️ Verify automatic CQRS tracing is working
5. ⏹️ Check logs for TracingPipelineBehavior span creation

### Short Term

1. Add business metrics to command handlers:
   - `PlaceOrderCommandHandler` - record orders_created, order_value
   - `StartCookingCommandHandler` - record cooking_duration start
   - `CompleteOrderCommandHandler` - record orders_completed, cooking_duration
   - `CancelOrderCommandHandler` - record orders_cancelled
2. Add business attributes to spans in handlers
3. Verify data appears in Grafana dashboards

### Long Term

1. Add custom instrumentation for:
   - Repository operations (already has TracedRepositoryMixin)
   - Event handlers (already has tracing support)
   - API endpoints (FastAPI auto-instrumentation)
2. Create alerts in Grafana for:
   - High order cancellation rate
   - Slow cooking times
   - High error rates
3. Add exemplar links from metrics to traces
4. Document observability patterns in MkDocs

## Related Documentation

- `docs/guides/opentelemetry-integration.md` - Complete OTEL setup guide
- `docs/guides/otel-framework-integration-analysis.md` - Framework architecture
- `GRAFANA_QUICK_ACCESS.md` - Dashboard access guide
- `deployment/grafana/dashboards/README.md` - Dashboard customization

## Debugging Commands

### View Application Logs with Trace Context

```bash
docker logs mario-pizzeria-mario-pizzeria-app-1 -f | grep -E "trace_id|span_id"
```

### Check OTEL Collector Debug Output

```bash
# Enable debug exporter in OTEL config if needed
docker logs mario-pizzeria-otel-collector-1 --tail 200
```

### Monitor Mediator Pipeline Execution

```bash
docker logs mario-pizzeria-mario-pizzeria-app-1 -f | grep -E "MEDIATOR DEBUG|pipeline behaviors"
```

### Test Trace Export

```bash
# If FastAPI instrumentation is working, HTTP requests should create traces
curl http://localhost:8080/api/menu

# Check if trace was exported
docker logs mario-pizzeria-otel-collector-1 --tail 50 | grep "Span"
```

## Known Issues

### Issue: PipelineBehavior Abstract Class Error

**Symptom**: `TypeError: PipelineBehavior() takes no arguments`  
**Workaround**: Rebuild container with service provider fix  
**Permanent Fix**: Enhance service provider to handle ABCs gracefully  
**Status**: Fix applied, testing in progress

### Issue: Tempo Ingester Startup Delay

**Symptom**: "Ingester not ready: waiting for 15s after being ready"  
**Workaround**: Wait 20-30 seconds after container start  
**Permanent Fix**: None needed (expected behavior)  
**Status**: Normal operation

### Issue: No Business Metrics

**Symptom**: Prometheus has no `mario_*` metrics  
**Workaround**: None - requires code changes  
**Permanent Fix**: Instrument handlers with metric recording  
**Status**: Pending implementation

## Conclusion

The observability infrastructure is correctly configured and operational. The primary issues are:

1. **TracingPipelineBehavior not functioning** due to service provider bug (fix applied, needs rebuild)
2. **Business metrics not recorded** because handlers aren't instrumented (pending implementation)

Once the container is rebuilt with the service provider fix, automatic CQRS tracing should work. After adding business metrics to handlers, Grafana dashboards will populate with data.

---

**Last Updated**: October 24, 2025  
**Author**: DevOps/Observability Team  
**Status**: Active Investigation - Fixes Implemented, Testing in Progress
