# Keycloak Configuration and Management

## Overview

Keycloak is configured with **persistent H2 file-based storage** to maintain realm configurations, users, and clients across container restarts. This ensures that you don't lose your authentication setup when restarting services.

## Database Configuration

### Current Setup (Persistent) ✅

```yaml
environment:
  KC_DB: dev-file # H2 file-based database
volumes:
  - keycloak_data:/opt/keycloak/data # Persistent storage
```

The database files are stored in the Docker volume `pyneuro_keycloak_data`, which persists across container restarts and recreations.

### Previous Setup (Non-Persistent) ❌

```yaml
environment:
  KC_DB: dev-mem # In-memory database (lost on restart)
```

## Realm Import

The `pyneuro` realm is automatically imported on first startup from:

```
deployment/keycloak/pyneuro-realm-export.json
```

This includes pre-configured clients:

- `mario-app` - Mario's Pizzeria backend
- `mario-public-app` - Mario's Pizzeria public client
- `pyneuro-public` - Event Player client
- `simple-ui-app` - Simple UI application

1. Open http://localhost:8090/admin
2. Login with `admin` / `admin`
3. Check if `mario-pizzeria` realm appears in the realm dropdown (top-left)

## 🔍 Troubleshooting

### If realm is not imported

1. **Check file exists in container:**

   ```bash
   docker-compose -f docker-compose.mario.yml exec keycloak ls -la /opt/keycloak/data/import/
   ```

2. **Check Keycloak startup logs:**

   ```bash
   docker-compose -f docker-compose.mario.yml logs keycloak | grep -i import
   ```

3. **Manual import (if needed):**

   ```bash
   # Get admin token
   TOKEN=$(curl -X POST 'http://localhost:8090/realms/master/protocol/openid-connect/token' \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d 'username=admin' \
     -d 'password=admin' \
     -d 'grant_type=password' \
     -d 'client_id=admin-cli' | jq -r '.access_token')

   # Import realm
   curl -X POST 'http://localhost:8090/admin/realms' \
     -H 'Authorization: Bearer '"$TOKEN" \
     -H 'Content-Type: application/json' \
     -d @deployment/keycloak/mario-pizzeria-realm-export.json
   ```

## � Authentication Flow Issue Fixed

**Problem**: The original realm export had empty `authenticationFlows: []` but referenced flow names like "browser", "registration", causing this error:

```
ERROR: Cannot invoke "org.keycloak.models.AuthenticationFlowModel.getId()" because "flow" is null
```

**Solution**: Created a minimal realm configuration without problematic flow references. The fixed realm uses Keycloak's default flows instead of custom ones.

## �📋 Expected Realm Configuration

The imported realm includes:

- **Realm Name**: `mario-pizzeria`
- **Display Name**: `Mario's Pizzeria 🍕`
- **Clients**:
  - `mario-app` (confidential client with client secret)
  - `mario-public-app` (public client for frontend)
- **Pre-configured Users**:
  - `customer` / `test` (customer role)
  - `chef` / `test` (chef role)
  - `manager` / `test` (manager + chef roles)

## Management Commands

### Using Makefile

```bash
# Reset Keycloak (delete volume and start fresh)
make keycloak-reset

# Configure realms (disable SSL, import pyneuro realm if needed)
make keycloak-configure

# View Keycloak logs
make keycloak-logs

# Restart Keycloak (preserves data)
make keycloak-restart

# Export current realm configuration
make keycloak-export
```

### Using Script Directly

```bash
# Interactive reset with confirmation
./scripts/keycloak-reset.sh

# Non-interactive reset (for CI/CD)
./scripts/keycloak-reset.sh --yes
```

## When to Reset Keycloak

Reset Keycloak when you need to:

1. **Start from scratch**: Remove all custom configurations and return to the exported realm state
2. **Fix corrupted data**: Resolve database inconsistencies or errors
3. **Test fresh installations**: Verify that realm import works correctly
4. **Update realm configuration**: Apply changes from the realm export file

## Data Persistence

### What Gets Persisted ✅

When using `KC_DB: dev-file`:

- All realms (master and pyneuro)
- All users and credentials
- All clients and their configurations
- SSL/TLS settings
- Role mappings and permissions
- Sessions and tokens (until expiry)

### What Gets Reset ❌

When running `make keycloak-reset`:

- Docker volume is deleted
- All runtime data is lost
- Fresh import from `pyneuro-realm-export.json`
- SSL disabled for local development

## Access Information

After successful setup:

- **Admin Console**: http://localhost:8090/admin
- **Master Realm**: http://localhost:8090/realms/master
- **Pyneuro Realm**: http://localhost:8090/realms/pyneuro
- **JWKS Endpoint**: http://localhost:8090/realms/pyneuro/protocol/openid-connect/certs

Default credentials:

- Username: `admin`
- Password: `admin`
- **Roles**: `customer`, `chef`, `manager`
- **Groups**: `customers`, `staff`, `management`
- **Client Scopes**: Standard OpenID Connect scopes + `mario-pizza` custom scope

## ✅ Success Indicators

**FIXED! ✅** The realm now imports successfully. Look for these messages in the logs:

- `Full importing from file /opt/keycloak/bin/../data/import/mario-pizzeria-realm-export.json`
- `Realm 'mario-pizzeria' imported`
- `Import finished successfully`
- `Keycloak 23.0.3 on JVM... started in 9.056s`
- `mario-pizzeria` realm visible in admin console at http://localhost:8090/admin

## 🧪 Test the Complete Setup

```bash
# Login to admin console
open http://localhost:8090/admin
# Credentials: admin / admin

# Check the realm dropdown (top-left) - should show:
# - master
# - mario-pizzeria

# Switch to mario-pizzeria realm and verify:
# - Users: customer, chef, manager (all with test)
# - Clients: mario-app, mario-public-app
# - Roles: customer, chef, manager
```

## 🎯 What Fixed It

The original realm export had problematic authentication flow references. The solution was creating a **minimal realm configuration** that:

1. ✅ **Uses Keycloak defaults** - no custom authentication flows
2. ✅ **Essential configuration only** - users, roles, clients
3. ✅ **Clean JSON structure** - no circular references or null pointers
4. ✅ **Proper client configuration** - both confidential and public clients
