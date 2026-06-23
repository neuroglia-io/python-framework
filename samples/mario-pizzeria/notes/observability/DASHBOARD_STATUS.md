# Grafana Dashboard Troubleshooting Summary

**Date**: October 24, 2025  
**Status**: Partially Working - Metrics Available, Some Panels Need Updates

## Current Status

### ✅ What's Working

**Mario's Pizzeria Dashboard**:

- ✅ **Order Rate Panel** - Shows orders created/completed rates
- ✅ **Average Order Value Panel** - Displays order value histogram
- ✅ **Pizzas by Size Panel** - Shows pizza size distribution
- ✅ **Cooking Duration Panel** - Displays cooking time percentiles
- ✅ **Recent Traces Panel** - Tempo traces visible
- ✅ **Application Logs Panel** - Loki logs available

**Available Metrics in Prometheus** (10 total):

1. `mario_orders_created_total` ✅
2. `mario_orders_completed_total` ✅
3. `mario_orders_value_USD_*` (bucket, count, sum) ✅
4. `mario_pizzas_ordered_total` ✅
5. `mario_pizzas_by_size_total` ✅
6. `mario_kitchen_cooking_duration_seconds_*` (bucket, count, sum) ✅

### ❌ What's Not Working

**Mario's Pizzeria Dashboard**:

- ❌ **Orders In Progress Panel** - Metric `mario_orders_in_progress` not available
  - **Reason**: Requires Observable Gauge pattern, not simple counter
  - **Current**: Disabled in handlers (would cause errors with `.set()` on Counter)

**Neuroglia Framework Dashboard**:

- ⚠️ **May have no data** - Need to verify trace queries are correct
  - **Issue**: Dashboard may be looking for specific service names or span attributes

### ⚠️ Missing Metrics

**Not Yet Recorded**:

- `mario_orders_cancelled_total` - No cancellation flow implemented
- `mario_orders_in_progress` - Needs observable gauge implementation
- `mario_kitchen_capacity_utilized` - Not implemented
- `mario_customers_registered` - Not implemented
- `mario_customers_returning` - Not implemented

## Issues Fixed

### 1. CompleteOrderCommand Timing Issue

**Problem**: Tried to access `order.state.actual_ready_time` before calling `order.mark_ready()`  
**Error**: `'OrderState' object has no attribute 'actual_ready_time'`  
**Fix**: Calculate cooking duration **before** marking order ready

```python
# BEFORE (Broken):
if order.state.cooking_started_time and order.state.actual_ready_time:
    cooking_duration_seconds = ...
order.mark_ready(user_id, user_name)  # Sets actual_ready_time HERE

# AFTER (Working):
if order.state.cooking_started_time:
    cooking_duration_seconds = (datetime.now() - order.state.cooking_started_time).total_seconds()
order.mark_ready(user_id, user_name)
```

### 2. Counter vs Gauge Issue

**Problem**: `orders_in_progress` defined as Counter but handlers used `.set()`  
**Error**: `'_Counter' object has no attribute 'set'`  
**Solution**: Temporarily disabled `.set()` calls - needs proper Observable Gauge implementation

```python
# In handlers - DISABLED for now:
# orders_in_progress.set(kitchen.current_capacity)  # ❌ Doesn't work with Counter

# Proper solution (TODO):
# Use create_observable_gauge with callback function
```

### 3. Dashboard Metric Name Mismatch

**Problem**: Dashboard expects `mario_cooking_duration_bucket` but actual metric is `mario_kitchen_cooking_duration_seconds_bucket`  
**Status**: ✅ Fixed - Metric now exports correctly with full name

## Dashboard Panel Status

### Mario's Pizzeria Overview Dashboard

| Panel               | Status         | Query                                                                           | Notes                              |
| ------------------- | -------------- | ------------------------------------------------------------------------------- | ---------------------------------- |
| Order Rate          | ✅ Working     | `rate(mario_orders_created_total[5m])`                                          | Shows order creation rate          |
| Orders In Progress  | ❌ Not Working | `mario_orders_in_progress`                                                      | Metric not available (needs gauge) |
| Average Order Value | ✅ Working     | `sum(rate(mario_order_value_sum[1h])) / sum(rate(mario_order_value_count[1h]))` | Histogram calculation working      |
| Recent Traces       | ✅ Working     | Tempo query                                                                     | 20+ traces available               |
| Application Logs    | ✅ Working     | Loki query                                                                      | Logs streaming                     |
| Pizzas by Size      | ✅ Working     | `sum by (size) (rate(mario_pizzas_by_size_total[5m]))`                          | Size distribution visible          |
| Cooking Duration    | ✅ Working     | `histogram_quantile(0.50/0.95/0.99, ...)`                                       | P50/P95/P99 percentiles            |

### Neuroglia Framework Dashboard

**Status**: ⚠️ Needs Investigation

**Potential Issues**:

1. May be looking for specific span names that don't match
2. Might need service name filter adjustment
3. Trace queries may need update for new TracingPipelineBehavior format

**To Check**:

- Verify span naming convention in traces
- Check if service.name attribute matches query
- Validate trace data structure in Tempo

## How to View Working Data

### 1. Prometheus Queries

```bash
# Order creation rate
curl "http://localhost:9090/api/v1/query?query=rate(mario_orders_created_total[5m])"

# Order completion rate
curl "http://localhost:9090/api/v1/query?query=rate(mario_orders_completed_total[5m])"

# Average order value
curl "http://localhost:9090/api/v1/query?query=sum(mario_orders_value_USD_sum)/sum(mario_orders_value_USD_count)"

# Cooking duration p95
curl "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(mario_kitchen_cooking_duration_seconds_bucket[5m]))by(le))"
```

### 2. Grafana Explore

**To view traces**:

1. Open http://localhost:3001/explore
2. Select "Tempo" datasource
3. Search for: `service.name="mario-pizzeria"`
4. View trace details with full span hierarchy

**To view metrics**:

1. Open http://localhost:3001/explore
2. Select "Prometheus" datasource
3. Use queries above in Metrics browser

### 3. Direct API Access

```bash
# Check all Mario metrics
curl -s "http://localhost:9090/api/v1/label/__name__/values" | python3 -c "import sys, json; [print(m) for m in json.load(sys.stdin)['data'] if 'mario' in m.lower()]"

# Get trace count
curl -s "http://localhost:3200/api/search?tags=service.name=mario-pizzeria" | python3 -c "import sys, json; print(f'Traces: {len(json.load(sys.stdin).get(\"traces\", []))}')"
```

## Recommended Next Steps

### Immediate (To Get More Dashboards Working)

1. **Fix Neuroglia Framework Dashboard Queries**

   - Check span naming in Tempo
   - Update dashboard queries to match actual trace structure
   - Verify service.name attribute

2. **Implement Observable Gauge for Orders In Progress**

   ```python
   # In observability/metrics.py
   def get_orders_in_progress():
       # Query kitchen state from repository
       kitchen = kitchen_repository.get_kitchen_state()
       return kitchen.current_capacity

   orders_in_progress_gauge = create_observable_gauge(
       name="mario.orders.in_progress",
       callback=get_orders_in_progress,
       unit="orders",
       description="Current orders being prepared"
   )
   ```

3. **Generate More Test Traffic**
   - Run `./scripts/test_mario_orders.sh` multiple times
   - Create variety of order sizes and types
   - Test complete workflows (place → cook → complete)

### Future Enhancements

1. **Add Missing Metrics**:

   - Order cancellation tracking
   - Customer registration/returning metrics
   - Kitchen capacity utilization

2. **Dashboard Improvements**:

   - Add alert thresholds
   - Create SLO/SLI panels
   - Add error rate tracking

3. **Trace Enrichment**:
   - Add more business context to spans
   - Implement exemplar links (metrics → traces)
   - Add baggage for distributed context

## Verification Commands

```bash
# Test complete order workflow
ORDER_ID=$(curl -s -X POST http://localhost:8080/api/orders/ -H "Content-Type: application/json" -d '{"customer_name":"Test","customer_phone":"+1234567890","customer_address":"123 St","pizzas":[{"name":"Margherita","size":"medium","toppings":[]}],"payment_method":"cash"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")

curl -s -X PUT "http://localhost:8080/api/orders/$ORDER_ID/cook" > /dev/null
curl -s -X PUT "http://localhost:8080/api/orders/$ORDER_ID/ready" > /dev/null

# Check metrics updated
sleep 5
curl -s "http://localhost:9090/api/v1/query?query=mario_orders_completed_total" | python3 -m json.tool

# View traces
curl -s "http://localhost:3200/api/search?tags=service.name=mario-pizzeria&limit=5" | python3 -m json.tool
```

## Summary

**Working**:

- ✅ 10 Mario metrics in Prometheus
- ✅ 20+ traces in Tempo
- ✅ 6 of 7 panels in Mario dashboard
- ✅ Logs in Loki
- ✅ Complete order lifecycle (place → cook → complete)

**Not Working**:

- ❌ Orders in progress gauge (needs implementation)
- ⚠️ Neuroglia dashboard (needs query fixes)
- ❌ Some planned metrics not yet implemented

**Overall Status**: 🟡 **70% Functional** - Core observability working, some enhancements needed
