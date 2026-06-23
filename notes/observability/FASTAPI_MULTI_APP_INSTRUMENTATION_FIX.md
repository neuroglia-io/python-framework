# FastAPI Multi-Application OpenTelemetry Instrumentation - Critical Fix

**Date**: October 25, 2025
**Issue**: OpenTelemetry duplicate metrics warnings in multi-app architectures
**Status**: ✅ **RESOLVED**
**Impact**: Framework-wide best practice established

## 🚨 Problem Identified

When building applications with multiple mounted FastAPI applications (common pattern in Neuroglia framework), instrumenting each app separately causes OpenTelemetry duplicate metric warnings:

### Problematic Code Pattern (Mario's Pizzeria Example)

```python
# This was causing duplicate metric warnings:
instrument_fastapi_app(app, "main-app")      # ✅ OK
instrument_fastapi_app(api_app, "api-app")   # ❌ Creates duplicate metrics
instrument_fastapi_app(ui_app, "ui-app")     # ❌ Creates duplicate metrics
```

### Error Messages

```
WARNING  opentelemetry.sdk.metrics._internal:209 An instrument with name
http.server.duration, type Histogram, unit ms and description Measures the
duration of inbound HTTP requests. has been created already.

WARNING  opentelemetry.sdk.metrics._internal:209 An instrument with name
http.server.response.size, type Histogram, unit By and description measures
the size of HTTP response messages (compressed). has been created already.

WARNING  opentelemetry.sdk.metrics._internal:209 An instrument with name
http.server.request.size, type Histogram, unit By and description Measures
the size of HTTP request messages (compressed). has been created already.

WARNING  opentelemetry.sdk.metrics._internal:136 An instrument with name
http.server.active_requests, type UpDownCounter, unit {request} and
description Number of active HTTP server requests. has been created already.
```

## ✅ Solution Implemented

### Root Cause Analysis

The OpenTelemetry FastAPI instrumentor creates **global HTTP metrics instruments** that cannot be created multiple times. When multiple FastAPI apps are instrumented, each tries to create the same global metrics, causing conflicts.

### Correct Implementation Pattern

**Key Principle**: Only instrument the main FastAPI app that contains mounted sub-applications.

```python
from neuroglia.observability import configure_opentelemetry, instrument_fastapi_app

# 1. Initialize OpenTelemetry (once per application)
configure_opentelemetry(
    service_name="mario-pizzeria",
    service_version="1.0.0"
)

# 2. Create applications
app = FastAPI(title="Mario's Pizzeria")
api_app = FastAPI(title="API")
ui_app = FastAPI(title="UI")

# 3. Define main app endpoints BEFORE mounting
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 4. Mount sub-applications
app.mount("/api", api_app, name="api")
app.mount("/", ui_app, name="ui")

# 5. ✅ ONLY instrument the main app
instrument_fastapi_app(app, "mario-pizzeria-main")
```

## 🔍 Technical Details

### Why This Works

1. **Request Flow**: All HTTP requests reach the main app first
2. **Middleware Interception**: OpenTelemetry middleware captures requests at the main app level
3. **Sub-App Routing**: Requests are then routed to mounted sub-apps
4. **Complete Coverage**: All endpoints across all apps are instrumented

```
HTTP Request → Main App (instrumented) → Mounted Sub-App → Response
                  ↑
            Metrics captured here
```

### Verification Results

**All endpoints tracked with single instrumentation:**

```bash
# Verified endpoints being tracked:
✅ /health                (main app)
✅ /                      (UI sub-app)
✅ /api/menu/             (API sub-app)
✅ /api/orders/           (API sub-app)
✅ /api/kitchen/status    (API sub-app)
✅ /api/metrics           (API sub-app)
✅ /api/docs              (API sub-app)
```

**HTTP status codes tracked:**

```bash
✅ 200 OK                (successful requests)
✅ 307 Temporary Redirect (FastAPI redirects)
✅ 404 Not Found          (missing endpoints)
✅ 401 Unauthorized       (auth failures)
```

## 📋 Framework Impact & Guidelines

### Updated Framework Best Practices

1. **Single Instrumentation Point**: Only instrument the main FastAPI application
2. **Mount Before Instrument**: Mount all sub-apps before calling `instrument_fastapi_app()`
3. **Health Endpoint Placement**: Define health endpoints on main app before mounting
4. **Service Naming**: Use descriptive, unique names for instrumentation

### Framework Module Updates

**File**: `src/neuroglia/observability/config.py`

- ✅ Existing `instrument_fastapi_app()` function works correctly
- ✅ Built-in duplicate detection via `app._is_otel_instrumented` flag
- ✅ Proper error handling and logging

### Documentation Updates

**File**: `docs/guides/opentelemetry-integration.md`

- ✅ Added comprehensive multi-app instrumentation section
- ✅ Included problem/solution examples
- ✅ Detailed technical explanation
- ✅ Best practices checklist
- ✅ Verification methods

## 🎯 Action Items for Framework Users

### For New Applications

1. Follow the single instrumentation pattern from the start
2. Use the updated documentation as reference
3. Include health endpoints on main app before mounting

### For Existing Applications

1. **Audit Current Implementation**: Check if multiple apps are being instrumented
2. **Remove Redundant Calls**: Only keep `instrument_fastapi_app()` for main app
3. **Verify Coverage**: Ensure all endpoints still appear in metrics
4. **Update Code Comments**: Document the single instrumentation approach

### Integration Checklist

- [ ] ✅ Initialize OpenTelemetry once at startup
- [ ] ✅ Create all FastAPI apps (main + sub-apps)
- [ ] ✅ Define main app endpoints (health, metrics)
- [ ] ✅ Mount all sub-applications to main app
- [ ] ✅ Instrument ONLY the main app
- [ ] ✅ Verify no duplicate metric warnings in logs
- [ ] ✅ Confirm all endpoints appear in `/metrics`
- [ ] ✅ Test trace propagation across all routes

## 🔗 Related Files Modified

### Mario's Pizzeria Sample

**File**: `samples/mario-pizzeria/main.py`

- ✅ Removed duplicate `instrument_fastapi_app()` calls for sub-apps
- ✅ Moved health endpoint definition before sub-app mounting
- ✅ Single instrumentation of main app only

**File**: `samples/mario-pizzeria/README.md`

- ✅ Updated endpoint documentation
- ✅ Added health and metrics endpoint URLs

### Framework Documentation

**File**: `docs/guides/opentelemetry-integration.md`

- ✅ Added comprehensive multi-app instrumentation section
- ✅ Detailed problem/solution examples
- ✅ Technical explanation and best practices

## 📊 Performance Impact

### Before Fix

- ✅ Multiple duplicate metric warnings on startup
- ✅ Unclear which instrumentation was capturing requests
- ✅ Potential metric conflicts and inconsistencies

### After Fix

- ✅ Clean startup with no warnings
- ✅ Single, clear instrumentation point
- ✅ Complete endpoint coverage verified
- ✅ Consistent metric collection across all routes

## 🎓 Lessons Learned

1. **OpenTelemetry Global State**: HTTP instrumentors create global metrics that can't be duplicated
2. **FastAPI Sub-App Routing**: Mounted apps inherit middleware from parent app
3. **Middleware Order Matters**: Instrumentation must happen after mounting for complete coverage
4. **Health Endpoints**: Main app endpoints must be defined before mounting to avoid 404s

## 🔮 Future Considerations

1. **Framework Integration**: Consider adding automatic detection of multi-app scenarios
2. **Documentation**: Keep multi-app patterns documented as applications grow in complexity
3. **Testing**: Include multi-app instrumentation tests in framework test suite
4. **Monitoring**: Monitor for duplicate instrumentation patterns in new applications

---

**Status**: ✅ **Complete and Documented**
**Next Review**: When adding new FastAPI applications or updating OpenTelemetry dependencies
