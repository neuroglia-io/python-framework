# 🚀 OpenTelemetry Quick Reference - Neuroglia Framework

**Last Updated**: December 2024  
**Status**: Framework Integration Complete ✅

---

## 📦 One-Time Setup (Already Done)

✅ Dependencies installed (21 packages)  
✅ Infrastructure configured (5 Docker services)  
✅ Framework module complete (`neuroglia.observability`)  
✅ Middleware complete (CQRS, events, repositories)

---

## 🎯 Getting Started (3 Steps)

### 1. Initialize OpenTelemetry

```python
# In your application's main.py or startup
from neuroglia.observability import configure_opentelemetry

configure_opentelemetry(
    service_name="your-service-name",
    service_version="1.0.0",
)
```

### 2. Register Tracing Middleware

```python
from neuroglia.mediation.tracing_middleware import TracingPipelineBehavior

# Automatic tracing for ALL commands and queries
services.add_pipeline_behavior(TracingPipelineBehavior)
```

### 3. Add Tracing to Repositories

```python
from neuroglia.data.infrastructure.tracing_mixin import TracedRepositoryMixin
from neuroglia.data.infrastructure.mongo import MotorRepository

class YourRepository(TracedRepositoryMixin, MotorRepository[YourEntity, str]):
    pass  # Automatic tracing for all CRUD operations!
```

**That's it!** You now have complete distributed tracing with zero additional code. 🎉

---

## 📊 What You Get Automatically

### Automatic Spans

✅ **HTTP Requests** (FastAPI auto-instrumentation)

- Span name: `GET /api/orders`
- Attributes: `http.method`, `http.route`, `http.status_code`

✅ **Commands** (TracingPipelineBehavior)

- Span name: `Command.PlaceOrderCommand`
- Attributes: `cqrs.operation`, `cqrs.type`, `aggregate.id`
- Metric: `neuroglia.command.duration`

✅ **Queries** (TracingPipelineBehavior)

- Span name: `Query.GetOrderByIdQuery`
- Attributes: `cqrs.operation`, `cqrs.type`
- Metric: `neuroglia.query.duration`

✅ **Events** (TracedEventHandler wrapper)

- Span name: `Event.OrderCreatedEvent`
- Attributes: `event.type`, `event.handler`, `aggregate.id`
- Metric: `neuroglia.event.processing.duration`

✅ **Repository Operations** (TracedRepositoryMixin)

- Span name: `Repository.get`, `Repository.add`, etc.
- Attributes: `repository.type`, `entity.type`, `entity.id`
- Metric: `neuroglia.repository.operation.duration`

### Automatic Metrics

| Metric Name                               | Type      | Description                    |
| ----------------------------------------- | --------- | ------------------------------ |
| `neuroglia.command.duration`              | Histogram | Command execution time (ms)    |
| `neuroglia.query.duration`                | Histogram | Query execution time (ms)      |
| `neuroglia.event.processing.duration`     | Histogram | Event processing time (ms)     |
| `neuroglia.repository.operation.duration` | Histogram | Repository operation time (ms) |

### Automatic Log Correlation

✅ **trace_id** and **span_id** automatically injected into logs  
✅ Click trace_id in Grafana Loki → Jump to corresponding trace  
✅ JSON structured logging with timestamps

---

## 🎨 Optional: Add Business Context

### Add Custom Attributes to Spans

```python
from neuroglia.observability import add_span_attributes

async def handle_async(self, command: PlaceOrderCommand):
    # Framework creates span automatically

    # Add business-specific attributes
    add_span_attributes({
        "order.id": order.id,
        "customer.id": command.customer_id,
        "order.item_count": len(command.items),
        "order.total": float(order.total_amount),
        "order.payment_method": command.payment_method,
    })

    # ... rest of business logic
```

### Record Business Metrics

```python
from neuroglia.observability import create_counter, create_histogram

# Define metrics (once, at module level)
orders_created = create_counter(
    name="orders.created",
    unit="orders",
    description="Total orders created"
)

order_value = create_histogram(
    name="orders.value",
    unit="USD",
    description="Order value distribution"
)

# Record metrics (in handlers)
async def handle_async(self, command: PlaceOrderCommand):
    # ... business logic

    orders_created.add(1, {"status": "pending", "payment": command.payment_method})
    order_value.record(float(order.total_amount), {"status": "pending"})
```

### Manual Span Creation (Rarely Needed)

```python
from neuroglia.observability import get_tracer

tracer = get_tracer(__name__)

async def complex_business_logic():
    with tracer.start_as_current_span("complex_calculation") as span:
        span.set_attribute("calculation.type", "tax")
        result = await calculate_tax()
        span.set_attribute("calculation.result", result)
        return result
```

---

## 🔍 Viewing Your Traces

### Grafana Access

```
URL: http://localhost:3001
Username: admin
Password: admin
```

### View Traces (Tempo)

1. Go to **Explore** → Select **Tempo** datasource
2. Click **Search** tab
3. Select recent time range (e.g., "Last 15 minutes")
4. Filter by:
   - Service Name: `mario-pizzeria`
   - Span Name: `Command.PlaceOrderCommand`
   - Min Duration: `100ms`
5. Click trace to see full hierarchy

### View Metrics (Prometheus)

1. Go to **Explore** → Select **Prometheus** datasource
2. Query examples:

   ```promql
   # Command execution time (P95)
   histogram_quantile(0.95, rate(neuroglia_command_duration_bucket[5m]))

   # Request rate
   rate(http_requests_total[5m])

   # Error rate
   rate(http_requests_total{status=~"5.."}[5m])
   ```

### View Logs (Loki)

1. Go to **Explore** → Select **Loki** datasource
2. Query examples:

   ```logql
   # All logs for service
   {service_name="mario-pizzeria"}

   # Logs for specific trace
   {service_name="mario-pizzeria"} |= "trace_id=abc123"

   # Error logs only
   {service_name="mario-pizzeria"} |= "ERROR"
   ```

### Trace-to-Log-to-Metric Correlation

1. Find a trace in Tempo
2. Note the **trace_id**
3. In Loki, search for that trace_id → See all related logs
4. Click **exemplar** links in metrics → Jump to corresponding traces

---

## 🛠️ Environment Variables

These are already configured in `docker-compose.mario.yml`:

```bash
OTEL_SERVICE_NAME=mario-pizzeria
OTEL_SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_INSECURE=true
```

---

## 🧪 Testing Your Integration

### 1. Start Services

```bash
./mario-docker.sh restart
```

### 2. Verify OTEL Collector

```bash
# Health check
curl http://localhost:13133/

# View collector logs
docker logs mario-pizzeria-otel-collector-1
```

### 3. Generate Test Traffic

```bash
curl -X POST http://localhost:8080/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_123",
    "items": [{"pizza_id": "margherita", "quantity": 2}]
  }'
```

### 4. Check Application Logs

```bash
# Look for trace_id in logs
docker logs mario-pizzeria-mario-pizzeria-app-1 2>&1 | grep trace_id
```

### 5. View Trace in Grafana

1. Open http://localhost:3001
2. Explore → Tempo
3. Search for recent traces
4. Verify span hierarchy

---

## 📝 Common Patterns

### Pattern 1: Command with Custom Metrics

```python
from neuroglia.observability import add_span_attributes
from observability.metrics import orders_created

class PlaceOrderHandler(CommandHandler):
    async def handle_async(self, command: PlaceOrderCommand):
        # Add business context
        add_span_attributes({
            "order.id": order.id,
            "customer.id": command.customer_id,
        })

        # Record metric
        orders_created.add(1, {"payment": command.payment_method})

        # Business logic
        await self.repository.add_async(order)
        return self.created(order)
```

### Pattern 2: Query with Performance Tracking

```python
from neuroglia.observability import add_span_attributes

class GetOrderByIdHandler(QueryHandler):
    async def handle_async(self, query: GetOrderByIdQuery):
        # Framework automatically times the query

        order = await self.repository.get_async(query.order_id)

        if order:
            # Add business context
            add_span_attributes({
                "order.status": order.status,
                "order.value": float(order.total_amount),
            })

        return order
```

### Pattern 3: Event Handler with Chaining

```python
from neuroglia.observability import add_span_attributes

class OrderCreatedHandler(DomainEventHandler):
    async def handle_async(self, notification: OrderCreatedEvent):
        # Framework creates span automatically

        add_span_attributes({
            "event.source": "order_aggregate",
            "customer.id": notification.customer_id,
        })

        # Downstream operations are automatically traced
        await self.email_service.send_confirmation(notification.order_id)
        await self.notification_service.notify_kitchen(notification.order_id)
```

---

## 🚨 Troubleshooting

### No Traces Appearing

**Check**:

1. OTEL Collector running: `docker ps | grep otel-collector`
2. Environment variables set in docker-compose
3. Application logs show trace_ids
4. Tempo datasource configured in Grafana

**Solution**:

```bash
# Restart all services
./mario-docker.sh restart

# Check collector health
curl http://localhost:13133/
```

### Traces Missing Spans

**Check**:

1. Middleware registered: `services.add_pipeline_behavior(TracingPipelineBehavior)`
2. Repository uses TracedRepositoryMixin
3. Event handlers wrapped with `wrap_event_handler_with_tracing()`

### Metrics Not Recording

**Check**:

1. Metric defined with correct type (counter/histogram)
2. Recording with correct format: `metric.add(value, attributes)`
3. Prometheus scraping endpoint: http://localhost:9090/targets

### Logs Missing trace_id

**Check**:

1. Logging configured: `configure_logging()` called
2. TraceContextFilter added to logger
3. Using structured logging format

---

## 📚 Additional Resources

- **Main Documentation**: `docs/guides/opentelemetry-integration.md`
- **Framework Analysis**: `docs/guides/otel-framework-integration-analysis.md`
- **Progress Tracking**: `OTEL_PROGRESS.md`
- **Complete Summary**: `OTEL_FRAMEWORK_COMPLETE.md`

### External Documentation

- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- Grafana Tempo: https://grafana.com/docs/tempo/
- Prometheus: https://prometheus.io/docs/
- Grafana Loki: https://grafana.com/docs/loki/

---

## ✅ Quick Checklist

**Framework Setup** (Already Complete):

- ✅ Dependencies installed
- ✅ Infrastructure configured
- ✅ Middleware created

**Application Integration** (Your Tasks):

- [ ] Call `configure_opentelemetry()` in main.py
- [ ] Register `TracingPipelineBehavior`
- [ ] Mix `TracedRepositoryMixin` into repositories
- [ ] (Optional) Add business attributes to spans
- [ ] (Optional) Define and record business metrics
- [ ] Test trace flow in Grafana

---

**Need Help?** Check the comprehensive documentation in `docs/guides/opentelemetry-integration.md`

**Quick Start Time**: ~15 minutes to complete application integration 🚀
