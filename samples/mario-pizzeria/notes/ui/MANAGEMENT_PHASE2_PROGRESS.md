# Management Dashboard - Phase 2 Implementation (Analytics)

## Progress Summary

**Phase**: 2 - Analytics Dashboard
**Status**: IN PROGRESS
**Date**: October 22, 2025

---

## Completed in This Session

### ✅ Analytics Queries Created

#### 1. GetOrdersTimeseriesQuery

**File**: `application/queries/get_orders_timeseries_query.py`

**Purpose**: Fetch orders timeseries data for trend analysis

**Features**:

- Date range filtering (default: last 30 days)
- Flexible period grouping: `day`, `week`, `month`
- Aggregated metrics per period:
  - `total_orders` - Number of orders
  - `total_revenue` - Total revenue (Decimal → float)
  - `average_order_value` - Average per order
  - `orders_delivered` - Successfully delivered count
  - `orders_cancelled` - Cancelled order count

**DTO**:

```python
@dataclass
class TimeseriesDataPoint:
    period: str  # "YYYY-MM-DD", "YYYY-Wxx", or "YYYY-MM"
    total_orders: int
    total_revenue: float
    average_order_value: float
    orders_delivered: int
    orders_cancelled: int = 0
```

**Usage**:

```python
query = GetOrdersTimeseriesQuery(
    start_date=datetime(2025, 10, 1, tzinfo=timezone.utc),
    end_date=datetime(2025, 10, 22, tzinfo=timezone.utc),
    period="day"  # or "week" or "month"
)
result = await mediator.execute_async(query)
timeseries_data = result.data  # List[TimeseriesDataPoint]
```

#### 2. GetOrdersByPizzaQuery

**File**: `application/queries/get_orders_by_pizza_query.py`

**Purpose**: Analyze pizza popularity and revenue contribution

**Features**:

- Date range filtering
- Top N limit (default: 10)
- Per-pizza metrics:
  - `pizza_name` - Pizza name
  - `total_orders` - Number ordered
  - `total_revenue` - Revenue generated (Decimal → float)
  - `average_price` - Average price per pizza
  - `percentage_of_total` - % of total revenue

**DTO**:

```python
@dataclass
class PizzaAnalytics:
    pizza_name: str
    total_orders: int
    total_revenue: float
    average_price: float
    percentage_of_total: float
```

**Usage**:

```python
query = GetOrdersByPizzaQuery(
    start_date=start,
    end_date=end,
    limit=10  # Top 10 pizzas
)
result = await mediator.execute_async(query)
pizza_analytics = result.data  # List[PizzaAnalytics]
```

### ✅ Query Registration

- Added to `application/queries/__init__.py`
- Auto-discovery enabled for mediator
- All handlers registered for dependency injection

---

## Technical Implementation Details

### Decimal to Float Conversion

All monetary values converted from `Decimal` to `float` to ensure JSON serializability:

```python
# In timeseries query
total_revenue = float(data["revenue"])
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0

# In pizza query
revenue = float(data["revenue"])
percentage = (revenue / total_revenue_float * 100) if total_revenue_float > 0 else 0.0
```

### Date Range Handling

- Default range: Last 30 days
- Timezone-aware datetime objects (UTC)
- Graceful handling of naive datetimes:

```python
if start_date.tzinfo is None:
    start_date = start_date.replace(tzinfo=timezone.utc)
```

### Period Grouping Logic

```python
def _get_period_key(self, dt: datetime, period: PeriodType) -> str:
    if period == "day":
        return dt.strftime("%Y-%m-%d")
    elif period == "week":
        return dt.strftime("%Y-W%V")  # ISO week
    elif period == "month":
        return dt.strftime("%Y-%m")
```

### OrderItem Structure Understanding

Corrected implementation after discovering OrderItem structure:

- `item.name` - Pizza name
- `item.total_price` - Total price (includes base + toppings + size multiplier)
- Each `OrderItem` represents 1 pizza (no quantity field)
- Items are value objects (frozen dataclass)

---

## Next Steps (Remaining Phase 2 Tasks)

### 1. Setup Chart.js and Assets 📊

**Task**: Install Chart.js, create analytics SASS/JS files

**Actions**:

- [ ] Add Chart.js to `ui/package.json` dependencies
- [ ] Create `ui/src/styles/management-analytics.scss`
- [ ] Create `ui/src/scripts/management-analytics.js`
- [ ] Import analytics styles in `main.scss`

**Chart.js Installation**:

```bash
cd samples/mario-pizzeria/ui
npm install chart.js --save
```

### 2. Create Analytics Dashboard Template 📈

**File**: `ui/templates/management/analytics.html`

**Components to Build**:

- Date range selector (today/week/month/custom)
- Time period selector (day/week/month grouping)
- Revenue trends line chart (Chart.js)
- Orders over time line chart (Chart.js)
- Pizza popularity bar chart (Chart.js)
- Top pizzas table with revenue/percentage
- Order status distribution pie chart (future)

**Template Structure**:

```html
{% extends "layouts/base.html" %} {% block head %}
<!-- Analytics styles loaded from management-analytics.scss -->
{% endblock %} {% block content %}
<div class="container-fluid analytics-dashboard">
  <!-- Date Range Controls -->
  <div class="row">
    <div class="col-md-6">
      <select id="dateRange">
        ...
      </select>
    </div>
    <div class="col-md-6">
      <select id="periodType">
        ...
      </select>
    </div>
  </div>

  <!-- Revenue Chart -->
  <div class="row">
    <div class="col-lg-6">
      <canvas id="revenueChart"></canvas>
    </div>
    <div class="col-lg-6">
      <canvas id="ordersChart"></canvas>
    </div>
  </div>

  <!-- Pizza Analytics -->
  <div class="row">
    <div class="col-lg-8">
      <canvas id="pizzaChart"></canvas>
    </div>
    <div class="col-lg-4">
      <table id="pizzaTable">
        ...
      </table>
    </div>
  </div>
</div>

<script type="module" src="/static/dist/scripts/management-analytics.js"></script>
{% endblock %}
```

### 3. Create Analytics Controller Route 🎯

**File**: `ui/controllers/management_controller.py`

**Routes to Add**:

```python
@get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(self, request: Request):
    """Display analytics dashboard"""
    if not self._check_manager_access(request):
        return 403_error

    # Get default timeseries data (last 30 days, by day)
    timeseries_query = GetOrdersTimeseriesQuery()
    timeseries_result = await self.mediator.execute_async(timeseries_query)

    # Get pizza analytics
    pizza_query = GetOrdersByPizzaQuery(limit=10)
    pizza_result = await self.mediator.execute_async(pizza_query)

    return TemplateResponse("management/analytics.html", {
        "timeseries": timeseries_result.data if timeseries_result.is_success else [],
        "pizza_analytics": pizza_result.data if pizza_result.is_success else [],
        ...
    })

@get("/analytics/data")
async def analytics_data(
    self,
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "day"
):
    """AJAX endpoint for analytics data"""
    if not self._check_manager_access(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    # Parse dates
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    # Get timeseries
    timeseries_query = GetOrdersTimeseriesQuery(
        start_date=start,
        end_date=end,
        period=period
    )
    timeseries_result = await self.mediator.execute_async(timeseries_query)

    # Get pizza analytics
    pizza_query = GetOrdersByPizzaQuery(start_date=start, end_date=end, limit=10)
    pizza_result = await self.mediator.execute_async(pizza_query)

    # Convert to JSON-safe format
    data = {
        "timeseries": [
            {
                "period": dp.period,
                "total_orders": dp.total_orders,
                "total_revenue": dp.total_revenue,
                "average_order_value": dp.average_order_value,
                "orders_delivered": dp.orders_delivered,
                "orders_cancelled": dp.orders_cancelled,
            }
            for dp in (timeseries_result.data if timeseries_result.is_success else [])
        ],
        "pizza_analytics": [
            {
                "pizza_name": pa.pizza_name,
                "total_orders": pa.total_orders,
                "total_revenue": pa.total_revenue,
                "average_price": pa.average_price,
                "percentage_of_total": pa.percentage_of_total,
            }
            for pa in (pizza_result.data if pizza_result.is_success else [])
        ],
    }

    # Safety net for any Decimal objects
    data = convert_decimal_to_float(data)

    return JSONResponse(content=data)
```

### 4. Create Analytics JavaScript 📱

**File**: `ui/src/scripts/management-analytics.js`

**Responsibilities**:

- Initialize Chart.js charts
- Handle date range selection
- Fetch data via AJAX (`/management/analytics/data`)
- Update charts dynamically
- Handle period type changes

**Implementation Outline**:

```javascript
import Chart from 'chart.js/auto';

class ManagementAnalytics {
  constructor() {
    this.charts = {};
    this.currentDateRange = 'month';
    this.currentPeriod = 'day';
  }

  async init() {
    this.setupCharts();
    this.setupEventListeners();
    await this.loadData();
  }

  setupCharts() {
    // Revenue chart
    this.charts.revenue = new Chart(
      document.getElementById('revenueChart'),
      {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: { responsive: true, ... }
      }
    );

    // Orders chart
    this.charts.orders = new Chart(
      document.getElementById('ordersChart'),
      {
        type: 'line',
        ...
      }
    );

    // Pizza chart
    this.charts.pizza = new Chart(
      document.getElementById('pizzaChart'),
      {
        type: 'bar',
        ...
      }
    );
  }

  async loadData() {
    const params = new URLSearchParams({
      date_range: this.currentDateRange,
      period: this.currentPeriod
    });

    const response = await fetch(`/management/analytics/data?${params}`);
    const data = await response.json();

    this.updateCharts(data);
  }

  updateCharts(data) {
    // Update revenue chart
    this.charts.revenue.data.labels = data.timeseries.map(d => d.period);
    this.charts.revenue.data.datasets[0].data = data.timeseries.map(d => d.total_revenue);
    this.charts.revenue.update();

    // Update pizza chart
    this.charts.pizza.data.labels = data.pizza_analytics.map(p => p.pizza_name);
    this.charts.pizza.data.datasets[0].data = data.pizza_analytics.map(p => p.total_revenue);
    this.charts.pizza.update();

    // ... etc
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const analytics = new ManagementAnalytics();
  analytics.init();
});
```

### 5. Create Analytics Styles 🎨

**File**: `ui/src/styles/management-analytics.scss`

**Components**:

```scss
.analytics-dashboard {
  .date-range-selector {
    margin-bottom: 2rem;
  }

  .chart-container {
    position: relative;
    height: 400px;
    margin-bottom: 2rem;
  }

  .analytics-card {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .pizza-table {
    width: 100%;

    th {
      background: #f8f9fa;
      font-weight: 600;
    }

    .percentage-bar {
      background: linear-gradient(90deg, #007bff 0%, #0056b3 100%);
      height: 20px;
      border-radius: 4px;
    }
  }
}
```

---

## Testing Plan

### Unit Tests

- [ ] Test `GetOrdersTimeseriesHandler` with different periods
- [ ] Test `GetOrdersByPizzaHandler` with various date ranges
- [ ] Verify Decimal to float conversions
- [ ] Test period key generation (day/week/month)

### Integration Tests

- [ ] Test analytics controller routes
- [ ] Test AJAX data endpoint
- [ ] Verify JSON serialization (no Decimal errors)
- [ ] Test with empty data sets

### UI Tests

- [ ] Verify charts render correctly
- [ ] Test date range selector
- [ ] Test period type switcher
- [ ] Verify data updates on selection change
- [ ] Test responsive design (mobile/tablet/desktop)

---

## Performance Considerations

### Current Implementation

- Loads ALL orders, filters in memory
- Suitable for small to medium datasets (<10K orders)

### Future Optimization (Phase 4)

Replace with MongoDB aggregation pipeline:

```python
# Future: Direct aggregation
pipeline = [
    {
        "$match": {
            "state.order_time": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
    },
    {
        "$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m-%d",
                    "date": "$state.order_time"
                }
            },
            "total_orders": {"$sum": 1},
            "total_revenue": {"$sum": "$total_amount"},
        }
    },
    {"$sort": {"_id": 1}}
]

results = await order_collection.aggregate(pipeline).to_list()
```

**Benefits**:

- Database-side aggregation (faster)
- Reduced network transfer
- Scalable to millions of orders

---

## Files Created/Modified

### Created

- ✅ `application/queries/get_orders_timeseries_query.py`
- ✅ `application/queries/get_orders_by_pizza_query.py`
- ⏳ `ui/src/styles/management-analytics.scss` (TODO)
- ⏳ `ui/src/scripts/management-analytics.js` (TODO)
- ⏳ `ui/templates/management/analytics.html` (TODO)

### Modified

- ✅ `application/queries/__init__.py` - Added new query imports

### To Modify

- ⏳ `ui/controllers/management_controller.py` - Add analytics routes
- ⏳ `ui/src/styles/main.scss` - Import analytics styles
- ⏳ `ui/package.json` - Add Chart.js dependency

---

## Documentation

- ✅ This file: Complete Phase 2 progress summary
- ⏳ Update MANAGEMENT_BUILD_GUIDE.md with Phase 2 steps
- ⏳ Create ANALYTICS_IMPLEMENTATION.md with Chart.js examples

---

## Next Immediate Actions

1. **Install Chart.js**: `npm install chart.js --save`
2. **Create analytics SCSS**: Style file for analytics dashboard
3. **Create analytics JS**: Chart initialization and data handling
4. **Create analytics template**: HTML structure with chart canvases
5. **Add controller routes**: Analytics page and data API endpoints
6. **Test end-to-end**: Verify charts display and update correctly

---

**Phase 2 Status**: 40% Complete (2 of 5 major tasks done)
