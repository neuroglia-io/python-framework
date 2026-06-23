# Infrastructure Recreate Command Guide

## Overview

The new `recreate` command has been added to the infrastructure CLI to properly handle service recreation when configuration changes are made.

## Why Recreate Instead of Restart?

**Problem**: Docker's `restart` command does NOT reload environment variables or configuration changes. It simply stops and starts the existing container with its original configuration.

**Solution**: The `recreate` command forces Docker to:

1. Stop the service
2. Remove the old container
3. Create a new container from the image
4. Apply current configuration and environment variables

## Usage

### Basic Recreate (Preserves Data)

```bash
# Recreate a specific service (keeps volumes/data)
./infra recreate keycloak

# Recreate all services (keeps volumes/data)
./infra recreate
```

### Recreate with Fresh Data

```bash
# Recreate Keycloak with fresh data volumes (deletes Keycloak data)
./infra recreate keycloak --delete-volumes

# Recreate all services with fresh volumes (deletes ALL data!)
./infra recreate --delete-volumes -y
```

### Using Makefile

```bash
# Recreate specific service
make infra-recreate SERVICE=keycloak

# Recreate all services
make infra-recreate

# Recreate with fresh volumes (deletes data)
make infra-recreate-clean SERVICE=keycloak

# Recreate all with fresh volumes
make infra-recreate-clean
```

## Common Use Cases

### 1. OAuth Configuration Changes

When you update OAuth settings in `docker-compose.shared.yml`:

```bash
# Update event-player OAuth client ID
# Edit: deployment/docker-compose/docker-compose.shared.yml
# Change: oauth_client_id: pyneuro-public-app
# To:     oauth_client_id: pyneuro-public

# Recreate to apply changes
./infra recreate event-player
```

### 2. Keycloak Realm Import Issues

When Keycloak needs to reimport realm configurations:

```bash
# Delete Keycloak data and reimport from JSON
./infra recreate keycloak --delete-volumes

# This will:
# 1. Stop Keycloak
# 2. Delete keycloak_data volume
# 3. Create fresh container
# 4. Auto-import pyneuro-realm-export.json
```

### 3. Environment Variable Updates

When any service environment variables change:

```bash
# Example: Changed MongoDB credentials
./infra recreate mongodb

# Example: Changed Grafana settings
./infra recreate grafana
```

### 4. Service Behaving Incorrectly

When a service is misbehaving after configuration changes:

```bash
# Try recreate first (keeps data)
./infra recreate prometheus

# If still issues, fresh start (deletes data)
./infra recreate prometheus --delete-volumes
```

## Command Options

| Option                | Description                                       |
| --------------------- | ------------------------------------------------- |
| `[service]`           | Specific service name (optional, defaults to all) |
| `--delete-volumes`    | Delete volumes (⚠️ destroys persisted data!)      |
| `--no-remove-orphans` | Don't remove orphan containers                    |
| `-y, --yes`           | Skip confirmation prompts                         |

## Available Services

- `mongodb` - NoSQL database
- `mongo-express` - Database UI
- `keycloak` - Identity & Access Management
- `prometheus` - Metrics collection
- `grafana` - Observability dashboards
- `loki` - Log aggregation
- `tempo` - Distributed tracing
- `otel-collector` - OpenTelemetry collector
- `event-player` - Event testing tool

## Safety Features

1. **Confirmation Prompts**: When using `--delete-volumes`, you'll be asked to confirm unless `-y` is provided
2. **Volume Preservation**: By default, volumes (data) are preserved
3. **Orphan Cleanup**: Automatically removes orphaned containers (can disable with `--no-remove-orphans`)

## Examples

### Fix Event-Player OAuth Issue

```bash
# 1. Update docker-compose.shared.yml with correct client ID
# 2. Recreate event-player to apply changes
./infra recreate event-player

# 3. If Keycloak realm needs reimport
./infra recreate keycloak --delete-volumes
```

### Reset Grafana Dashboards

```bash
# Delete Grafana data and start fresh
./infra recreate grafana --delete-volumes
```

### Update MongoDB Configuration

```bash
# Recreate MongoDB with current config (keeps data)
./infra recreate mongodb
```

### Nuclear Option - Fresh Everything

```bash
# Delete all infrastructure data and recreate
./infra recreate --delete-volumes -y
```

## Comparison: Restart vs Recreate

| Action                 | Restart | Recreate | Recreate --delete-volumes |
| ---------------------- | ------- | -------- | ------------------------- |
| Stops container        | ✅      | ✅       | ✅                        |
| Starts container       | ✅      | ✅       | ✅                        |
| Creates new container  | ❌      | ✅       | ✅                        |
| Applies config changes | ❌      | ✅       | ✅                        |
| Reloads env vars       | ❌      | ✅       | ✅                        |
| Preserves data         | ✅      | ✅       | ❌                        |
| Reimports configs      | ❌      | ❌       | ✅                        |

## Technical Details

The `recreate` command internally:

1. Stops the service(s): `docker-compose stop [service]`
2. Removes containers: `docker-compose rm -f [service]`
3. Optionally removes volumes: `docker-compose rm -f -v [service]` + `docker volume rm`
4. Creates new containers: `docker-compose up -d --force-recreate [service]`

The `--force-recreate` flag ensures Docker creates new containers even if the configuration hasn't changed.

## Troubleshooting

### "Volume is in use" Error

If you get an error about volumes being in use:

```bash
# Stop all services first
./infra stop

# Then recreate with fresh volumes
./infra recreate keycloak --delete-volumes
```

### "Service not found" Error

Make sure the service name is correct (lowercase, hyphen-separated):

```bash
# Correct
./infra recreate event-player

# Incorrect
./infra recreate event_player
./infra recreate EventPlayer
```

### Changes Still Not Applied

If changes aren't applied after recreate:

1. Check docker-compose.shared.yml has your changes
2. Try recreating all services: `./infra recreate`
3. Check logs: `./infra logs [service]`
4. Verify environment variables: `docker inspect [container-name]`

## Related Documentation

- [Infra CLI Documentation](docs/cli/infra-cli.md)
- [Docker Compose Shared Infrastructure](deployment/docker-compose/docker-compose.shared.yml)
- [Keycloak Quick Start](deployment/keycloak/QUICK_START.md)
