# ⚠️ PARTIALLY OUTDATED - See Updated Guides

**This document is partially correct but incomplete.**

**What's still valid:**

- ✅ Keycloak 22.0.5 is the recommended version (not 23.0.3)
- ✅ Environment variables shown are correct
- ✅ Docker compose configuration is correct

**What's missing:**

- ❌ Master realm SSL configuration (required even on 22.0.5)
- ❌ Persistence strategy for H2 database
- ❌ Complete first-time setup instructions

**For complete, up-to-date information, see:**

- `KEYCLOAK_CONFIGURATION_INDEX.md` - Central index of all Keycloak docs
- `KEYCLOAK_MASTER_REALM_SSL_FIX.md` - Master realm SSL requirement
- `KEYCLOAK_PERSISTENCE_STRATEGY.md` - How to persist configuration
- `deployment/keycloak/QUICK_START.md` - Complete setup guide

---

# Keycloak HTTPS Required - Complete Reset Guide

## Problem Summary

Keycloak 23.0.3+ has extremely strict HTTPS enforcement that cannot be easily disabled in development mode. Even with all the recommended environment variables set, the admin console may still require HTTPS.

## Root Cause

**Keycloak 23+ introduced breaking changes** in hostname/HTTPS handling that make it nearly impossible to run without HTTPS, even in `start-dev` mode. The `KC_HOSTNAME_STRICT_BACKCHANNEL` variable that was supposed to help doesn't fully work in version 23.0.3.

## Solution: Downgrade to Keycloak 22.0.5

Keycloak 22.0.5 is the last version before the strict HTTPS changes. It works perfectly in development mode with HTTP.

### docker-compose.mario.yml Changes

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:22.0.5 # ✅ Changed from 23.0.3
  command: ["start-dev", "--import-realm"]
  ports:
    - 8090:8080
  environment:
    KEYCLOAK_ADMIN: admin
    KEYCLOAK_ADMIN_PASSWORD: admin
    KC_HTTP_PORT: 8080
    KC_HOSTNAME_STRICT: false
    KC_HOSTNAME_STRICT_HTTPS: false
    KC_HTTP_ENABLED: true
    KC_HEALTH_ENABLED: true
    KC_METRICS_ENABLED: true
    KC_HOSTNAME_URL: http://localhost:8090
    KC_HOSTNAME_ADMIN_URL: http://localhost:8090
    KC_PROXY: edge
```

**Note**: Removed `KC_HOSTNAME_STRICT_BACKCHANNEL: false` as it's not needed in version 22.0.5.

## Complete Reset Procedure

### Step 1: Stop and Remove Keycloak Container

```bash
docker-compose -f docker-compose.mario.yml stop keycloak
docker-compose -f docker-compose.mario.yml rm -f keycloak
```

### Step 2: Remove Old Keycloak Image

```bash
docker rmi quay.io/keycloak/keycloak:23.0.3
```

### Step 3: Update docker-compose.mario.yml

Change the image version from `23.0.3` to `22.0.5` (already done above).

### Step 4: Start Keycloak 22.0.5

```bash
docker-compose -f docker-compose.mario.yml up -d keycloak
```

### Step 5: Wait for Startup

```bash
# Wait 40 seconds for Keycloak to initialize
sleep 40

# Check logs
docker logs mario-pizzeria-keycloak-1 | tail -30
```

### Step 6: Verify

```bash
# Should show HTTP access
curl -I http://localhost:8090

# Open in browser
open http://localhost:8090
```

## One-Command Complete Reset

```bash
# Complete cleanup and restart
docker-compose -f docker-compose.mario.yml stop keycloak && \
docker-compose -f docker-compose.mario.yml rm -f keycloak && \
docker rmi quay.io/keycloak/keycloak:23.0.3 2>/dev/null || true && \
docker-compose -f docker-compose.mario.yml up -d keycloak && \
echo "⏳ Waiting 40 seconds for Keycloak 22.0.5 to start..." && \
sleep 40 && \
docker logs mario-pizzeria-keycloak-1 | tail -30 && \
echo "" && \
echo "✅ Keycloak should now be accessible at: http://localhost:8090" && \
echo "   Login: admin / admin"
```

## Verification Checklist

After restart, verify:

- [ ] Navigate to http://localhost:8090
- [ ] See Keycloak welcome page (no HTTPS error)
- [ ] Click "Administration Console"
- [ ] Login with admin/admin succeeds
- [ ] Can see mario-pizzeria realm
- [ ] Can see mario-app client
- [ ] Can configure client settings
- [ ] Can create/edit users

## What Changed in Keycloak 22.0.5 vs 23.0.3

| Feature                              | Version 22.0.5  | Version 23.0.3               |
| ------------------------------------ | --------------- | ---------------------------- |
| **HTTP in Dev Mode**                 | ✅ Works easily | ❌ Extremely difficult       |
| **Admin Console over HTTP**          | ✅ Supported    | ❌ Requires complex config   |
| **`KC_HOSTNAME_STRICT_HTTPS`**       | ✅ Respected    | ⚠️ Not always respected      |
| **`KC_HOSTNAME_STRICT_BACKCHANNEL`** | ❌ Not needed   | ⚠️ Required but may not work |
| **Hostname Validation**              | ✅ Flexible     | ❌ Very strict               |
| **Development Experience**           | ✅ Easy         | ❌ Frustrating               |

## Why Keycloak 23+ Is So Strict

Keycloak 23.0+ was hardened for **production security** with:

- Mandatory HTTPS by default (even in dev mode)
- Stricter hostname validation
- Separate admin console HTTPS requirements
- More restrictive default policies

While these changes improve production security, they make **local development very difficult** without proper SSL certificates.

## Alternative: Use Keycloak 21.x (Even Older)

If 22.0.5 still has issues, you can go even older:

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:21.1.2 # Very stable version
```

Version 21.x is very permissive and works great for development.

## Production Recommendations

For **production**, you should:

1. **Use Keycloak 24+ (latest stable)** for security fixes
2. **Always use HTTPS** with valid certificates
3. **Use proper database** (PostgreSQL, not H2)
4. **Enable all strictness settings**:

   ```yaml
   KC_HOSTNAME_STRICT: true
   KC_HOSTNAME_STRICT_HTTPS: true
   KC_HOSTNAME_URL: https://keycloak.production.com
   KC_DB: postgres
   ```

## If You Must Use Keycloak 23+

If you absolutely need version 23+, you'll need to:

1. **Set up local SSL certificates**:

   ```bash
   # Generate self-signed cert
   openssl req -x509 -newkey rsa:4096 -nodes \
     -keyout keycloak.key -out keycloak.crt \
     -days 365 -subj "/CN=localhost"
   ```

2. **Configure Keycloak with HTTPS**:

   ```yaml
   keycloak:
     image: quay.io/keycloak/keycloak:23.0.3
     command:
       ["start-dev", "--https-certificate-file=/certs/keycloak.crt", "--https-certificate-key-file=/certs/keycloak.key"]
     ports:
       - 8443:8443
     environment:
       KC_HTTPS_PORT: 8443
       KC_HOSTNAME_URL: https://localhost:8443
     volumes:
       - ./certs:/certs:ro
   ```

3. **Accept self-signed certificate** in browser

But honestly, **just use version 22.0.5 for development** - it's much easier!

## Logs to Check

After starting Keycloak, look for this line in the logs:

```
Hostname settings: Base URL: http://localhost:8090, Hostname: localhost,
Strict HTTPS: false, Path: /, Strict BackChannel: false,
Admin URL: http://localhost:8090
```

If you see:

- ✅ `Strict HTTPS: false` - Good!
- ❌ `Strict HTTPS: true` - Problem, won't work

## Common Issues After Downgrade

### Issue: "Failed to import realm"

**Cause**: Realm export from newer version incompatible with older version.

**Solution**: The mario-pizzeria realm export should work fine with 22.0.5. If not, recreate the realm manually.

### Issue: "Database schema version mismatch"

**Cause**: H2 database from newer version.

**Solution**: Remove the H2 database:

```bash
docker volume rm mario-pizzeria_keycloak_data 2>/dev/null || true
```

### Issue: Port 8090 already in use

**Solution**:

```bash
lsof -ti:8090 | xargs kill -9
```

## Version Compatibility Matrix

| Keycloak Version | HTTP Dev Mode | Admin Console HTTP | Recommended        |
| ---------------- | ------------- | ------------------ | ------------------ |
| **21.1.2**       | ✅ Easy       | ✅ Works           | ✅ Very Safe       |
| **22.0.5**       | ✅ Easy       | ✅ Works           | ✅ **Recommended** |
| **23.0.3**       | ⚠️ Hard       | ❌ Broken          | ❌ Avoid           |
| **24.0+**        | ⚠️ Very Hard  | ❌ Requires SSL    | ❌ Avoid for dev   |

## Testing After Downgrade

```bash
# Test admin console access
curl -I http://localhost:8090/admin/master/console/

# Should return HTTP 200 or 302 (not 400 or 500)

# Test realm endpoint
curl http://localhost:8090/realms/mario-pizzeria

# Should return JSON with realm info
```

## Related Documentation

- **Keycloak 22.0 Docs**: https://www.keycloak.org/docs/22.0/
- **Keycloak Server Configuration**: https://www.keycloak.org/server/configuration
- **Hostname Configuration Changes**: https://www.keycloak.org/docs/latest/upgrading/#hostname-changes

## Summary

**TL;DR**: Keycloak 23+ is too strict for local HTTP development. Use version **22.0.5** instead - it's stable, well-tested, and works perfectly with HTTP in development mode without any SSL certificate hassles.
