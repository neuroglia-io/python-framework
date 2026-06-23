# Keycloak Configuration Guide - Index

## Current Active Documentation

### 1. **KEYCLOAK_PERSISTENCE_STRATEGY.md** ⭐ PRIMARY

Complete guide on persisting Keycloak configuration across container restarts.

**Topics Covered:**

- Named volume for H2 database (recommended)
- Startup script approach
- Custom Docker entrypoint
- PostgreSQL backend for production
- Implementation details and tradeoffs

**Use this for:** Understanding persistence options and implementing the volume-based solution.

---

### 2. **KEYCLOAK_MASTER_REALM_SSL_FIX.md** ⭐ REFERENCE

Detailed explanation of the "HTTPS required" error and the master realm SSL configuration.

**Topics Covered:**

- Why master realm is separate from application realm
- Why environment variables don't fix the SSL requirement
- How to use kcadm.sh to disable SSL for master realm
- Troubleshooting steps

**Use this for:** Understanding the root cause of HTTPS errors and how to fix them.

---

### 3. **deployment/keycloak/QUICK_START.md** ⭐ QUICK REFERENCE

Fast reference guide for day-to-day Keycloak operations.

**Topics Covered:**

- Access admin console
- Configure OAuth2 client (mario-app)
- Test OAuth2 in Swagger UI
- Test users and credentials
- Common troubleshooting

**Use this for:** Quick setup, daily operations, and testing.

---

## Deprecated/Outdated Documentation

### ~~KEYCLOAK_HTTPS_REQUIRED_FIX.md~~ ❌ OUTDATED

**Status:** Superseded by KEYCLOAK_MASTER_REALM_SSL_FIX.md

**Why outdated:** This document suggested adding `KC_HOSTNAME_STRICT_BACKCHANNEL: false` as a solution, but this doesn't fix the master realm SSL requirement. The real issue is realm-level SSL settings, not server-level hostname settings.

**Migration:** See KEYCLOAK_MASTER_REALM_SSL_FIX.md instead.

---

### ~~KEYCLOAK_VERSION_DOWNGRADE.md~~ ⚠️ PARTIALLY OUTDATED

**Status:** Correct about version downgrade, but incomplete solution

**Why partially outdated:**

- ✅ **Correct:** Keycloak 23+ has stricter HTTPS enforcement, downgrade to 22.0.5 is recommended
- ❌ **Incomplete:** Doesn't mention that master realm SSL still needs manual configuration even on 22.0.5

**What's still valid:**

- Version 22.0.5 is recommended for development
- Environment variable configurations are correct
- Docker compose changes are correct

**What's missing:**

- Master realm SSL configuration requirement
- Persistence strategy

**Migration:**

1. Keep using 22.0.5 (correct)
2. Add named volume for persistence (see KEYCLOAK_PERSISTENCE_STRATEGY.md)
3. Configure master realm SSL on first startup (see KEYCLOAK_MASTER_REALM_SSL_FIX.md)

---

### KEYCLOAK_AUTH_INTEGRATION_COMPLETE.md ✅ STILL VALID

**Status:** Active - OAuth2 integration documentation

**Topics Covered:**

- OAuth2 settings configuration
- ProfileController OAuth2 integration
- Token validation patterns
- API endpoint protection

**Use this for:** Understanding how OAuth2 is integrated into the Mario's Pizzeria application.

---

### samples/mario-pizzeria/notes/BUGFIX_STATIC_KEYCLOAK.md ✅ STILL VALID

**Status:** Active - UI-specific Keycloak issue

**Topics Covered:**

- Static file serving conflicts with Keycloak redirects
- Flask UI server configuration
- Path routing fixes

**Use this for:** Troubleshooting UI server and static file issues.

---

## Quick Start: Complete Setup Process

### First-Time Setup

```bash
# 1. Start services (imports realm on first startup)
docker-compose -f docker-compose.mario.yml up -d

# 2. Wait for Keycloak to be ready
sleep 30

# 3. Configure master realm SSL (REQUIRED ON FIRST STARTUP)
make keycloak-setup
# or: ./deployment/keycloak/configure-master-realm.sh

# 4. Verify configuration
make keycloak-verify

# 5. Access admin console
open http://localhost:8090
# Login: admin / admin
```

### After First Setup (Volume Persists Configuration)

```bash
# Just start services - configuration is persisted!
docker-compose -f docker-compose.mario.yml up -d

# Access admin console
open http://localhost:8090
```

### Reset Everything

```bash
# Complete reset (removes volumes, reimports realm)
make keycloak-reset
```

---

## Makefile Commands

```bash
make keycloak-setup    # Configure master realm SSL
make keycloak-verify   # Check configuration status
make keycloak-reset    # Complete reset (removes volume)
make keycloak-logs     # Show container logs
```

---

## Troubleshooting Decision Tree

### "HTTPS required" error on admin console

1. **Check which realm is causing the error:**

   ```bash
   docker logs mario-pizzeria-keycloak-1 | grep ssl_required
   ```

2. **If you see master realm UUID (c80baf0b-...):**

   - Run: `make keycloak-setup`
   - See: KEYCLOAK_MASTER_REALM_SSL_FIX.md

3. **If you see mario-pizzeria realm:**
   - Check realm export: `deployment/keycloak/mario-pizzeria-realm-export.json`
   - Should have: `"sslRequired": "none"`

### Configuration not persisting after restart

1. **Check if volume exists:**

   ```bash
   docker volume ls | grep keycloak
   ```

2. **If no volume:** Add to docker-compose.yml (see KEYCLOAK_PERSISTENCE_STRATEGY.md)

3. **If volume exists but config lost:**
   - Volume might be corrupted
   - Run: `make keycloak-reset`

### OAuth2 flow fails in Swagger UI

1. **Check client configuration in Keycloak admin console:**

   - Valid Redirect URIs must include: `http://localhost:8080/api/docs/oauth2-redirect`
   - Web Origins must include: `http://localhost:8080`

2. **Check application settings:**

   ```bash
   cat samples/mario-pizzeria/application/settings.py | grep keycloak
   ```

3. **See:** deployment/keycloak/QUICK_START.md for detailed OAuth2 setup

---

## File Organization

```
notes/
├── KEYCLOAK_PERSISTENCE_STRATEGY.md    ⭐ How to persist configuration
├── KEYCLOAK_MASTER_REALM_SSL_FIX.md    ⭐ Why HTTPS errors happen
├── KEYCLOAK_AUTH_INTEGRATION_COMPLETE.md  OAuth2 integration guide
├── KEYCLOAK_VERSION_DOWNGRADE.md       ⚠️  Partially outdated (keep for version info)
└── KEYCLOAK_HTTPS_REQUIRED_FIX.md      ❌ Outdated (wrong solution)

deployment/keycloak/
├── QUICK_START.md                      ⭐ Daily operations guide
├── configure-master-realm.sh           Configuration script
├── mario-pizzeria-realm-export.json    Realm configuration
└── master-realm-config.json            Master realm reference

samples/mario-pizzeria/notes/
└── BUGFIX_STATIC_KEYCLOAK.md          UI-specific issue (still valid)
```

---

## Version History

- **v1.0** (Initial): Keycloak 23.0.3 with environment variable attempts
- **v1.1** (Downgrade): Keycloak 22.0.5 to avoid strict HTTPS
- **v1.2** (Root Cause): Master realm SSL configuration discovered
- **v1.3** (Persistence): Named volume added for H2 database
- **v1.4** (Current): Consolidated documentation, deprecated outdated guides

---

## Related Documentation

- **Neuroglia Framework**: OAuth2 integration patterns
- **FastAPI OAuth2**: `samples/mario-pizzeria/api/services/oauth2_scheme.py`
- **Application Settings**: `samples/mario-pizzeria/application/settings.py`
- **Docker Compose**: `docker-compose.mario.yml`

---

## Summary

**For new developers:**

1. Read: KEYCLOAK_PERSISTENCE_STRATEGY.md
2. Read: deployment/keycloak/QUICK_START.md
3. Follow: First-Time Setup process above

**For troubleshooting:**

1. Use: Troubleshooting Decision Tree above
2. Reference: KEYCLOAK_MASTER_REALM_SSL_FIX.md for deep dive

**Ignore:**

- KEYCLOAK_HTTPS_REQUIRED_FIX.md (wrong solution)
- Most of KEYCLOAK_VERSION_DOWNGRADE.md (incomplete, but version info is correct)
