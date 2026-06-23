# OAuth2 Swagger UI Redirect Fix

## Problem

When clicking "Authorize" in Swagger UI, you get redirected to:

```
http://localhost:8080/realms/mario-pizzeria/protocol/openid-connect/auth?
  response_type=code
  &client_id=mario-app
  &redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fapi%2Fdocs%2Foauth2-redirect  ❌ WRONG PORT
  &scope=openid%20profile%20email%20openid%20profile%20email
  &state=...
  &code_challenge=...
  &code_challenge_method=S256
```

The `redirect_uri` is pointing to `localhost:8080` (Keycloak port) instead of `localhost:8000` (your app port).

## Root Cause

The `swagger_ui_init_oauth` configuration was missing the `authorizationUrl` and `tokenUrl` parameters. Without these, Swagger UI defaults to using the same host/port as the authorization server.

## Solution

### 1. Added `app_url` setting

Added a new setting to track where the application is accessible from outside Docker:

```python
# application/settings.py
class MarioPizzeriaApplicationSettings(ApplicationSettings):
    app_url: str = "http://localhost:8080"  # External URL (Docker port mapping 8080:8080)
```

### 2. Fixed `swagger_ui_jwt_authority` Computed Field

Updated to use the correct Keycloak port (8090) for browser access:

```python
@computed_field
def swagger_ui_jwt_authority(self) -> str:
    """External Keycloak authority URL (for browser/Swagger UI)"""
    if self.local_dev:
        # Development: Browser connects to localhost:8090 (Keycloak Docker port mapping)
        return f"http://localhost:8090/realms/{self.keycloak_realm}"
    else:
        # Production: Browser connects to public Keycloak URL
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}"
```

### 3. Fixed Swagger UI OAuth Configuration

Updated `api/services/openapi.py` to include the authorization and token URLs:

```python
app.swagger_ui_init_oauth = {
    "clientId": settings.swagger_ui_client_id,
    "appName": settings.app_name,
    "usePkceWithAuthorizationCodeGrant": True,
    "scopes": settings.required_scope,  # "openid profile email"
    # CRITICAL: These URLs tell Swagger UI where Keycloak is
    "authorizationUrl": settings.swagger_ui_authorization_url,  # http://localhost:8090/realms/.../auth
    "tokenUrl": settings.swagger_ui_token_url,  # http://localhost:8090/realms/.../token
}
```

Without the `authorizationUrl` and `tokenUrl`, Swagger UI couldn't properly construct the OAuth2 redirect URI.

### 3. Keycloak Client Configuration

**CRITICAL**: You must configure the Keycloak client to accept redirects from your app.

In Keycloak Admin Console:

1. **Open**: http://localhost:8090 (admin/admin)
2. Navigate to: **Realm: mario-pizzeria → Clients → mario-app**
3. Add to **Valid Redirect URIs**:

   ```
   http://localhost:8080/*
   http://localhost:8080/api/docs/oauth2-redirect
   ```

4. Set **Web Origins**:

   ```
   http://localhost:8080
   ```

5. **Access Type**: Public (for browser apps without backend secret)
6. **Save**

## How OAuth2 Flow Works

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User clicks "Authorize" in Swagger UI                       │
│     http://localhost:8080/api/docs                              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Swagger UI redirects browser to Keycloak                    │
│     http://localhost:8090/realms/mario-pizzeria/.../auth        │
│     with redirect_uri=http://localhost:8080/api/docs/oauth2... │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. User logs in to Keycloak                                    │
│     Username/password or SSO                                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Keycloak redirects back with authorization code             │
│     http://localhost:8080/api/docs/oauth2-redirect?code=...    │
│     ✅ This must match Valid Redirect URIs in Keycloak          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Swagger UI exchanges code for access token                  │
│     POST http://localhost:8090/realms/.../token                 │
│     (PKCE code verifier + authorization code)                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. Swagger UI stores token and includes in API requests        │
│     Authorization: Bearer <access_token>                        │
└─────────────────────────────────────────────────────────────────┘
```

## Testing Steps

### 1. Restart Your Application

```bash
docker-compose down
docker-compose up
```

### 2. Open Swagger UI

Navigate to: http://localhost:8080/api/docs

### 3. Click "Authorize" Button

You should see:

- Client ID: `mario-app`
- Available scopes: `openid`, `profile`, `email`
- ✅ Authorization endpoint should be visible

### 4. Click "Authorize" to Start OAuth Flow

The redirect should now go to:

```
# OAuth2 Swagger UI Redirect Fix

## Problem

When clicking "Authorize" in Swagger UI, you get redirected to:
```

http://localhost:8090/realms/mario-pizzeria/protocol/openid-connect/auth?
response_type=code
&client_id=mario-app
&redirect_uri=http%3A%2F%2Flocalhost%3A8090%2Fapi%2Fdocs%2Foauth2-redirect ❌ WRONG - points to Keycloak
&scope=openid%20profile%20email
&state=...
&code_challenge=...
&code_challenge_method=S256

````

The `redirect_uri` is pointing to `localhost:8090` (Keycloak port) instead of `localhost:8080` (your app port).

## Docker Port Mappings (IMPORTANT!)

From `docker-compose.mario.yml`:
```yaml
services:
  mario-pizzeria-app:
    ports:
      - 8080:8080  # App accessible at localhost:8080

  keycloak:
    ports:
      - 8090:8080  # Keycloak accessible at localhost:8090
````

**From outside Docker (browser):**

- 🍕 **Mario's Pizzeria App**: http://localhost:8080
- 🔐 **Keycloak**: http://localhost:8090

**Inside Docker network:**

- 🍕 **Mario's Pizzeria App**: http://mario-pizzeria-app:8080
- 🔐 **Keycloak**: http://keycloak:8080

### 4. Click "Authorize" to Start OAuth Flow

The redirect should now go to Keycloak at port 8090 with redirect_uri pointing to your app at port 8080:

```
http://localhost:8090/realms/mario-pizzeria/protocol/openid-connect/auth?
  response_type=code
  &client_id=mario-app
  &redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fapi%2Fdocs%2Foauth2-redirect  ✅ CORRECT
  &scope=openid%20profile%20email
  &state=...
  &code_challenge=...
  &code_challenge_method=S256
```

Notice: Authorization URL uses `localhost:8090` (Keycloak), redirect_uri uses `localhost:8080` (your app).

### 5. Login to Keycloak

If you don't have a user:

```bash
# Create a test user in Keycloak
docker exec -it mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password admin

docker exec -it mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh create users \
  -r mario-pizzeria \
  -s username=testuser \
  -s enabled=true

docker exec -it mario-pizzeria-keycloak-1 /opt/keycloak/bin/kcadm.sh set-password \
  -r mario-pizzeria \
  --username testuser \
  --new-password test123
```

### 6. After Login

- Should redirect back to Swagger UI
- Token should be stored
- Lock icons should turn from "unlocked" to "locked"
- Protected endpoints (`/api/profile/me`) should now work

### 7. Test Protected Endpoint

Try calling `GET /api/profile/me`:

- Click "Try it out"
- Click "Execute"
- Should return your profile (or 404 if no profile exists yet)

## Troubleshooting

### Issue: "Invalid redirect_uri"

**Symptom**: Keycloak shows error page "Invalid parameter: redirect_uri"

**Solution**: Add `http://localhost:8080/*` to Valid Redirect URIs in Keycloak client configuration.

### Issue: "CORS error" in browser console

**Symptom**: Browser blocks the token request

**Solution**: Add `http://localhost:8080` to Web Origins in Keycloak client configuration.

### Issue: "Invalid client credentials"

**Symptom**: Token exchange fails

**Solution**:

- If using **Public** client: Remove `swagger_ui_client_secret` from settings (set to empty string)
- If using **Confidential** client: Set correct secret in both Keycloak and `swagger_ui_client_secret`

### Issue: Still redirecting to wrong port

**Symptom**: Redirect URI still shows wrong port after changes

**Solution**:

1. Clear browser cache (Swagger UI caches OpenAPI spec)
2. Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
3. Restart application to regenerate OpenAPI spec
4. Check browser DevTools → Network tab to see actual redirect URL

### Issue: "Not Found" from Keycloak

**Symptom**: Keycloak returns 404 on authorization endpoint

**Solution**: Check that:

- Keycloak is running: `docker ps | grep keycloak`
- Realm name is correct: `mario-pizzeria`
- Client ID exists in that realm
- Authorization URL is correct: `http://localhost:8090/realms/mario-pizzeria/protocol/openid-connect/auth`

## Environment Variables Override

For production or different environments:

```bash
# .env file
APP_URL=https://pizza.example.com
KEYCLOAK_SERVER_URL=http://keycloak:8080
LOCAL_DEV=false  # Use same URL for browser and backend
```

## Expected URLs After Fix

| Setting                    | Development Value                                | Production Value                                     |
| -------------------------- | ------------------------------------------------ | ---------------------------------------------------- |
| `app_url`                  | `http://localhost:8080`                          | `https://pizza.example.com`                          |
| `keycloak_server_url`      | `http://keycloak:8080`                           | `http://keycloak:8080` (internal)                    |
| `jwt_authority`            | `http://keycloak:8080/realms/mario-pizzeria`     | Same (internal)                                      |
| `swagger_ui_jwt_authority` | `http://localhost:8090/realms/mario-pizzeria`    | `https://keycloak.example.com/realms/mario-pizzeria` |
| Redirect URI               | `http://localhost:8080/api/docs/oauth2-redirect` | `https://pizza.example.com/api/docs/oauth2-redirect` |

## Files Changed

- ✅ `application/settings.py` - Added `app_url` setting
- ✅ `api/services/openapi.py` - Added `authorizationUrl` and `tokenUrl` to `swagger_ui_init_oauth`

## Next Steps

1. ✅ Fixed settings to use correct ports (app:8080, keycloak:8090)
2. ⏳ Configure Keycloak client Valid Redirect URIs (http://localhost:8080/\*)
3. ⏳ Test full OAuth2 flow in Swagger UI
4. ⏳ Test protected endpoints with token
5. ⏳ Create Keycloak test users if needed
