# Bug Fixes: Static Files & Keycloak

## Issue 1: Static Files Not Found (404)

### Problem

```
INFO: 185.125.190.81:45920 - "GET /static/dist/scripts/app.js HTTP/1.1" 404 Not Found
INFO: 185.125.190.81:45920 - "GET /static/dist/styles/main.css HTTP/1.1" 404 Not Found
```

### Root Cause

**Path mismatch** between Parcel output and FastAPI static mount:

- **Parcel writes to**: `samples/mario-pizzeria/static/dist/`
- **Python served from**: `samples/mario-pizzeria/ui/static/` ❌

### Investigation

```bash
# Files were being built successfully
docker exec ui-builder find /app -name "app.js"
→ /app/samples/mario-pizzeria/static/dist/scripts/app.js ✅

# But Python was looking in wrong place
Path(__file__).parent / "ui" / "static"  ❌
```

### Solution

**Fixed `main.py`** to point to correct static directory:

```python
# Before (WRONG)
static_directory = Path(__file__).parent / "ui" / "static"

# After (CORRECT)
static_directory = Path(__file__).parent / "static"
```

### Verification

```bash
curl http://localhost:8080/static/dist/scripts/app.js
→ HTTP 200 ✅

curl http://localhost:8080/static/dist/styles/main.css
→ HTTP 200 ✅
```

## Issue 2: Keycloak Configuration Complexity

### Problem

- Keycloak required external PostgreSQL database
- Unnecessary complexity for development
- Additional container and volume management
- User reported HTTPS requirement issues

### Solution

**Simplified to dev-mode with H2 in-memory database:**

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:23.0.3
  command: ["start-dev", "--import-realm"]
  environment:
    KEYCLOAK_ADMIN: admin
    KEYCLOAK_ADMIN_PASSWORD: admin
    KC_HTTP_PORT: 8080
    KC_HOSTNAME_STRICT: false
    KC_HOSTNAME_STRICT_HTTPS: false
    KC_HTTP_ENABLED: true
  volumes:
    - ./deployment/keycloak/mario-pizzeria-realm-export.json:/opt/keycloak/data/import/mario-pizzeria-realm-export.json:ro
```

### Changes

✅ Removed `keycloak-db` service
✅ Removed PostgreSQL dependency
✅ Removed `keycloak_db_data` volume
✅ Removed database environment variables
✅ Added explicit `KC_HTTP_PORT: 8080`
✅ Uses H2 in-memory database (dev-mode default)

### Benefits

- **Simpler**: One less container to manage
- **Faster startup**: No database initialization
- **Cleaner**: Realm import still works from JSON
- **Development-focused**: Perfect for local dev (not production)

## Directory Structure (Final)

```
samples/mario-pizzeria/
├── static/                    # ← Python serves from here
│   └── dist/                  # ← Parcel writes here
│       ├── scripts/
│       │   └── app.js
│       └── styles/
│           └── main.css
├── ui/
│   ├── src/                   # ← Parcel source files
│   │   ├── scripts/
│   │   │   └── app.js
│   │   └── styles/
│   │       └── main.scss
│   ├── static/                # ← OLD (unused now)
│   └── templates/
└── main.py
```

## Commit

- `791b7d2` - Fix static path & simplify Keycloak

## Testing Checklist

✅ Homepage loads at `http://localhost:8080/`
✅ CSS loads (`/static/dist/styles/main.css`)
✅ JS loads (`/static/dist/scripts/app.js`)
✅ Keycloak starts without PostgreSQL
✅ Keycloak accessible at `http://localhost:8090`
✅ No orphaned containers or volumes
