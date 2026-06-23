# ❌ OUTDATED - See KEYCLOAK_MASTER_REALM_SSL_FIX.md Instead

**This document is outdated and contains an incomplete solution.**

**The correct solution is in:**

- `KEYCLOAK_MASTER_REALM_SSL_FIX.md` - Root cause and proper fix
- `KEYCLOAK_PERSISTENCE_STRATEGY.md` - Persistence configuration
- `deployment/keycloak/QUICK_START.md` - Quick reference

**Why this is outdated:**
The `KC_HOSTNAME_STRICT_BACKCHANNEL: false` environment variable suggested here does NOT fix the "HTTPS required" error for the admin console. The real issue is that the **master realm** has a separate `sslRequired` setting that must be changed via `kcadm.sh` CLI tool.

---

# Keycloak "HTTPS Required" Error - Troubleshooting

## Problem

When accessing Keycloak admin console at http://localhost:8090, you get an error:

```
HTTPS required
```

This happens even though the docker-compose configuration appears to have HTTP enabled.

## Root Cause

Keycloak 23+ (newer versions) have **stricter HTTPS enforcement** by default. Even with `KC_HOSTNAME_STRICT_HTTPS: false`, the admin console may still require HTTPS if backchannel communication isn't explicitly allowed over HTTP.

## Solution

Add the missing environment variable `KC_HOSTNAME_STRICT_BACKCHANNEL: false` to the Keycloak service in `docker-compose.mario.yml`:

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:23.0.3
  command: ["start-dev", "--import-realm"]
  ports:
    - 8090:8080
  environment:
    KEYCLOAK_ADMIN: admin
    KEYCLOAK_ADMIN_PASSWORD: admin
    KC_HTTP_PORT: 8080
    KC_HOSTNAME_STRICT: false
    KC_HOSTNAME_STRICT_HTTPS: false
    KC_HOSTNAME_STRICT_BACKCHANNEL: false # ✅ CRITICAL - Allows HTTP for admin console
    KC_HTTP_ENABLED: true
    KC_HEALTH_ENABLED: true
    KC_METRICS_ENABLED: true
    KC_HOSTNAME_URL: http://localhost:8090
    KC_HOSTNAME_ADMIN_URL: http://localhost:8090
    KC_PROXY: edge
```

## Why This Happens

Keycloak has **three different strictness settings**:

1. **`KC_HOSTNAME_STRICT`**: Controls whether hostname validation is strict
2. **`KC_HOSTNAME_STRICT_HTTPS`**: Controls whether HTTPS is required for frontend requests
3. **`KC_HOSTNAME_STRICT_BACKCHANNEL`**: Controls whether HTTPS is required for backchannel/admin requests

Even if you set the first two to `false`, Keycloak may still enforce HTTPS for the **admin console** (backchannel) unless you explicitly disable it with `KC_HOSTNAME_STRICT_BACKCHANNEL: false`.

## Environment Variables Explained

| Variable                         | Value                   | Purpose                          |
| -------------------------------- | ----------------------- | -------------------------------- |
| `KC_HOSTNAME_STRICT`             | `false`                 | Disable hostname validation      |
| `KC_HOSTNAME_STRICT_HTTPS`       | `false`                 | Allow HTTP for frontend requests |
| `KC_HOSTNAME_STRICT_BACKCHANNEL` | `false`                 | **Allow HTTP for admin console** |
| `KC_HTTP_ENABLED`                | `true`                  | Enable HTTP protocol             |
| `KC_HOSTNAME_URL`                | `http://localhost:8090` | Base URL for Keycloak            |
| `KC_HOSTNAME_ADMIN_URL`          | `http://localhost:8090` | Admin console URL                |
| `KC_PROXY`                       | `edge`                  | Trust proxy headers (for Docker) |

## Alternative: Master Realm HTTPS Setting

If the above doesn't work, you may need to also check the **master realm** SSL settings:

1. **Login to master realm**: http://localhost:8090/admin/master/console
2. **Navigate to**: Realm Settings → General
3. **Require SSL**: Set to "none" or "external requests"
4. **Save**

However, this shouldn't be necessary if the environment variables are set correctly.

## Restart Steps

After adding `KC_HOSTNAME_STRICT_BACKCHANNEL: false`:

```bash
# Stop and remove containers (to ensure clean state)
docker-compose -f docker-compose.mario.yml down

# Remove any orphaned volumes (optional, if you want clean slate)
docker volume prune -f

# Start fresh
docker-compose -f docker-compose.mario.yml up -d

# Wait for Keycloak to start (takes ~30 seconds)
sleep 30

# Check logs
docker logs mario-pizzeria-keycloak-1

# Access admin console
open http://localhost:8090
```

## Verification

After restart, you should be able to:

1. **Access**: http://localhost:8090
2. **See**: Keycloak welcome page (not HTTPS error)
3. **Click**: "Administration Console"
4. **Login**: admin / admin
5. **Success**: Admin dashboard loads

## Realm SSL Settings

The `mario-pizzeria` realm has the correct SSL setting in the export file:

```json
{
  "realm": "mario-pizzeria",
  "sslRequired": "none",  // ✅ Correct - allows HTTP
  ...
}
```

This allows HTTP for the **mario-pizzeria** realm, but the **admin console** runs on the **master** realm, which needs the `KC_HOSTNAME_STRICT_BACKCHANNEL: false` environment variable.

## Production Notes

⚠️ **NEVER use these settings in production!**

In production, you should:

- Use proper HTTPS with valid certificates
- Set `KC_HOSTNAME_STRICT: true`
- Set `KC_HOSTNAME_STRICT_HTTPS: true`
- Set `KC_HOSTNAME_STRICT_BACKCHANNEL: true`
- Use a proper database (PostgreSQL) instead of H2
- Use `start` command instead of `start-dev`

```yaml
# Production example
keycloak:
  command: ["start", "--import-realm"]
  environment:
    KC_HOSTNAME_STRICT: true
    KC_HOSTNAME_STRICT_HTTPS: true
    KC_HOSTNAME_STRICT_BACKCHANNEL: true
    KC_HOSTNAME_URL: https://keycloak.production.com
    KC_HOSTNAME_ADMIN_URL: https://keycloak.production.com
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
```

## Why It Worked Before

If this worked previously and then stopped working, possible reasons:

1. **Keycloak version upgrade**: Newer versions (23+) are stricter
2. **Docker image cache**: Old image had different defaults
3. **Realm import**: The realm import may have overwritten settings
4. **Browser cache**: Try clearing browser cache or incognito mode

## Testing Checklist

- [ ] Added `KC_HOSTNAME_STRICT_BACKCHANNEL: false` to docker-compose.mario.yml
- [ ] Ran `docker-compose down`
- [ ] Ran `docker-compose up -d`
- [ ] Waited 30 seconds for Keycloak to start
- [ ] Accessed http://localhost:8090 (no HTTPS error)
- [ ] Logged into admin console (admin/admin)
- [ ] Can see mario-pizzeria realm
- [ ] Can configure clients and users

## Related Documentation

- **Keycloak Server Configuration**: https://www.keycloak.org/server/configuration
- **Hostname Configuration**: https://www.keycloak.org/server/hostname
- **Running Keycloak in Docker**: https://www.keycloak.org/server/containers

## Quick Fix Command

If you just want to restart with the fix:

```bash
docker-compose -f docker-compose.mario.yml down && \
docker-compose -f docker-compose.mario.yml up -d && \
echo "Waiting for Keycloak to start..." && \
sleep 30 && \
docker logs mario-pizzeria-keycloak-1 | tail -20 && \
echo "✅ Try accessing: http://localhost:8090"
```
