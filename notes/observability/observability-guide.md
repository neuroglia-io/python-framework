# 🔍 Mario's Pizzeria - Observability Guide

## 📊 Current Observability Stack Status

### ✅ **What's Working**

- **Mario's Pizzeria Service**: Running with full instrumentation
- **Prometheus Metrics**: HTTP request rates, CQRS operations, business metrics
- **Distributed Tracing**: OTEL → Tempo → Grafana pipeline operational
- **Grafana Dashboards**: Multiple dashboards with proper configuration
- **Performance**: Workstation responsive (logging collection disabled)
- **Debugging**: debugpy available on port 5678

### 🎯 **Key Discovery: Traces Panel Limitation**

**Important Finding** (from [Grafana Issue #100166](https://github.com/grafana/grafana/issues/100166)):

> _"To the contrary of the 'Table view', the traces panel will only render for a single trace."_ - @grafakus (Grafana contributor)

**This means:**

- ✅ **Table View**: Shows multiple traces from TraceQL search queries
- ✅ **Explore Interface**: Full TraceQL functionality for analysis
- ❌ **Traces Panel**: Only works with specific trace IDs (single trace viewing)

## 🛠️ **How to Use the Observability Stack**

### 🔍 **Distributed Tracing Analysis**

#### **1. Primary Method: Explore Interface** ⭐

**Best for: Advanced analysis, debugging, service mapping**

```
URL: http://localhost:3001/explore
Datasource: Tempo
Query Type: TraceQL
```

**Features Available:**

- Full TraceQL query support
- Detailed trace timelines and span analysis
- Service dependency mapping
- Trace-to-metrics correlation
- Advanced filtering and search

#### **2. Dashboard Table View**

**Best for: Overview, trace listing, quick access**

**Dashboards:**

- **Main**: `/d/mario-traces/` - Comprehensive traces dashboard
- **Working**: `/d/mario-traces-working/` - Simplified table view
- **Status**: `/d/mario-traces-status/` - Status information

**Features:**

- Multiple traces in table format
- Filtering and sorting
- Direct links to Explore interface
- Trace ID copying for detailed analysis

#### **3. Individual Trace Analysis**

**Best for: Single trace deep-dive**

1. Copy trace ID from table view
2. Use trace ID in Explore interface
3. Or create traces panel with specific trace ID

### 📈 **Metrics Analysis**

#### **Prometheus Metrics via Grafana**

```
URL: http://localhost:3001
Datasource: Prometheus
Query Language: PromQL
```

**Available Dashboards:**

- **Business Operations**: `/d/mario-business/` - Orders, revenue, inventory
- **HTTP Performance**: `/d/mario-http/` - Request rates, response times, errors
- **CQRS Performance**: `/d/mario-cqrs/` - Command/query metrics
- **System Infrastructure**: `/d/system-infra/` - Container and system metrics

## 📚 **TraceQL Cheat Sheet**

### **Basic Syntax**

```traceql
# Find all traces for a service
{resource.service.name="mario-pizzeria"}

# Filter by span attributes
{resource.service.name="mario-pizzeria" && span.http.method="POST"}

# Filter by operation name
{resource.service.name="mario-pizzeria" && name="CreateOrderCommand"}

# Regex matching
{resource.service.name="mario-pizzeria" && name=~".*Command.*|.*Query.*"}
```

### **Advanced Filtering**

```traceql
# Duration filtering (nanoseconds)
{resource.service.name="mario-pizzeria" && duration > 100ms}

# Status filtering
{resource.service.name="mario-pizzeria" && status=error}

# Custom attributes
{resource.service.name="mario-pizzeria" && span.custom.order_id="12345"}

# Multiple conditions
{
  resource.service.name="mario-pizzeria" &&
  span.http.method="POST" &&
  duration > 50ms &&
  status=ok
}
```

### **Span Selection**

```traceql
# Select specific spans within traces
{resource.service.name="mario-pizzeria"} | select(span.http.method="POST")

# Aggregate operations
{resource.service.name="mario-pizzeria"} | count() by (name)

# Rate calculations
{resource.service.name="mario-pizzeria"} | rate() by (resource.service.name)
```

### **Common Use Cases**

```traceql
# Find slow operations
{duration > 1s}

# Find errors
{status=error}

# Find database operations
{span.db.system!=""}

# Find HTTP errors
{span.http.status_code >= 400}

# CQRS operations
{name=~".*Command.*|.*Query.*Handler"}

# Recent traces only
{resource.service.name="mario-pizzeria"} && start > 15m ago
```

## 📊 **PromQL Cheat Sheet**

### **Basic Syntax**

```promql
# Instant vector (current value)
http_requests_total

# Rate calculation (per second)
rate(http_requests_total[5m])

# Increase over time
increase(http_requests_total[1h])

# Average over time
avg_over_time(response_time[5m])
```

### **Filtering and Labels**

```promql
# Filter by labels
http_requests_total{service="mario-pizzeria"}

# Multiple label filters
http_requests_total{service="mario-pizzeria", method="POST"}

# Regex matching
http_requests_total{endpoint=~"/api/orders.*"}

# Negative matching
http_requests_total{status_code!="200"}
```

### **Aggregation Functions**

```promql
# Sum by label
sum(http_requests_total) by (service)

# Average by service
avg(response_time) by (service)

# Maximum value
max(memory_usage) by (instance)

# Count of series
count(up) by (job)

# Percentiles
histogram_quantile(0.95, rate(response_time_bucket[5m]))
```

### **Mario's Pizzeria Specific Queries**

```promql
# HTTP request rate
rate(http_server_requests_total{service_name="mario-pizzeria"}[5m])

# Error rate
rate(http_server_requests_total{service_name="mario-pizzeria", status_code=~"4..|5.."}[5m])

# Response time percentiles
histogram_quantile(0.95, rate(http_server_request_duration_seconds_bucket{service_name="mario-pizzeria"}[5m]))

# CQRS command rate
rate(cqrs_commands_total{service="mario-pizzeria"}[5m])

# Business metrics
sum(order_total_value) by (status)

# Inventory levels
inventory_items{service="mario-pizzeria"}

# Active orders
sum(orders_total{status="active"})
```

### **Common Calculations**

```promql
# Success rate (percentage)
(
  rate(http_requests_total{status_code="200"}[5m]) /
  rate(http_requests_total[5m])
) * 100

# Error budget (SLI/SLO monitoring)
1 - (
  rate(http_requests_total{status_code=~"5.."}[30d]) /
  rate(http_requests_total[30d])
)

# Apdex score
(
  sum(rate(response_time_bucket{le="0.1"}[5m])) +
  sum(rate(response_time_bucket{le="0.3"}[5m]))
) / (2 * sum(rate(response_time_count[5m])))
```

## 🚀 **Quick Start Guide**

### **1. Trace Analysis Workflow**

1. **Overview**: Visit main dashboard `/d/mario-traces/`
2. **Explore**: Click "🔍 Explore Traces" for detailed analysis
3. **Filter**: Use TraceQL queries to find specific traces
4. **Deep-dive**: Click individual traces for span details
5. **Correlate**: Use trace-to-metrics correlation features

### **2. Performance Monitoring**

1. **HTTP Metrics**: Visit `/d/mario-http/` dashboard
2. **Business Metrics**: Visit `/d/mario-business/` dashboard
3. **Alerts**: Set up alerts on key SLIs (response time, error rate)
4. **Trends**: Use longer time ranges to identify patterns

### **3. Debugging Workflow**

1. **Identify Issue**: Use metrics dashboards to spot anomalies
2. **Find Traces**: Use TraceQL to find relevant traces
3. **Analyze Spans**: Examine individual spans for errors/latency
4. **Debug Code**: Use debugpy (port 5678) for live debugging
5. **Verify Fix**: Monitor metrics and traces for improvement

## 🔧 **Configuration & Troubleshooting**

### **Service Endpoints**

- **Mario's Pizzeria API**: http://localhost:8080
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Tempo API**: http://localhost:3200
- **debugpy**: localhost:5678

### **Common Issues & Solutions**

#### **"No data found in response" in Traces Panel**

- **Cause**: Traces panels only work with single trace IDs
- **Solution**: Use table view or Explore interface instead

#### **TraceQL Query Not Working**

- **Check**: Verify service name: `resource.service.name="mario-pizzeria"`
- **Check**: Ensure traces exist in time range
- **Try**: Use Explore interface for better error messages

#### **Metrics Missing**

- **Check**: Prometheus targets at http://localhost:9090/targets
- **Check**: Service is running and exposing metrics on /metrics
- **Check**: Firewall/network connectivity

### **Performance Optimization Notes**

- ✅ **OTEL Logging**: Disabled for performance (was causing workstation slowdown)
- ✅ **Metrics Collection**: Enabled and optimized
- ✅ **Trace Collection**: Enabled with reasonable sampling
- ✅ **Dashboard Refresh**: Set to 30s to balance freshness vs. load

## 📈 **Monitoring Best Practices**

### **SLIs (Service Level Indicators)**

```promql
# Availability
sum(rate(http_requests_total{status_code!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Latency (P95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error Rate
sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Throughput
sum(rate(http_requests_total[5m]))
```

### **Alert Thresholds**

- **Error Rate**: > 1% for 2 minutes
- **Response Time P95**: > 500ms for 5 minutes
- **Availability**: < 99.9% for 1 minute
- **Throughput**: Significant deviation from baseline

### **Dashboard Organization**

1. **Executive**: High-level business metrics
2. **Operational**: SLI/SLO monitoring
3. **Diagnostic**: Detailed performance metrics
4. **Debugging**: Traces and detailed spans

---

## 🎯 **Next Steps**

1. **Explore Interface**: Start using TraceQL queries in Explore
2. **Custom Dashboards**: Create team-specific dashboards
3. **Alerting**: Set up Grafana alerts on key metrics
4. **Documentation**: Add team-specific TraceQL/PromQL queries
5. **Integration**: Connect traces to business metrics for correlation

**Remember**: The observability stack is fully operational - use Explore interface for traces and dashboard table views for overview!
