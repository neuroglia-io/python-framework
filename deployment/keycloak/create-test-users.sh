#!/bin/bash
#
# Create Test Users Script for Keycloak
#
# This script creates/updates test users in the pyneuro realm with passwords.
# Run this after importing the realm or resetting Keycloak.
#
# Usage: ./deployment/keycloak/create-test-users.sh

set -e

KEYCLOAK_CONTAINER="pyneuro-keycloak-1"
REALM="pyneuro"
KCADM="/opt/keycloak/bin/kcadm.sh"

echo "👥 Creating/Updating Test Users in Keycloak"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if Keycloak container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${KEYCLOAK_CONTAINER}$"; then
    echo "❌ Keycloak container '${KEYCLOAK_CONTAINER}' is not running"
    exit 1
fi

echo "📦 Found Keycloak container: $KEYCLOAK_CONTAINER"

# Authenticate
echo "🔐 Authenticating with Keycloak..."
docker exec "$KEYCLOAK_CONTAINER" "$KCADM" config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password admin >/dev/null 2>&1

echo "✅ Authenticated successfully"
echo ""

# Function to create or update user
create_or_update_user() {
    local username=$1
    local password=$2
    local firstname=$3
    local lastname=$4
    local email=$5

    echo "👤 Processing user: $username"

    # Check if user exists
    USER_ID=$(docker exec "$KEYCLOAK_CONTAINER" "$KCADM" get users -r "$REALM" \
        --fields id,username 2>/dev/null | jq -r ".[] | select(.username == \"$username\") | .id")

    if [ -z "$USER_ID" ]; then
        echo "   Creating new user..."
        # Create user
        docker exec "$KEYCLOAK_CONTAINER" "$KCADM" create users -r "$REALM" \
            -s username="$username" \
            -s enabled=true \
            -s firstName="$firstname" \
            -s lastName="$lastname" \
            -s email="$email" >/dev/null 2>&1

        # Get the new user ID
        USER_ID=$(docker exec "$KEYCLOAK_CONTAINER" "$KCADM" get users -r "$REALM" \
            --fields id,username 2>/dev/null | jq -r ".[] | select(.username == \"$username\") | .id")
    else
        echo "   User exists (ID: ${USER_ID:0:8}...)"
    fi

    # Set password
    echo "   Setting password..."
    docker exec "$KEYCLOAK_CONTAINER" "$KCADM" set-password -r "$REALM" \
        --username "$username" \
        --new-password "$password" >/dev/null 2>&1

    echo "   ✅ Password set for $username"
}

# Create/Update test users with default password "test"
echo "Creating test users with password 'test':"
echo ""

create_or_update_user "manager" "test" "System" "Manager" "manager@pyneuro.io"
create_or_update_user "chef" "test" "Mario" "Chef" "chef@pyneuro.io"
create_or_update_user "customer" "test" "Test" "Customer" "customer@pyneuro.io"
create_or_update_user "driver" "test" "Delivery" "Driver" "driver@pyneuro.io"
create_or_update_user "john.doe" "test" "John" "Doe" "john.doe@pyneuro.io"
create_or_update_user "jane.smith" "test" "Jane" "Smith" "jane.smith@pyneuro.io"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Test users created/updated successfully!"
echo ""
echo "📋 Available Test Users:"
echo "   • manager@pyneuro.io     / test"
echo "   • chef@pyneuro.io        / test"
echo "   • customer@pyneuro.io    / test"
echo "   • driver@pyneuro.io      / test"
echo "   • john.doe@pyneuro.io    / test"
echo "   • jane.smith@pyneuro.io  / test"
echo ""
echo "🔗 You can now login at:"
echo "   • Event Player: http://localhost:8085"
echo "   • Mario's Pizzeria: http://localhost:8080"
echo "   • Simple UI: http://localhost:8081"
echo ""
