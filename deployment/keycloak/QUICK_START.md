# Keycloak Quick Start Guide

## ✅ Current Status

The master realm SSL requirement has been **disabled**. You can now access the admin console!

## 🚀 Access Admin Console

1. **Open Browser**: http://localhost:8090
2. **Click**: "Administration Console"
3. **Login**:
   - Username: `admin`
   - Password: `admin`
4. **Success**: You should see the Keycloak admin dashboard

## 📋 Next Steps: Configure OAuth2 Client

### 1. Configure mario-app Client

Navigate to: **mario-pizzeria realm** → **Clients** → **mario-app**

#### Required Settings

**Valid Redirect URIs:**

```
http://localhost:8080/*
http://localhost:8080/api/docs/oauth2-redirect
```

**Web Origins:**

```
http://localhost:8080
```

**Access Type:**

```
Public
```

**Standard Flow Enabled:** ✅ (should already be enabled)

**Direct Access Grants Enabled:** ✅ (optional, for testing)

Click **Save**

### 2. Test OAuth2 in Swagger UI

1. **Open**: http://localhost:8080/api/docs
2. **Verify**: "Authorize" button is visible at top right
3. **Click**: "Authorize"
4. **Login**: Use test credentials:
   - Username: `customer` (or `chef`, `manager`)
   - Password: `test`
5. **Success**: You should be redirected back and see "Authorized" status

### 3. Test Protected Endpoint

Try calling: **GET /api/profile/me**

Expected outcomes:

- **200 OK**: If profile exists for the logged-in user
- **404 Not Found**: If no profile exists (expected for new users)
- **401 Unauthorized**: If token is invalid or expired

## 🔧 Container Restart Procedure

⚠️ **Important**: If you restart/remove the Keycloak container, you'll need to reconfigure the master realm.

```bash
# 1. Start services
docker-compose -f docker-compose.mario.yml up -d

# 2. Wait for Keycloak to be ready
sleep 25

# 3. Configure master realm SSL (if needed)
./deployment/keycloak/configure-master-realm.sh

# 4. Verify configuration
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired
# Should show: "sslRequired" : "NONE"
```

## 📝 Test Users

The mario-pizzeria realm has these pre-configured test users:

| Username | Password | Role     | Description                           |
| -------- | -------- | -------- | ------------------------------------- |
| customer | test     | customer | Regular customer, can place orders    |
| chef     | test     | chef     | Kitchen staff, can view/manage orders |
| manager  | test     | manager  | Manager, full access                  |

## 🐛 Troubleshooting

### Can't Access Admin Console

**Symptom**: "HTTPS required" error

**Solution**:

```bash
# Check master realm SSL setting
docker exec mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired

# If not "NONE", run configuration script
./deployment/keycloak/configure-master-realm.sh
```

### OAuth2 Login Fails in Swagger

**Symptom**: "Invalid redirect URI" or "Not Found"

**Solution**: Verify mario-app client configuration:

1. Check Valid Redirect URIs include `http://localhost:8080/api/docs/oauth2-redirect`
2. Check Web Origins include `http://localhost:8080`
3. Ensure Standard Flow is enabled

### Token Validation Fails

**Symptom**: 401 Unauthorized even with valid login

**Check**:

```bash
# Verify app settings match Keycloak configuration
cat samples/mario-pizzeria/application/settings.py | grep -E "keycloak|jwt|oauth"
```

Settings should show:

- `keycloak_realm: "mario-pizzeria"`
- `keycloak_client_id: "mario-app"`
- `jwt_audience: "mario-app"`

## 📚 Related Documentation

- **OAuth2 Setup**: See `/notes/KEYCLOAK_MASTER_REALM_SSL_FIX.md`
- **Application Settings**: `samples/mario-pizzeria/application/settings.py`
- **OAuth2 Scheme**: `samples/mario-pizzeria/api/services/oauth2_scheme.py`

## ✨ Quick Test Command

```bash
# Test OAuth2 flow with curl (get access token)
curl -X POST "http://localhost:8090/realms/mario-pizzeria/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=mario-app" \
  -d "grant_type=password" \
  -d "username=customer" \
  -d "password=test" \
  -d "scope=openid profile email"
```

This should return a JSON response with `access_token`, `refresh_token`, etc.
