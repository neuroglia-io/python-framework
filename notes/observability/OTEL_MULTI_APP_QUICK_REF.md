# OpenTelemetry Multi-App Instrumentation Quick Reference

> **Critical**: Only instrument the main FastAPI app, never sub-apps!

## ❌ Wrong (Causes duplicate metrics warnings)

```python
instrument_fastapi_app(app, "main-app")
instrument_fastapi_app(api_app, "api-app")    # ⚠️ Duplicate metrics
instrument_fastapi_app(ui_app, "ui-app")      # ⚠️ Duplicate metrics
```

## ✅ Correct (Single instrumentation point)

```python
# 1. Mount sub-apps first
app.mount("/api", api_app, name="api")
app.mount("/", ui_app, name="ui")

# 2. Only instrument main app
instrument_fastapi_app(app, "mario-pizzeria-main")
```

## 📊 Verification

All endpoints are captured with single instrumentation:

```bash
curl -s "http://localhost:8080/api/metrics" | \
  grep 'http_target=' | \
  sed 's/.*http_target="\([^"]*\)".*/\1/' | \
  sort | uniq
```

## 📖 Full Documentation

See: `docs/guides/opentelemetry-integration.md` - Section "FastAPI Multi-Application Instrumentation"
