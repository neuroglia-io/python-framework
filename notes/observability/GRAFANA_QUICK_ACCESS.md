# Grafana Quick Access Guide

## 🎨 Grafana Access

**URL**: http://localhost:3001

**Credentials**:

- Username: `admin`
- Password: `admin`

## 📊 Pre-Configured Dashboards (Automatically Provisioned)

### 1. Mario's Pizzeria - Overview Dashboard

**Direct URL**: http://localhost:3001/d/mario-pizzeria-overview/mario-s-pizzeria-overview

**What it shows**:

- 📈 Order rate (created, completed, cancelled)
- 🔢 Current orders in progress
- 💰 Average order value
- 🍕 Pizzas ordered by size
- ⏱️ Cooking duration percentiles
- 🔍 Recent traces from Tempo
- 📝 Application logs from Loki

**Refresh**: Auto-refreshes every 5 seconds

---

### 2. Neuroglia Framework - CQRS & Tracing

**Direct URL**: http://localhost:3001/d/neuroglia-framework/neuroglia-framework-cqrs-and-tracing

**What it shows**:

- 🎯 Recent command executions (with automatic tracing)
- 🔍 Recent query executions
- 💾 Repository operations (database calls)
- 📋 Framework operation logs (MEDIATOR, Events, Repository)

**Refresh**: Auto-refreshes every 5 seconds

---

## 🔗 Data Sources (Pre-configured)

All dashboards are connected to these data sources:

- **Tempo** (Distributed Tracing): http://tempo:3200
- **Prometheus** (Metrics): http://prometheus:9090
- **Loki** (Logs): http://loki:3100

---

## 🚀 Quick Start

1. **Start all services**:

   ```bash
   ./mario-docker.sh start
   ```

2. **Open Grafana**: http://localhost:3001

3. **First Time Setup**:

   - Login with `admin` / `admin`
   - (Optional) Change password or skip

4. **View Dashboards**:
   - Click "Dashboards" in left sidebar
   - Open "Mario Pizzeria" folder
   - Select either dashboard

---

## 📊 Available Business Metrics

From `samples/mario-pizzeria/observability/metrics.py`:

- `mario_orders_created_total` - Counter of orders created
- `mario_orders_completed_total` - Counter of orders completed
- `mario_orders_cancelled_total` - Counter of orders cancelled
- `mario_orders_in_progress` - Gauge of current orders in progress
- `mario_order_value` - Histogram of order values in USD
- `mario_pizzas_ordered_total` - Counter of pizzas ordered
- `mario_pizzas_by_size_total` - Counter by pizza size
- `mario_kitchen_capacity_utilized` - Histogram of kitchen utilization
- `mario_cooking_duration` - Histogram of cooking duration
- `mario_customers_registered_total` - Counter of new customers
- `mario_customers_returning_total` - Counter of returning customers

---

## 🔍 Trace-to-Log-to-Metric Correlation

The dashboards support automatic correlation:

1. **From Trace → Logs**: Click on trace span → "View Logs" shows related logs
2. **From Logs → Trace**: Click on trace_id in logs → Opens full trace
3. **From Metrics → Trace**: Exemplar support links metrics to traces

---

## 🛠️ Troubleshooting

### No Data in Dashboards

```bash
# Check services
docker compose -f docker-compose.mario.yml ps

# Check OTEL Collector
docker logs mario-pizzeria-otel-collector-1 | tail -20

# Test datasources in Grafana UI:
# Configuration → Data Sources → Test
```

### Dashboards Not Loading

```bash
# Check Grafana logs
docker logs mario-pizzeria-grafana-1 | grep -i dashboard

# Verify files
ls -la deployment/grafana/dashboards/json/
```

---

## 📚 Dashboard Files

Dashboards are automatically provisioned from:

- `deployment/grafana/dashboards/json/mario-pizzeria-overview.json`
- `deployment/grafana/dashboards/json/neuroglia-framework.json`

See `deployment/grafana/dashboards/README.md` for customization guide.
