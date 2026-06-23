# Grafana Dashboards for Mario's Pizzeria

This directory contains pre-configured Grafana dashboards that are automatically provisioned when the Grafana service starts.

## 📊 Available Dashboards

### 1. **Mario's Pizzeria - Overview** (`mario-pizzeria-overview.json`)

Main business metrics dashboard showing:

- **Order Metrics**: Rate of orders created, completed, and cancelled
- **Current Status**: Orders in progress
- **Financial Metrics**: Average order value
- **Pizza Analytics**: Orders by pizza size
- **Performance**: Cooking duration percentiles (p50, p95, p99)
- **Observability**: Recent traces and application logs

**Access**: Grafana Home → Dashboards → Mario Pizzeria folder → Overview

### 2. **Neuroglia Framework - CQRS & Tracing** (`neuroglia-framework.json`)

Framework-level observability dashboard showing:

- **Command Traces**: Recent command executions with automatic tracing
- **Query Traces**: Recent query executions
- **Repository Operations**: Database operations with automatic instrumentation
- **Framework Logs**: MEDIATOR, Repository, and Event logs

**Access**: Grafana Home → Dashboards → Mario Pizzeria folder → Framework

## 🚀 Automatic Provisioning

These dashboards are **automatically loaded** when you start the stack:

```bash
./mario-docker.sh start
# or
docker compose -f docker-compose.mario.yml up -d
```

The dashboards are provisioned through:

- **Configuration**: `deployment/grafana/dashboards/dashboards.yaml`
- **Dashboard Files**: `deployment/grafana/dashboards/json/*.json`
- **Docker Mount**: Volume mapped to `/etc/grafana/provisioning/dashboards/json` in container

## 📝 Configuration Details

### Datasources (Pre-configured)

All dashboards use these datasources (automatically provisioned):

1. **Tempo** (uid: `tempo`) - Distributed tracing

   - URL: `http://tempo:3200`
   - Linked to logs via trace IDs

2. **Prometheus** (uid: `prometheus`) - Metrics

   - URL: `http://prometheus:9090`
   - Default datasource
   - Exemplar links to traces

3. **Loki** (uid: `loki`) - Logs
   - URL: `http://loki:3100`
   - Trace ID extraction from logs

### Update Behavior

- **Interval**: Dashboards refresh every 30 seconds from disk
- **UI Updates**: Allowed (`allowUiUpdates: true`)
- **Deletion**: Allowed (`disableDeletion: false`)
- **Changes**: Any changes made in Grafana UI will be **overwritten** on next reload

## 🎨 Customizing Dashboards

### Option 1: Edit JSON Files (Recommended)

Edit the JSON files directly in `deployment/grafana/dashboards/json/`:

- Changes are picked up automatically within 30 seconds
- Version-controllable
- Applies to all instances

### Option 2: Edit in Grafana UI

1. Open dashboard in Grafana
2. Click gear icon → Settings
3. Make changes
4. **Important**: Export JSON and save to this directory to persist changes

### Creating New Dashboards

1. **Create in Grafana UI**:

   - Create new dashboard
   - Add panels
   - Save

2. **Export JSON**:

   - Dashboard Settings → JSON Model
   - Copy JSON
   - Save to `deployment/grafana/dashboards/json/your-dashboard.json`

3. **Set Required Fields**:

   ```json
   {
     "id": null,  // Important: null for provisioned dashboards
     "uid": "unique-dashboard-id",
     "title": "Your Dashboard Title",
     ...
   }
   ```

## 🔍 Dashboard Metrics Reference

### Business Metrics (from `observability/metrics.py`)

**Order Metrics**:

- `mario_orders_created_total` - Counter of orders created
- `mario_orders_completed_total` - Counter of orders completed
- `mario_orders_cancelled_total` - Counter of orders cancelled
- `mario_orders_in_progress` - Gauge of current orders in progress
- `mario_order_value` - Histogram of order values in USD

**Pizza Metrics**:

- `mario_pizzas_ordered_total` - Counter of pizzas ordered
- `mario_pizzas_by_size_total` - Counter by pizza size (small/medium/large)

**Kitchen Metrics**:

- `mario_kitchen_capacity_utilized` - Histogram of kitchen utilization %
- `mario_cooking_duration` - Histogram of cooking duration in seconds

**Customer Metrics**:

- `mario_customers_registered_total` - Counter of new customers
- `mario_customers_returning_total` - Counter of returning customers

### Framework Traces

All CQRS operations are automatically traced with these attributes:

- `span.operation.type`: `command`, `query`, `event`, or `repository`
- `span.operation.name`: Name of the command/query/event
- `service.name`: `mario-pizzeria`

## 🔗 Trace-to-Log-to-Metric Correlation

The dashboards are configured with automatic correlation:

1. **Traces → Logs**: Click on trace span → "View Logs" shows related logs
2. **Logs → Traces**: Click on trace_id in logs → Opens full trace
3. **Metrics → Traces**: Exemplar support links metrics to traces

## 📖 Access URLs

- **Grafana**: http://localhost:3001
  - Username: `admin`
  - Password: `admin`
- **Prometheus**: http://localhost:9090
- **Tempo**: http://localhost:3200
- **Loki**: http://loki:3100 (internal only)

## 🛠️ Troubleshooting

### Dashboards Not Appearing

1. Check Grafana logs: `docker logs mario-pizzeria-grafana-1`
2. Verify mount: `docker exec mario-pizzeria-grafana-1 ls /etc/grafana/provisioning/dashboards/json`
3. Check provisioning config: `docker exec mario-pizzeria-grafana-1 cat /etc/grafana/provisioning/dashboards/dashboards.yaml`

### No Data in Dashboards

1. Verify services are running: `docker compose -f docker-compose.mario.yml ps`
2. Check OTEL Collector: `docker logs mario-pizzeria-otel-collector-1`
3. Test datasources in Grafana: Configuration → Data Sources → Test

### Dashboards Reset After Changes

This is expected behavior - dashboards are provisioned from JSON files. To persist changes:

1. Export dashboard JSON from Grafana
2. Save to `deployment/grafana/dashboards/json/`
3. Set `id: null` in JSON

## 📚 Additional Resources

- [Grafana Dashboard Documentation](https://grafana.com/docs/grafana/latest/dashboards/)
- [Tempo Query Language (TraceQL)](https://grafana.com/docs/tempo/latest/traceql/)
- [Prometheus Query Language (PromQL)](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [LogQL (Loki)](https://grafana.com/docs/loki/latest/logql/)
