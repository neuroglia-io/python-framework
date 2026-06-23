# 🚀 Mario's Pizzeria - Quick Start Observability

## 📊 **Dashboard Quick Access**

### **Main Dashboards**

- **📍 Overview**: `/d/mario-pizzeria-overview/` - Business metrics & system health
- **🔍 Distributed Traces**: `/d/mario-traces/` - Trace analysis (table view + Explore links)
- **🚀 HTTP Performance**: `/d/mario-http/` - Request rates, latency, errors
- **💼 Business Operations**: `/d/mario-business/` - Orders, revenue, inventory
- **🏗️ CQRS Performance**: `/d/mario-cqrs/` - Command/Query metrics
- **🎯 Neuroglia Framework**: `/d/neuroglia-framework/` - Framework-specific traces

### **Direct Access**

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Mario's API**: http://localhost:8080

## 🔍 **Trace Analysis - Quick Guide**

### **Method 1: Explore Interface** ⭐ **(Recommended)**

```
1. Go to: http://localhost:3001/explore
2. Select: Tempo datasource
3. Query: {resource.service.name="mario-pizzeria"}
4. Analyze: Full trace timeline and spans
```

### **Method 2: Dashboard Table View**

```
1. Visit any traces dashboard
2. View traces in table format
3. Copy trace IDs for detailed analysis
4. Click "Explore" links for advanced analysis
```

## 📈 **Essential TraceQL Queries**

### **Basic Queries**

```traceql
# All Mario's Pizzeria traces
{resource.service.name="mario-pizzeria"}

# HTTP POST operations (orders)
{resource.service.name="mario-pizzeria" && span.http.method="POST"}

# Slow operations (>100ms)
{resource.service.name="mario-pizzeria" && duration > 100ms}

# Error traces
{resource.service.name="mario-pizzeria" && status=error}

# CQRS operations
{resource.service.name="mario-pizzeria" && name=~".*Command.*|.*Query.*"}
```

### **Advanced Queries**

```traceql
# Order creation workflow
{resource.service.name="mario-pizzeria" && name=~".*CreateOrder.*"}

# Database operations
{resource.service.name="mario-pizzeria" && span.db.system!=""}

# Recent slow operations
{resource.service.name="mario-pizzeria" && duration > 50ms} && start > 15m ago
```

## 📊 **Essential PromQL Queries**

### **Performance Metrics**

```promql
# Request rate (per second)
rate(http_server_requests_total{service_name="mario-pizzeria"}[5m])

# Error rate percentage
(rate(http_server_requests_total{service_name="mario-pizzeria",status_code=~"5.."}[5m]) / rate(http_server_requests_total{service_name="mario-pizzeria"}[5m])) * 100

# Response time P95
histogram_quantile(0.95, rate(http_server_request_duration_seconds_bucket{service_name="mario-pizzeria"}[5m]))

# Active orders
sum(orders_total{status="active"})
```

### **Business Metrics**

```promql
# Total revenue rate
rate(order_total_value_sum[5m])

# Orders per minute
rate(orders_total[1m]) * 60

# Average order value
sum(rate(order_total_value_sum[1h])) / sum(rate(order_total_value_count[1h]))

# Inventory levels
inventory_items{service="mario-pizzeria"}
```

## ⚡ **Troubleshooting Quick Reference**

### **"No data found in response" in Traces Panel**

✅ **Solution**: Use table view or Explore interface
❌ **Cause**: Traces panels only work with single trace IDs

### **TraceQL Query Not Working**

✅ **Fix**: Use `resource.service.name="mario-pizzeria"` (not `service.name`)
✅ **Try**: Explore interface for better error messages
✅ **Check**: Time range includes actual traces

### **Missing Metrics**

✅ **Check**: http://localhost:9090/targets (Prometheus targets)
✅ **Verify**: Mario's service is running on port 8080
✅ **Test**: `curl http://localhost:8080/metrics`

## 🎯 **Monitoring Workflow**

### **Daily Health Check**

1. **Overview Dashboard** → Check business metrics
2. **HTTP Performance** → Verify response times < 500ms
3. **Error Rates** → Ensure < 1%
4. **Trace Analysis** → Sample recent operations

### **Investigation Workflow**

1. **Metrics** → Identify anomaly (high latency, errors)
2. **Traces** → Use TraceQL to find relevant traces
3. **Spans** → Analyze individual operations
4. **Debug** → Use debugpy (port 5678) if needed
5. **Verify** → Confirm fix with metrics/traces

## 🔧 **Performance Notes**

### **Current Optimizations**

- ✅ **OTEL Logging**: Disabled (was causing workstation slowdown)
- ✅ **Traces & Metrics**: Enabled and optimized
- ✅ **Dashboard Refresh**: 30s (balanced load vs. freshness)
- ✅ **Trace Sampling**: Reasonable limits for development

### **Debugging Available**

- **debugpy**: localhost:5678 (remote debugging)
- **Live Reload**: Service auto-restarts on code changes
- **Full Observability**: Metrics + traces active

---

**🎯 Remember**: Use **Explore interface** for trace analysis - it has full TraceQL support and works perfectly!
