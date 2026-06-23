#!/bin/bash
#
# Keycloak Reset Script
#
# This script completely resets Keycloak by:
# 1. Stopping the Keycloak container
# 2. Deleting the persistent volume
# 3. Starting Keycloak fresh (with auto realm import)
# 4. Configuring SSL settings
#
# Usage: ./scripts/keycloak-reset.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/deployment/docker-compose/docker-compose.shared.yml"
CONFIGURE_SCRIPT="$PROJECT_ROOT/deployment/keycloak/configure-master-realm.sh"

echo "🔐 Keycloak Reset Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  WARNING: This will DELETE all Keycloak data!"
echo "   - All realms will be removed"
echo "   - All users will be deleted"
echo "   - All client configurations will be lost"
echo ""
echo "   The pyneuro realm will be reimported from:"
echo "   deployment/keycloak/pyneuro-realm-export.json"
echo ""

# Check if running in CI or with --yes flag
if [[ "$CI" != "true" ]] && [[ "$1" != "--yes" ]] && [[ "$1" != "-y" ]]; then
    read -p "Do you want to continue? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo "❌ Aborted"
        exit 1
    fi
fi

echo "⏹️  Step 1: Stopping Keycloak container..."
docker compose -f "$COMPOSE_FILE" stop keycloak

echo ""
echo "🗑️  Step 2: Deleting Keycloak data volume..."
VOLUME_NAME=$(docker volume ls --format '{{.Name}}' | grep keycloak_data || echo "")

if [ -n "$VOLUME_NAME" ]; then
    echo "   Found volume: $VOLUME_NAME"
    docker volume rm "$VOLUME_NAME" 2>/dev/null && echo "   ✅ Volume deleted" || echo "   ⚠️  Failed to delete volume (may be in use)"
else
    echo "   ℹ️  No keycloak_data volume found"
fi

echo ""
echo "🚀 Step 3: Starting Keycloak with fresh import..."
docker compose -f "$COMPOSE_FILE" up -d keycloak

echo ""
echo "⏳ Step 4: Waiting for Keycloak to be ready..."
echo "   This may take 30-60 seconds..."

MAX_WAIT=60
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8090/health/ready > /dev/null 2>&1; then
        echo "   ✅ Keycloak is ready!"
        break
    fi

    if [ $((COUNTER % 5)) -eq 0 ]; then
        echo "   Still waiting... ($COUNTER/$MAX_WAIT seconds)"
    fi

    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq $MAX_WAIT ]; then
    echo "   ⚠️  Timeout waiting for Keycloak"
    echo "   You may need to run the configuration script manually:"
    echo "   $CONFIGURE_SCRIPT"
    exit 1
fi

echo ""
echo "🔧 Step 5: Configuring realms (SSL, import pyneuro)..."
bash "$CONFIGURE_SCRIPT"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Keycloak reset complete!"
echo ""
echo "📋 Access Information:"
echo "   Admin Console: http://localhost:8090/admin"
echo "   Username:      admin"
echo "   Password:      admin"
echo "   Master Realm:  http://localhost:8090/realms/master"
echo "   Pyneuro Realm: http://localhost:8090/realms/pyneuro"
echo ""
echo "🔍 Next Steps:"
echo "   1. Verify realms at http://localhost:8090/admin"
echo "   2. Test authentication with your applications"
echo "   3. Check JWKS endpoint: http://localhost:8090/realms/pyneuro/protocol/openid-connect/certs"
echo ""
