#!/bin/bash
# Keycloak Master Realm SSL Configuration Script
# This script disables SSL requirement for the master realm in Keycloak
# Run this after Keycloak starts to allow HTTP access to admin console

set -e

echo "🔐 Configuring Keycloak master realm SSL settings..."

# Get the Keycloak container name
KEYCLOAK_CONTAINER=$(docker ps --filter "name=keycloak" --format "{{.Names}}" | head -n 1)

if [ -z "$KEYCLOAK_CONTAINER" ]; then
  echo "❌ Error: Keycloak container not found. Make sure it's running."
  exit 1
fi

echo "📦 Found Keycloak container: $KEYCLOAK_CONTAINER"

# Wait for Keycloak to be ready by checking logs
echo "⏳ Waiting for Keycloak to be ready..."
MAX_WAIT=60
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
  if docker logs "$KEYCLOAK_CONTAINER" 2>&1 | grep -q "Listening on:"; then
    echo "✅ Keycloak is ready"
    break
  fi
  echo "   Still waiting... ($COUNTER/$MAX_WAIT)"
  sleep 2
  COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq $MAX_WAIT ]; then
  echo "⚠️  Warning: Keycloak may not be fully ready, but proceeding anyway..."
fi

# Give it a few more seconds to stabilize
sleep 5

# Detect kcadm.sh location (different in various Keycloak versions)
echo "🔍 Detecting kcadm.sh location..."
if docker exec "$KEYCLOAK_CONTAINER" test -f /opt/keycloak/bin/kcadm.sh; then
  KCADM_PATH="/opt/keycloak/bin/kcadm.sh"
elif docker exec "$KEYCLOAK_CONTAINER" test -f /opt/jboss/keycloak/bin/kcadm.sh; then
  KCADM_PATH="/opt/jboss/keycloak/bin/kcadm.sh"
else
  echo "❌ Error: kcadm.sh not found in container"
  exit 1
fi

echo "✅ Found kcadm.sh at: $KCADM_PATH"

# Configure kcadm credentials with proper error handling
echo "📝 Configuring kcadm credentials..."
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if docker exec "$KEYCLOAK_CONTAINER" "$KCADM_PATH" config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user admin \
    --password admin 2>&1; then
    echo "✅ Successfully authenticated"
    break
  else
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
      echo "⚠️  Authentication failed, retrying in 5 seconds... (Attempt $RETRY_COUNT/$MAX_RETRIES)"
      sleep 5
    else
      echo "❌ Failed to authenticate after $MAX_RETRIES attempts"
      echo ""
      echo "🔍 Debugging information:"
      echo "Container logs (last 30 lines):"
      docker logs "$KEYCLOAK_CONTAINER" 2>&1 | tail -30
      exit 1
    fi
  fi
done

# Update master realm to disable SSL requirement
echo "🔓 Disabling SSL requirement for master realm..."
docker exec "$KEYCLOAK_CONTAINER" "$KCADM_PATH" update realms/master \
  -s sslRequired=NONE

# Check if pyneuro realm exists and configure it too
echo "🔍 Checking for pyneuro realm..."
if docker exec "$KEYCLOAK_CONTAINER" "$KCADM_PATH" get realms/pyneuro >/dev/null 2>&1; then
  echo "🔓 Disabling SSL requirement for pyneuro realm..."
  docker exec "$KEYCLOAK_CONTAINER" "$KCADM_PATH" update realms/pyneuro \
    -s sslRequired=NONE
  echo "✅ Pyneuro realm SSL configuration complete!"
else
  echo "⚠️  Pyneuro realm not found - importing from file..."
  if docker exec "$KEYCLOAK_CONTAINER" "$KCADM_PATH" create realms \
    -f /opt/keycloak/data/import/pyneuro-realm-export.json 2>&1; then
    echo "✅ Pyneuro realm imported successfully!"
    echo "🔓 Disabling SSL requirement for pyneuro realm..."
    docker exec "$KEYCLOAK_CONTAINER" "$KCADM_PATH" update realms/pyneuro \
      -s sslRequired=NONE
  else
    echo "❌ Failed to import pyneuro realm"
    echo "   Continuing anyway - manual import may be needed"
  fi
fi

echo "✅ Master realm SSL configuration complete!"

# Create test users with passwords
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/create-test-users.sh" ]; then
  echo ""
  echo "👥 Creating test users..."
  bash "$SCRIPT_DIR/create-test-users.sh"
else
  echo "⚠️  Test user creation script not found at: $SCRIPT_DIR/create-test-users.sh"
  echo "   You'll need to set passwords manually"
fi

echo ""
echo "🌐 You can now access the admin console at: http://localhost:8090"
echo ""
echo "📋 Next steps:"
echo "   1. Access admin console: http://localhost:8090/admin"
echo "   2. Username: admin"
echo "   3. Password: admin"
if docker exec "$KEYCLOAK_CONTAINER" "$KCADM_PATH" get realms/pyneuro >/dev/null 2>&1; then
  echo "   4. Pyneuro realm: http://localhost:8090/realms/pyneuro"
fi
