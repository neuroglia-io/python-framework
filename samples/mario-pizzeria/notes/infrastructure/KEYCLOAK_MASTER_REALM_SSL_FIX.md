# Keycloak Master Realm SSL Requirement Fix

## Problem

When accessing Keycloak admin console at http://localhost:8090 and trying to login, you get:

```
HTTPS required
```

Even though the environment variables disable HTTPS, the **master realm** still requires SSL.

## Root Cause

Keycloak has **two separate realms**:

1. **master realm** - For admin console (NOT imported from JSON, has default SSL settings)
2. **mario-pizzeria realm** - Your application realm (imported from JSON with `"sslRequired": "none"`)

The environment variables (`KC_HOSTNAME_STRICT_HTTPS: false`) control the **server-level** settings, but each **realm** has its own SSL requirement setting that overrides this.

When Keycloak starts fresh, the **master realm** defaults to requiring SSL, and the `--import-realm` command does NOT import master realm configuration.

## Logs Show the Problem

```
type=LOGIN_ERROR, realmId=c80baf0b-f703-46d3-92e3-58e7770e66e3, error=ssl_required
```

The realm ID `c80baf0b-...` is the **master realm**, not mario-pizzeria!

## Solution: Manual Configuration Required

After Keycloak starts, you must manually disable SSL for the master realm:

```bash
# 1. Configure kcadm.sh credentials
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password admin

# 2. Update master realm SSL setting
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh update realms/master \
  -s sslRequired=NONE

# 3. Verify it worked
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired
```

Expected output: `"sslRequired" : "NONE",`

## Automated Script

We've created a script to do this automatically:

```bash
./deployment/keycloak/configure-master-realm.sh
```

This script:

1. Waits for Keycloak to be ready (20 seconds)
2. Configures kcadm credentials
3. Updates master realm SSL setting
4. Confirms completion

## Complete Restart Process

To start Keycloak with proper SSL configuration:

```bash
# 1. Start Keycloak
docker-compose -f docker-compose.mario.yml up -d keycloak

# 2. Wait for it to be ready
sleep 25

# 3. Configure master realm
./deployment/keycloak/configure-master-realm.sh

# 4. Access admin console
open http://localhost:8090
```

## Why This Happens

1. **Keycloak starts** with default master realm (SSL required)
2. **`--import-realm` runs** and imports mario-pizzeria realm (SSL none)
3. **Master realm is NOT touched** by import process
4. **Admin console uses master realm** for authentication
5. **SSL is still required** for master realm → Error!

## Alternative: Use REST API During Startup

You could also use a startup script that runs after Keycloak is ready:

```yaml
# docker-compose.mario.yml
keycloak:
  image: quay.io/keycloak/keycloak:22.0.5
  command: |
    bash -c "
      /opt/keycloak/bin/kc.sh start-dev --import-realm &
      sleep 30 &&
      /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin &&
      /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=NONE &&
      wait
    "
```

But this is complex and fragile.

## Recommended: Make It Part of Your Setup

Add this to your project's README or setup script:

```markdown
### Keycloak Setup

After starting Docker:

1. Start services: `docker-compose -f docker-compose.mario.yml up -d`
2. Configure Keycloak: `./deployment/keycloak/configure-master-realm.sh`
3. Access admin: http://localhost:8090 (admin/admin)
```

## Verification Steps

After running the configuration script:

```bash
# Check master realm SSL setting
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired

# Should show:
"sslRequired" : "NONE",
```

Then try accessing the admin console:

1. **Open**: http://localhost:8090
2. **Click**: "Administration Console"
3. **Login**: admin / admin
4. **Success**: No HTTPS error, admin dashboard loads

## Important Notes

⚠️ **This configuration is lost when container is removed**

If you run `docker-compose down` or remove the container, you'll need to run the configuration script again.

To avoid this:

- Use a persistent volume for Keycloak data (not recommended for development)
- Run the configuration script as part of your startup process
- Document this as a required setup step

⚠️ **Never use this in production**

In production:

- Use proper HTTPS with valid certificates
- Keep SSL required for all realms
- Use a persistent database (PostgreSQL)

## Troubleshooting

### Issue: "Connection refused" when running script

**Solution**: Keycloak isn't ready yet. Wait longer:

```bash
sleep 30
./deployment/keycloak/configure-master-realm.sh
```

### Issue: "Invalid credentials"

**Solution**: Check admin password in docker-compose:

```yaml
environment:
  KEYCLOAK_ADMIN: admin
  KEYCLOAK_ADMIN_PASSWORD: admin # Must match what you use in script
```

### Issue: Still getting HTTPS required after script

**Solution**: Check which realm is showing the error:

```bash
docker logs mario-pizzeria-keycloak-1 | grep ssl_required
```

If you see a different realm ID, you may need to update that realm too:

```bash
# For mario-pizzeria realm (shouldn't be needed, but just in case)
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh update realms/mario-pizzeria \
  -s sslRequired=NONE
```

### Issue: Want to persist this configuration

**Solution**: Add a named volume for Keycloak data:

```yaml
keycloak:
  volumes:
    - keycloak_data:/opt/keycloak/data
    - ./deployment/keycloak/mario-pizzeria-realm-export.json:/opt/keycloak/data/import/mario-pizzeria-realm-export.json:ro

volumes:
  keycloak_data:
    driver: local
```

But be aware this will persist ALL Keycloak data including the H2 database.

## Quick Reference

**Start Keycloak:**

```bash
docker-compose -f docker-compose.mario.yml up -d keycloak
```

**Configure Master Realm:**

```bash
sleep 25
./deployment/keycloak/configure-master-realm.sh
```

**Verify Configuration:**

```bash
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired
```

**Access Admin Console:**

```bash
open http://localhost:8090
```

## Files Created

- ✅ `deployment/keycloak/configure-master-realm.sh` - Automated configuration script
- ✅ `deployment/keycloak/master-realm-config.json` - Reference configuration (not used by import)
- ✅ `notes/KEYCLOAK_MASTER_REALM_SSL_FIX.md` - This documentation

## Summary

The key insight: **Keycloak's `--import-realm` does not configure the master realm**. You must manually disable SSL for the master realm after startup using the kcadm CLI tool. The provided script automates this process.
