# Management Dashboard Design Document

## Overview

The Management Dashboard provides restaurant managers with comprehensive tools to:

- Monitor real-time operations (kitchen + delivery)
- Manage menu items (add, edit, delete pizzas)
- Analyze business metrics and trends
- View performance statistics across all operations

## Access Control

**Role Required**: `manager`

The manager role provides access to:

- All customer features (menu, orders, profile)
- All chef features (kitchen dashboard)
- All delivery features (delivery dashboard)
- Exclusive management features (analytics, menu editing)

## Dashboard Sections

### 1. Overview Dashboard (`/management`)

**Purpose**: Real-time KPI monitoring and quick insights

**Key Metrics**:

- **Today's Stats**:
  - Total orders (with % change from yesterday)
  - Total revenue (with % change)
  - Average order value
  - Active orders (pending + cooking + ready + delivering)
- **Real-Time Status**:

  - Orders in kitchen (by status: pending, confirmed, cooking, ready)
  - Orders out for delivery (by driver)
  - Average prep time today
  - Average delivery time today

- **Quick Actions**:
  - Link to Kitchen Dashboard
  - Link to Delivery Dashboard
  - Link to Menu Management
  - Link to Analytics

**SSE Updates**: Refresh metrics every 5 seconds

### 2. Menu Management (`/management/menu`)

**Purpose**: CRUD operations for pizza menu items

**Features**:

- **Pizza List**:
  - Display all pizzas with name, sizes, base price, availability
  - Search/filter functionality
  - Sort by name, price, popularity
- **Add New Pizza**:
  - Form: name, description, available sizes, base prices per size
  - Available toppings selection
  - Image URL (optional)
  - Availability toggle (active/inactive)
- **Edit Pizza**:
  - Update all pizza properties
  - Change availability status
  - View order history for this pizza
- **Delete Pizza**:
  - Soft delete (mark as unavailable)
  - Confirmation dialog
  - Warn if pizza has active orders

**Validation**:

- Pizza name must be unique
- At least one size must be available
- Base prices must be positive
- Cannot delete pizzas with active orders

### 3. Operations Monitor (`/management/operations`)

**Purpose**: Unified view of kitchen and delivery operations

**Layout**: Split-screen or tabbed view

**Kitchen Section**:

- Same view as kitchen dashboard
- Orders by status (pending, confirmed, cooking, ready)
- Real-time updates via SSE
- Quick status change buttons

**Delivery Section**:

- All active deliveries across all drivers
- Ready orders waiting for pickup
- Delivery assignments by driver
- Real-time location tracking (future feature)

**Combined Metrics**:

- Total orders in pipeline
- Average time from order to delivery
- Bottleneck identification
- Driver utilization rates

### 4. Analytics Dashboard (`/management/analytics`)

**Purpose**: Business intelligence and trend analysis

**Time Range Selector**: Today, Yesterday, Last 7 days, Last 30 days, Custom range

**Charts and Visualizations**:

#### A. Orders Over Time (Line Chart)

- X-axis: Time (hourly/daily/weekly)
- Y-axis: Number of orders
- Compare with previous period
- Identify peak hours/days

#### B. Revenue Trends (Line Chart)

- X-axis: Time period
- Y-axis: Revenue ($)
- Average order value line
- Revenue by pizza category

#### C. Pizza Popularity (Bar Chart)

- X-axis: Pizza names
- Y-axis: Number of orders
- Sort by most/least popular
- Revenue per pizza

#### D. Order Status Distribution (Pie Chart)

- Completed vs Cancelled
- Success rate percentage
- Cancellation reasons analysis

#### E. Chef Performance (Table + Bar Chart)

- Orders processed per chef
- Average prep time per chef
- Quality ratings (if implemented)
- Efficiency metrics

#### F. Driver Performance (Table + Bar Chart)

- Deliveries completed per driver
- Average delivery time per driver
- Distance traveled
- Customer ratings (if implemented)

#### G. Peak Hours Analysis (Heatmap)

- Day of week vs Hour of day
- Order volume intensity
- Staffing recommendations

**Export Options**:

- Download data as CSV
- Export charts as PNG
- Generate PDF reports (future)

## Data Architecture

### Aggregation Queries

#### GetOrderStatisticsQuery

```python
@dataclass
class GetOrderStatisticsQuery:
    start_date: datetime
    end_date: datetime
    group_by: str = "day"  # hour, day, week, month
```

**Returns**: OrderStatisticsDto with total orders, revenue, avg value, completion rate

#### GetOrdersByChefQuery

```python
@dataclass
class GetOrdersByChefQuery:
    start_date: datetime
    end_date: datetime
```

**Returns**: List[ChefPerformanceDto] with chef_id, order_count, avg_prep_time

#### GetOrdersByDriverQuery

```python
@dataclass
class GetOrdersByDriverQuery:
    start_date: datetime
    end_date: datetime
```

**Returns**: List[DriverPerformanceDto] with driver_id, delivery_count, avg_delivery_time

#### GetOrdersByPizzaQuery

```python
@dataclass
class GetOrdersByPizzaQuery:
    start_date: datetime
    end_date: datetime
```

**Returns**: List[PizzaStatisticsDto] with pizza_name, order_count, revenue

#### GetOrdersTimeseriesQuery

```python
@dataclass
class GetOrdersTimeseriesQuery:
    start_date: datetime
    end_date: datetime
    interval: str = "1h"  # 1h, 1d, 1w, 1M
```

**Returns**: List[TimeseriesDataPoint] with timestamp, order_count, revenue

### MongoDB Aggregation Pipelines

#### Orders by Pizza (Example)

```python
pipeline = [
    {"$match": {"order_time": {"$gte": start_date, "$lte": end_date}}},
    {"$unwind": "$order_items"},
    {"$group": {
        "_id": "$order_items.name",
        "count": {"$sum": 1},
        "revenue": {"$sum": "$order_items.total_price"}
    }},
    {"$sort": {"count": -1}}
]
```

#### Orders Over Time (Example)

```python
pipeline = [
    {"$match": {"order_time": {"$gte": start_date, "$lte": end_date}}},
    {"$group": {
        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_time"}},
        "count": {"$sum": 1},
        "revenue": {"$sum": "$total_amount"}
    }},
    {"$sort": {"_id": 1}}
]
```

## Menu Management Operations

### Commands

#### CreatePizzaCommand

- Validates unique name
- Validates pricing
- Creates pizza in menu repository

#### UpdatePizzaCommand

- Validates pizza exists
- Updates properties
- Handles availability changes

#### DeletePizzaCommand

- Soft delete (marks unavailable)
- Checks for active orders
- Prevents hard delete if referenced

#### UpdatePizzaAvailabilityCommand

- Quick toggle for availability
- Used for 86'ing items temporarily

### Repository Methods

Add to IPizzaRepository:

```python
async def create_pizza_async(self, pizza: Pizza) -> Pizza
async def update_pizza_async(self, pizza: Pizza) -> Pizza
async def delete_pizza_async(self, pizza_id: str) -> bool
async def get_pizza_order_count_async(self, pizza_name: str) -> int
```

## UI Components

### Chart.js Integration

**Library**: Chart.js v4.x
**CDN**: https://cdn.jsdelivr.net/npm/chart.js

**Chart Types Used**:

- Line charts: Trends over time
- Bar charts: Comparisons (pizza, chef, driver stats)
- Pie charts: Distributions (status, categories)
- Doughnut charts: Percentages (completion rate)

**Responsive Design**:

- Charts resize with viewport
- Mobile-friendly data tables
- Collapsible sections on small screens

### Real-Time Updates

**SSE Endpoint**: `/management/stream`

**Update Frequency**: 5 seconds

**Data Sent**:

```json
{
  "overview": {
    "total_orders_today": 45,
    "revenue_today": 1234.50,
    "active_orders": 8,
    "orders_in_kitchen": 3,
    "orders_in_delivery": 5
  },
  "kitchen_orders": [...],
  "delivery_orders": [...]
}
```

## Navigation Updates

### Main Navigation

```html
{% if 'manager' in roles %}
<li class="nav-item">
  <a class="nav-link" href="/management"> <i class="bi bi-speedometer2"></i> Management </a>
</li>
{% endif %}
```

### User Dropdown Menu

```html
{% if 'manager' in roles %}
<li><hr class="dropdown-divider" /></li>
<li class="dropdown-header">Management</li>
<li>
  <a class="dropdown-item" href="/management"> <i class="bi bi-speedometer2"></i> Dashboard </a>
</li>
<li>
  <a class="dropdown-item" href="/management/menu"> <i class="bi bi-card-list"></i> Menu Management </a>
</li>
<li>
  <a class="dropdown-item" href="/management/analytics"> <i class="bi bi-graph-up"></i> Analytics </a>
</li>
{% endif %}
```

## Security Considerations

1. **Role-Based Access**: All management endpoints require `manager` role
2. **Input Validation**: Validate all menu management inputs
3. **Audit Logging**: Log all menu changes (who, what, when)
4. **Data Export Limits**: Prevent excessive data exports
5. **Rate Limiting**: Limit aggregation query frequency

## Performance Considerations

1. **Caching**: Cache aggregation results for 30-60 seconds
2. **Indexes**: Create indexes on order_time, status, chef_id, delivery_person_id
3. **Pagination**: Paginate large result sets
4. **Async Processing**: Run heavy aggregations asynchronously
5. **Query Optimization**: Use MongoDB aggregation pipelines

## Testing Strategy

### Unit Tests

- Test aggregation query builders
- Test menu CRUD commands
- Test access control logic

### Integration Tests

- Test MongoDB aggregation pipelines
- Test chart data generation
- Test SSE streaming

### E2E Tests

- Test complete management workflow
- Test role-based access enforcement
- Test real-time updates

## Implementation Priority

**Phase 1** (MVP):

1. ✅ Design architecture (this document)
2. Create overview dashboard with basic metrics
3. Implement operations monitor (combined kitchen + delivery view)
4. Add management navigation

**Phase 2** (Analytics):

1. Implement aggregation queries
2. Create analytics dashboard with Chart.js
3. Add time range selector
4. Implement export functionality

**Phase 3** (Menu Management):

1. Create menu CRUD commands
2. Implement menu management UI
3. Add validation and error handling
4. Test menu operations

**Phase 4** (Enhancements):

1. Add caching layer
2. Implement audit logging
3. Add advanced filters
4. Performance optimization

## Future Enhancements

1. **Real-time Notifications**: Alert managers of issues
2. **Forecasting**: Predict order volumes
3. **Inventory Management**: Track ingredient usage
4. **Staff Scheduling**: Optimize staffing based on predicted demand
5. **Customer Analytics**: Repeat customer analysis, lifetime value
6. **Financial Reports**: Profit/loss, cost analysis
7. **Mobile App**: Dedicated management mobile interface

## Success Metrics

- Dashboard load time < 2 seconds
- Aggregation queries < 500ms
- SSE updates with < 100ms latency
- Chart rendering < 1 second
- Menu CRUD operations < 300ms

---

**Status**: Design Phase Complete ✅
**Next Step**: Begin Phase 1 implementation
