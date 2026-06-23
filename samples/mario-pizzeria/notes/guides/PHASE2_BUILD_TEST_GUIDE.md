# Phase 2 Analytics - Build and Test Guide

## Overview

This guide walks through building and testing the new analytics dashboard feature.

## What Was Built

### Backend (Python)

1. **GetOrdersTimeseriesQuery** - Groups orders by day/week/month with revenue metrics
2. **GetOrdersByPizzaQuery** - Analyzes pizza popularity and revenue contribution
3. **Analytics Routes** - Two new endpoints in UIManagementController:
   - `/management/analytics` - Renders analytics HTML page
   - `/management/analytics/data` - JSON API for dynamic data fetching

### Frontend (TypeScript/JavaScript)

1. **management-analytics.scss** (450 lines) - Complete analytics dashboard styles
2. **management-analytics.js** (600 lines) - Chart.js integration with data fetching
3. **analytics.html** - Analytics dashboard template with charts and tables

### Features Implemented

- 📊 **Revenue Trends Chart** - Line chart showing revenue over time
- 📈 **Order Volume Chart** - Multi-line chart (total/delivered/cancelled)
- 🍕 **Pizza Popularity Chart** - Horizontal bar chart of top pizzas
- 📋 **Pizza Analytics Tables** - Compact and detailed views with percentages
- 🗓️ **Date Range Selector** - Today/Week/Month/Quarter/Year/Custom
- ⏱️ **Period Grouping** - Group data by day/week/month
- 📊 **Summary Statistics** - Total orders, revenue, avg value, delivery rate

---

## Build Process

### Step 1: Install Dependencies

Navigate to the UI directory and install Chart.js:

```bash
cd samples/mario-pizzeria/ui
npm install
```

This will install:

- `chart.js@^4.4.0` - Charting library
- All existing dependencies (bootstrap, parcel, sass)

### Step 2: Build Assets

Build the Parcel bundle including the new analytics files:

```bash
npm run build
```

**Expected Output:**

```
✨ Built in 2.5s

dist/scripts/management-analytics.js    125.4 KB    2.1s
dist/scripts/management-dashboard.js     45.2 KB    1.8s
dist/styles/main.css                     85.7 KB    2.3s
```

**What Gets Built:**

- `ui/static/dist/scripts/management-analytics.js` - Analytics JavaScript bundle
- `ui/static/dist/scripts/management-dashboard.js` - Dashboard JavaScript bundle
- `ui/static/dist/styles/main.css` - Combined CSS (includes analytics styles)

### Step 3: Verify Build Output

Check that files were created:

```bash
ls -lh ../static/dist/scripts/
ls -lh ../static/dist/styles/
```

**Expected Files:**

```
management-analytics.js       # NEW - Analytics JavaScript
management-analytics.js.map   # Source map
management-dashboard.js       # Existing dashboard JavaScript
management-dashboard.js.map   # Source map
main.css                      # Combined CSS with analytics styles
main.css.map                  # Source map
```

### Step 4: Restart Application

Return to project root and restart the application:

```bash
cd ../../..  # Back to pyneuro root
./mario-docker.sh restart
```

**Restart Process:**

1. Stops existing containers
2. Rebuilds Docker image (includes new Python routes)
3. Starts services (app, MongoDB, Keycloak)
4. Waits for health checks

**Expected Output:**

```
Stopping mario-pizzeria...
Rebuilding application image...
Starting services...
✓ MongoDB ready
✓ Keycloak ready
✓ Application ready on http://localhost:8000
```

---

## Testing Guide

### Test 1: Access Analytics Dashboard

**Steps:**

1. Open browser to `http://localhost:8000`
2. Login with test credentials (if not already logged in)
3. Navigate to Management Dashboard (`/management`)
4. Look for "Analytics" link or button
5. Click to navigate to `/management/analytics`

**Expected Result:**

- Analytics page loads successfully
- Charts are visible (may show loading state initially)
- Controls are rendered (date range, period selector)
- Page title: "Sales Analytics"

**Troubleshooting:**

- **404 Error**: Controller route not registered - check app startup logs
- **403 Error**: User doesn't have "manager" role - check Keycloak roles
- **Blank page**: JavaScript error - check browser console

### Test 2: Verify Initial Data Load

**Steps:**

1. On analytics page, open browser Developer Tools (F12)
2. Go to Network tab
3. Refresh the page
4. Look for request to `/management/analytics/data?...`

**Expected Result:**

- Request returns 200 OK status
- Response contains JSON with:
  - `timeseries` array with data points
  - `pizza_analytics` array with pizza data
- Charts render with data
- Tables populate with pizza information

**Check Response Format:**

```json
{
  "timeseries": [
    {
      "period": "2025-10-23",
      "total_orders": 45,
      "total_revenue": 1234.56,
      "average_order_value": 27.43,
      "orders_delivered": 40,
      "orders_cancelled": 2
    }
  ],
  "pizza_analytics": [
    {
      "pizza_name": "Margherita",
      "total_orders": 120,
      "total_revenue": 1500.0,
      "average_price": 12.5,
      "percentage_of_total": 25.5
    }
  ]
}
```

**Troubleshooting:**

- **500 Error**: Check server logs for Python exceptions
- **Empty arrays**: No orders in database - create test orders first
- **Decimal error**: Check convert_decimal_to_float is being called

### Test 3: Date Range Selection

**Steps:**

1. Change date range dropdown from "Last 30 Days" to "Last 7 Days"
2. Observe network request in Developer Tools
3. Verify charts update with new data

**Expected Result:**

- New request to `/management/analytics/data` with updated dates
- Charts smoothly update (not full page reload)
- Data reflects 7-day window
- Summary stats update accordingly

**Test All Presets:**

- ✓ Today - Shows only today's data
- ✓ Last 7 Days - Shows past week
- ✓ Last 30 Days - Shows past month (default)
- ✓ Last 90 Days - Shows past quarter
- ✓ Last Year - Shows past year

### Test 4: Period Grouping

**Steps:**

1. Keep date range at "Last 30 Days"
2. Change period from "Daily" to "Weekly"
3. Observe chart X-axis labels change

**Expected Result:**

- Chart labels change from dates (2025-10-23) to weeks (2025-W43)
- Data aggregated by week
- Fewer data points on chart (4-5 weeks vs 30 days)

**Test All Periods:**

- ✓ Daily - Date format: YYYY-MM-DD
- ✓ Weekly - Date format: YYYY-Wxx (ISO week)
- ✓ Monthly - Date format: YYYY-MM

### Test 5: Custom Date Range

**Steps:**

1. Select "Custom Range" from date range dropdown
2. Date inputs appear
3. Select start date (e.g., October 1, 2025)
4. Select end date (e.g., October 15, 2025)
5. Click "Apply Filters" button

**Expected Result:**

- Custom date inputs become visible
- Apply button is enabled
- After clicking, charts update with custom date range
- Data reflects only orders between selected dates

**Edge Cases to Test:**

- ✓ Same start and end date - Should show one day
- ✓ Start date after end date - Should handle gracefully
- ✓ Future dates - Should show empty state

### Test 6: Chart Interactions

**Steps:**

1. Hover over data points on charts
2. Check tooltip appears with values
3. Verify legend items (Orders, Delivered, Cancelled)
4. Try clicking legend items to toggle datasets

**Expected Result:**

- **Revenue Chart**: Shows revenue amount with $ formatting
- **Orders Chart**: Shows counts for total/delivered/cancelled
- **Pizza Chart**: Shows pizza name and revenue
- Tooltips are readable and accurate
- Legend items can toggle visibility (if Chart.js feature enabled)

### Test 7: Pizza Analytics Tables

**Steps:**

1. Scroll to "Top Pizzas" table (right side)
2. Verify top 5 pizzas by revenue
3. Scroll to "Detailed Pizza Analytics" table (bottom)
4. Verify all pizzas listed with percentages

**Expected Result:**

- **Compact Table**: Shows rank, name, orders, revenue (top 5)
- **Detailed Table**: Shows rank, name, orders, revenue, avg price, percentage
- **Percentage Bars**: Visual bars scale with percentage value
- **Sorting**: Pizzas sorted by revenue (highest first)
- **Formatting**: Currency formatted as $XX.XX, percentages as XX.X%

### Test 8: Summary Statistics

**Steps:**

1. Look at summary stats boxes at top of page
2. Verify calculations match chart data
3. Change date range and verify stats update

**Expected Result:**

- **Total Orders**: Sum of all orders in period
- **Total Revenue**: Sum of all revenue in period
- **Avg Order Value**: Total revenue / total orders
- **Orders Delivered**: Count of delivered orders
- Stats update when date range changes
- Values match aggregated chart data

### Test 9: Responsive Design

**Steps:**

1. Resize browser window to mobile width (< 768px)
2. Verify layout adjusts properly
3. Test on tablet width (768px - 1200px)

**Expected Result:**

- **Mobile**: Charts stack vertically, controls full-width
- **Tablet**: Two-column layout where appropriate
- **Desktop**: Full multi-column layout
- Charts resize smoothly without distortion
- Tables remain readable (may scroll horizontally)

### Test 10: Error Handling

**Steps:**

1. Simulate network error (disconnect network, then try to load data)
2. Verify error message appears
3. Try invalid date range (end before start)

**Expected Result:**

- **Network Error**: Red error alert appears at top-right
- **Error Message**: Clear description of what went wrong
- **Auto-dismiss**: Alert disappears after 5 seconds
- **Graceful Degradation**: Existing data remains visible
- **Invalid Dates**: API returns 400 error with helpful message

---

## Verification Checklist

### Backend ✓

- [ ] GetOrdersTimeseriesQuery returns correct data structure
- [ ] GetOrdersByPizzaQuery returns correct data structure
- [ ] `/management/analytics` route renders template successfully
- [ ] `/management/analytics/data` API returns valid JSON
- [ ] Decimal values converted to float (no serialization errors)
- [ ] Timezone-aware dates handled properly
- [ ] Error handling works (try-catch blocks)
- [ ] Logging statements present for debugging

### Frontend ✓

- [ ] Chart.js installed and imported correctly
- [ ] All three charts render properly
- [ ] Date range selector works for all presets
- [ ] Period grouping updates charts correctly
- [ ] Custom date range input and apply button work
- [ ] AJAX requests send correct parameters
- [ ] Response data updates charts and tables
- [ ] Summary stats calculate correctly
- [ ] Loading states shown during data fetch
- [ ] Error alerts appear on failures

### Styling ✓

- [ ] Analytics styles load from compiled CSS
- [ ] Charts have proper heights and spacing
- [ ] Tables are readable and well-formatted
- [ ] Percentage bars display correctly
- [ ] Responsive breakpoints work
- [ ] Colors match design (gradients, stat colors)
- [ ] Hover effects work on interactive elements
- [ ] Print styles hide unnecessary elements

### Integration ✓

- [ ] No console errors in browser
- [ ] No Python exceptions in server logs
- [ ] SSE stream still works on dashboard page
- [ ] Navigation between dashboard and analytics works
- [ ] Authentication required (403 without manager role)
- [ ] Session persists across page navigation

---

## Performance Checks

### Initial Page Load

- **Target**: < 2 seconds
- **Check**: Network tab shows page load time
- **Optimize**: Enable caching headers, minify assets

### Data Fetch (AJAX)

- **Target**: < 1 second for 30 days of data
- **Check**: Network tab shows request duration
- **Optimize**: Add database indexes, implement caching

### Chart Rendering

- **Target**: < 500ms to update charts
- **Check**: No visible lag when changing filters
- **Optimize**: Limit data points, use Chart.js animations sparingly

### Memory Usage

- **Target**: No memory leaks after multiple filter changes
- **Check**: Browser Memory Profiler shows stable memory
- **Optimize**: Destroy old chart instances before recreating

---

## Common Issues and Solutions

### Issue: Charts Don't Appear

**Symptoms:**

- Canvas elements visible but no charts
- Console error: "Cannot read property 'getContext' of null"

**Solutions:**

1. Check Chart.js imported: `import Chart from 'chart.js/auto';`
2. Verify canvas IDs match JavaScript: `getElementById('revenueChart')`
3. Check Parcel build output includes Chart.js bundle
4. Ensure JavaScript loads after DOM ready

### Issue: No Data in Charts

**Symptoms:**

- Charts render but show empty datasets
- API returns empty arrays

**Solutions:**

1. Create test orders in database
2. Check date range isn't too narrow (e.g., "Today" with no orders today)
3. Verify query filters aren't too restrictive
4. Check server logs for query errors

### Issue: Decimal Serialization Errors

**Symptoms:**

- API returns 500 error
- Server logs: "Object of type Decimal is not JSON serializable"

**Solutions:**

1. Verify `convert_decimal_to_float()` is called on response data
2. Check all revenue/price fields explicitly converted to float
3. Add safety net conversion before JSONResponse

### Issue: Date Range Doesn't Update

**Symptoms:**

- Changing date range doesn't trigger new data fetch
- Old data remains on screen

**Solutions:**

1. Check event listener on date range select element
2. Verify `loadData()` method called on change
3. Check browser console for JavaScript errors
4. Ensure async/await properly handled

---

## Next Steps After Testing

Once all tests pass:

1. **Document Issues** - Note any bugs or improvements needed
2. **Performance Tuning** - Optimize slow queries or rendering
3. **Add Features** - Implement additional analytics queries (chef/driver performance)
4. **User Feedback** - Get manager role users to test and provide feedback
5. **Production Deployment** - Prepare for production release

---

## Rollback Plan

If critical issues found:

### Quick Rollback (Hide Feature)

```python
# In management_controller.py
@get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(self, request: Request):
    return request.app.state.templates.TemplateResponse(
        "errors/503.html",
        {"request": request, "message": "Analytics temporarily unavailable"},
        status_code=503
    )
```

### Full Rollback (Remove Feature)

```bash
# Revert to previous commit
git revert <commit-hash>

# Rebuild and restart
cd samples/mario-pizzeria/ui
npm run build
cd ../../..
./mario-docker.sh restart
```

---

## Success Criteria

Phase 2 Analytics is **complete** when:

- ✅ All 10 test scenarios pass
- ✅ No console errors or server exceptions
- ✅ Charts render correctly with real data
- ✅ Date range and period filters work
- ✅ Tables populate with accurate data
- ✅ Responsive design works on mobile/tablet/desktop
- ✅ Performance meets targets (< 2s page load, < 1s data fetch)
- ✅ Error handling works gracefully
- ✅ Documentation updated with new features

**Phase 2 Status**: Ready for testing 🚀
