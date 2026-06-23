# Keycloak Persistence Strategy

## Problem

Keycloak's master realm SSL configuration (`sslRequired=NONE`) is lost when the container is removed or recreated. We need a way to persist this configuration across container restarts.

## Solution Options

### Option 1: Named Volume for H2 Database (Recommended for Development)

**Pros:**

- Simple, single volume mount
- Persists ALL Keycloak data (realms, users, sessions)
- No external database required
- Survives `docker-compose down` and `docker-compose up`

**Cons:**

- Data is lost if you run `docker-compose down -v` (removes volumes)
- H2 database is file-based, not suitable for production
- Volume contains binary data (not human-readable)

**Implementation:**

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:22.0.5
  command: ["start-dev", "--import-realm"]
  volumes:
    - keycloak_data:/opt/keycloak/data # Persist H2 database
    - ./deployment/keycloak/mario-pizzeria-realm-export.json:/opt/keycloak/data/import/mario-pizzeria-realm-export.json:ro
  # ... rest of config

volumes:
  keycloak_data:
    driver: local
```

**Important:** The `--import-realm` only imports on **first startup**. After that, the persisted database takes precedence.

### Option 2: Startup Script (Current Recommendation)

**Pros:**

- Clean separation of concerns
- Easy to version control
- Can be automated in development workflow
- Doesn't require persistent storage

**Cons:**

- Must run script after every fresh container start
- Not automatic (requires manual step)

**Implementation:**

Already created: `./deployment/keycloak/configure-master-realm.sh`

Add to your development workflow:

```bash
# Start services
docker-compose -f docker-compose.mario.yml up -d

# Configure Keycloak (wait for startup)
sleep 25 && ./deployment/keycloak/configure-master-realm.sh

# Verify
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired
```

### Option 3: Custom Docker Entrypoint Script

**Pros:**

- Fully automated
- Runs on every container start
- No manual intervention needed

**Cons:**

- More complex to maintain
- Requires custom Dockerfile
- Adds startup time

**Implementation:**

Create `deployment/keycloak/entrypoint.sh`:

```bash
#!/bin/bash
set -e

# Start Keycloak in background
/opt/keycloak/bin/kc.sh start-dev --import-realm &
KEYCLOAK_PID=$!

# Wait for Keycloak to be ready
echo "Waiting for Keycloak to start..."
sleep 30

# Configure master realm
echo "Configuring master realm..."
/opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user $KEYCLOAK_ADMIN \
  --password $KEYCLOAK_ADMIN_PASSWORD

/opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=NONE
echo "Master realm configured successfully!"

# Keep Keycloak running
wait $KEYCLOAK_PID
```

Create `deployment/keycloak/Dockerfile`:

```dockerfile
FROM quay.io/keycloak/keycloak:22.0.5

# Copy custom entrypoint
COPY entrypoint.sh /opt/keycloak/bin/entrypoint.sh
RUN chmod +x /opt/keycloak/bin/entrypoint.sh

ENTRYPOINT ["/opt/keycloak/bin/entrypoint.sh"]
```

Update `docker-compose.mario.yml`:

```yaml
keycloak:
  build:
    context: ./deployment/keycloak
    dockerfile: Dockerfile
  # ... rest of config
```

### Option 4: PostgreSQL Backend (Production-Ready)

**Pros:**

- Production-ready persistence
- Scalable and reliable
- Survives container recreation
- Better performance than H2

**Cons:**

- Requires PostgreSQL container
- More complex setup
- Overkill for local development

**Implementation:**

```yaml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:22.0.5
    command: ["start-dev", "--import-realm"]
    environment:
      # ... existing env vars
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: keycloak
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: keycloak
    volumes:
      - postgres_keycloak_data:/var/lib/postgresql/data

volumes:
  postgres_keycloak_data:
    driver: local
```

## Recommended Approach for This Project

**Development (Current):** Option 2 - Startup Script

Keep it simple and explicit. The script approach:

- Is easy to understand and debug
- Doesn't hide complexity
- Makes it clear this is a development workaround
- Can be documented in README

**Why not Option 1 (H2 volume)?**

While tempting, the H2 volume approach has a subtle issue: The `--import-realm` flag only works on **first startup**. If you:

1. Start Keycloak with volume → imports realm, configures master realm manually
2. Stop and remove container
3. Start Keycloak again → volume exists, so `--import-realm` does nothing

If you make changes to `mario-pizzeria-realm-export.json`, they won't be applied because the persisted H2 database takes precedence. You'd need to delete the volume to reimport.

**For Production:** Option 4 - PostgreSQL

Use a proper database backend with automated configuration via infrastructure-as-code (Terraform, Kubernetes, etc.).

## Implementation: Add Named Volume (Recommended)

Let's implement Option 1 (H2 volume) since it's the best balance for development:

```yaml
# docker-compose.mario.yml
keycloak:
  image: quay.io/keycloak/keycloak:22.0.5
  command: ["start-dev", "--import-realm"]
  ports:
    - 8090:8080
  environment:
    # ... all existing environment variables
  volumes:
    - keycloak_data:/opt/keycloak/data # ADD THIS LINE
    - ./deployment/keycloak/mario-pizzeria-realm-export.json:/opt/keycloak/data/import/mario-pizzeria-realm-export.json:ro
  networks:
    - mario-net

volumes:
  mario_data:
    driver: local
  mongodb_data:
    driver: local
  eventstoredb_data:
    driver: local
  keycloak_data: # ADD THIS
    driver: local
```

## First-Time Setup with Volume

After adding the volume:

```bash
# 1. Start Keycloak (will import realm on first startup)
docker-compose -f docker-compose.mario.yml up -d keycloak

# 2. Wait for it to be ready
sleep 30

# 3. Configure master realm (ONLY NEEDED ONCE)
./deployment/keycloak/configure-master-realm.sh

# 4. Verify
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired
```

**From now on:** The configuration persists! Just run `docker-compose up -d` and you're good to go.

## When to Reset Keycloak

If you need to start fresh (reimport realm, reset users, etc.):

```bash
# Stop services
docker-compose -f docker-compose.mario.yml down

# Remove Keycloak volume
docker volume rm mario-pizzeria_keycloak_data

# Start fresh
docker-compose -f docker-compose.mario.yml up -d keycloak
sleep 30
./deployment/keycloak/configure-master-realm.sh
```

## Makefile Targets (Suggested)

Add these to your `Makefile` for convenience:

```makefile
.PHONY: keycloak-setup
keycloak-setup:  ## Configure Keycloak master realm SSL
 @echo "Configuring Keycloak master realm..."
 @./deployment/keycloak/configure-master-realm.sh

.PHONY: keycloak-reset
keycloak-reset:  ## Reset Keycloak (removes volume and recreates)
 @echo "Resetting Keycloak..."
 @docker-compose -f docker-compose.mario.yml stop keycloak
 @docker volume rm -f mario-pizzeria_keycloak_data
 @docker-compose -f docker-compose.mario.yml up -d keycloak
 @echo "Waiting for Keycloak to start..."
 @sleep 30
 @./deployment/keycloak/configure-master-realm.sh
 @echo "Keycloak reset complete!"

.PHONY: keycloak-verify
keycloak-verify:  ## Verify Keycloak master realm configuration
 @docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired
```

Usage:

```bash
make keycloak-setup     # Configure master realm
make keycloak-verify    # Check configuration
make keycloak-reset     # Start fresh
```

## Summary

**For your use case:** Add the named volume (`keycloak_data`) to persist the H2 database. This gives you:

- ✅ Automatic persistence across container restarts
- ✅ Simple to implement (one line in docker-compose)
- ✅ No external dependencies
- ✅ Survives `docker-compose down` and `docker-compose up`
- ✅ One-time configuration of master realm SSL

The only time you need to reconfigure is when you explicitly delete the volume or want to reimport the realm configuration.

## Related Files

- `docker-compose.mario.yml` - Docker configuration
- `deployment/keycloak/configure-master-realm.sh` - Configuration script
- `deployment/keycloak/QUICK_START.md` - Quick start guide
- `notes/KEYCLOAK_MASTER_REALM_SSL_FIX.md` - Detailed explanation of the SSL issue
