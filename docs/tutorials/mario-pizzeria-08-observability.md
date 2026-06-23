# Part 8: Observability & Tracing

**Time: 30 minutes** | **Prerequisites: [Part 7](mario-pizzeria-07-auth.md)**

In this tutorial, you'll add observability to your application using OpenTelemetry. You'll learn how Neuroglia provides automatic tracing for CQRS operations and how to add custom instrumentation.

## 🎯 What You'll Learn

- OpenTelemetry basics (traces, spans, metrics)
- Automatic CQRS tracing in Neuroglia
- Custom instrumentation for business operations
- Distributed tracing across services
- Observability stack (Jaeger, Prometheus, Grafana)

## 📊 Understanding Observability

Observability answers: **"What is my system doing right now?"**

### The Three Pillars

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Traces    │  │   Metrics   │  │    Logs     │
├─────────────┤  ├─────────────┤  ├─────────────┤
│ Request flow│  │ Counters    │  │ Event records│
│ Performance │  │ Gauges      │  │ Errors      │
│ Dependencies│  │ Histograms  │  │ Debug info  │
└─────────────┘  └─────────────┘  └─────────────┘
```

**Traces**: Show request flow through services
**Metrics**: Aggregate statistics (requests/sec, latency)
**Logs**: Detailed event records

## 🔍 Automatic CQRS Tracing

Neuroglia **automatically traces** all CQRS operations!

### What You Get For Free

Every command/query execution creates spans:

```
🍕 Place Order Request
├── PlaceOrderCommand (handler execution)
│   ├── MongoCustomerRepository.get_async
│   ├── Order.add_order_item (domain operation)
│   ├── Order.confirm_order (domain operation)
│   ├── MongoOrderRepository.add_async
│   └── Event: OrderConfirmedEvent
└── Response: OrderDto
```

**Automatically captured:**

- Command/query name and type
- Handler execution time
- Repository operations
- Domain events published
- Errors and exceptions

### Enable Observability

In `main.py`:

```python
from neuroglia.observability import Observability

def create_pizzeria_app():
    builder = WebApplicationBuilder()

    # ... other configuration ...

    # Configure observability (BEFORE building app)
    Observability.configure(builder)

    app = builder.build_app_with_lifespan(...)
    return app
```

That's it! All CQRS operations are now traced.

### Environment Configuration

Create `observability/otel-collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true

  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]

    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

## 🎨 Custom Instrumentation

Add custom spans for business operations:

### Step 1: Install OpenTelemetry

```bash
poetry add opentelemetry-api opentelemetry-sdk
poetry add opentelemetry-instrumentation-fastapi
```

### Step 2: Add Custom Spans

```python
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class PlaceOrderCommandHandler(CommandHandler):

    async def handle_async(self, command: PlaceOrderCommand):
        # Add business context to automatic span
        add_span_attributes({
            "order.customer_name": command.customer_name,
            "order.pizza_count": len(command.pizzas),
            "order.payment_method": command.payment_method,
        })

        # Create custom span for business logic
        with tracer.start_as_current_span("calculate_order_total") as span:
            total = self._calculate_total(command.pizzas)
            span.set_attribute("order.total_amount", float(total))

        # Automatic tracing continues...
        order = Order(command.customer_id)
        # ...
```

### Step 3: Trace Repository Operations

Repository operations are automatically traced:

```python
class MongoOrderRepository(MotorRepository):

    async def find_by_status_async(self, status: str):
        # Automatic span: "MongoOrderRepository.find_by_status_async"
        # Captures: status parameter, execution time, result count

        orders = await self.find_async({"status": status})
        return orders
```

**What's traced:**

- Method name and class
- Parameters (customer_id, status, etc.)
- Execution time
- Result count
- Errors/exceptions

## 📈 Custom Metrics

Track business metrics:

### Step 1: Define Metrics

Create `observability/metrics.py`:

```python
"""Business metrics for Mario's Pizzeria"""
from opentelemetry import metrics

meter = metrics.get_meter(__name__)

# Counters
orders_created = meter.create_counter(
    name="mario.orders.created",
    description="Total orders created",
    unit="1"
)

orders_completed = meter.create_counter(
    name="mario.orders.completed",
    description="Total orders completed",
    unit="1"
)

# Histograms
order_value = meter.create_histogram(
    name="mario.order.value",
    description="Order value distribution",
    unit="USD"
)

cooking_time = meter.create_histogram(
    name="mario.cooking.time",
    description="Time to cook orders",
    unit="seconds"
)

# Gauges (via callback)
def get_active_orders():
    # Query database for active count
    return 42

active_orders = meter.create_observable_gauge(
    name="mario.orders.active",
    description="Current active orders",
    callbacks=[lambda options: get_active_orders()],
    unit="1"
)
```

### Step 2: Record Metrics

In handlers:

```python
from observability.metrics import orders_created, order_value

class PlaceOrderCommandHandler(CommandHandler):

    async def handle_async(self, command: PlaceOrderCommand):
        # ... create order ...

        # Record metrics
        orders_created.add(
            1,
            {
                "payment_method": command.payment_method,
                "customer_type": "new" if new_customer else "returning"
            }
        )

        order_value.record(
            float(order.total_amount),
            {"payment_method": command.payment_method}
        )

        return self.created(order_dto)
```

## 🐳 Observability Stack with Docker

Create `docker-compose.observability.yml`:

```yaml
version: "3.8"

services:
  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./observability/otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317" # OTLP gRPC
      - "4318:4318" # OTLP HTTP
      - "8889:8889" # Prometheus metrics

  # Jaeger (Tracing UI)
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686" # Jaeger UI
      - "14250:14250" # Collector
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  # Prometheus (Metrics)
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"

  # Grafana (Dashboards)
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./observability/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./observability/grafana/datasources:/etc/grafana/provisioning/datasources
```

### Start Observability Stack

```bash
# Start services
docker-compose -f docker-compose.observability.yml up -d

# Access UIs
# Jaeger: http://localhost:16686
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

## 🔍 Viewing Traces

### In Jaeger

1. Open http://localhost:16686
2. Select service: `mario-pizzeria`
3. Click "Find Traces"
4. Click on a trace to see:
   - Complete request flow
   - Each handler/repository call
   - Timing breakdown
   - Errors and exceptions

### Example Trace

```
PlaceOrderCommand [200ms]
├─ GetOrCreateCustomer [50ms]
│  └─ MongoCustomerRepository.find_by_phone [45ms]
├─ Order.add_order_item [5ms]
├─ Order.confirm_order [2ms]
├─ MongoOrderRepository.add_async [80ms]
└─ DomainEventDispatch [60ms]
   └─ OrderConfirmedEvent [55ms]
      ├─ SendSMS [30ms]
      └─ NotifyKitchen [20ms]
```

## 📝 Key Takeaways

1. **Automatic Tracing**: Neuroglia traces all CQRS operations
2. **Custom Spans**: Add business context with `add_span_attributes`
3. **Business Metrics**: Track orders, revenue, performance
4. **OpenTelemetry**: Standard observability protocol
5. **Jaeger UI**: Visualize distributed traces
6. **Production Ready**: Export to Datadog, New Relic, etc.

## 🚀 What's Next?

In [Part 9: Deployment](mario-pizzeria-09-deployment.md), you'll learn:

- Docker containerization
- Docker Compose orchestration
- Production configuration
- Scaling considerations

---

**Previous:** [← Part 7: Authentication](mario-pizzeria-07-auth.md) | **Next:** [Part 9: Deployment →](mario-pizzeria-09-deployment.md)
