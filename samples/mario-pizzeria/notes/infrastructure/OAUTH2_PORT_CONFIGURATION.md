# OAuth2 Port Configuration - Final Summary

## Corrected Port Mappings

Based on `docker-compose.mario.yml`:

```yaml
services:
  mario-pizzeria-app:
    ports:
      - 8080:8080 # Host:Container - App accessible at localhost:8080

  keycloak:
    ports:
      - 8090:8080 # Host:Container - Keycloak accessible at localhost:8090
```

## Access URLs

### From Browser (Outside Docker)

| Service              | URL                            | Notes              |
| -------------------- | ------------------------------ | ------------------ |
| **Mario's Pizzeria** | http://localhost:8080          | Main application   |
| **Swagger UI**       | http://localhost:8080/api/docs | API documentation  |
| **Keycloak**         | http://localhost:8090          | Identity provider  |
| **Keycloak Admin**   | http://localhost:8090          | Login: admin/admin |
| **MongoDB Express**  | http://localhost:8081          | Database admin UI  |

### From Backend (Inside Docker Network)

| Service              | URL                            | Notes          |
| -------------------- | ------------------------------ | -------------- |
| **Mario's Pizzeria** | http://mario-pizzeria-app:8080 | Container name |
| **Keycloak**         | http://keycloak:8080           | Container name |
| **MongoDB**          | mongodb://mongodb:27017        | Container name |

## Application Settings (Corrected)

```python
# application/settings.py
class MarioPizzeriaApplicationSettings(ApplicationSettings):
    # External access (from browser)
    app_url: str = "http://localhost:8080"  # ✅ CORRECT - matches Docker port mapping
    local_dev: bool = True

    # Internal Docker network access (from backend)
    keycloak_server_url: str = "http://keycloak:8080"  # ✅ CORRECT - internal hostname
    keycloak_realm: str = "mario-pizzeria"
    keycloak_client_id: str = "mario-app"

    # JWT validation
    jwt_audience: str = "mario-app"  # Must match client_id
    required_scope: str = "openid profile email"

    # Computed fields
    @computed_field
    def jwt_authority(self) -> str:
        """Internal: http://keycloak:8080/realms/mario-pizzeria"""
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}"

    @computed_field
    def swagger_ui_jwt_authority(self) -> str:
        """External: http://localhost:8090/realms/mario-pizzeria"""
        if self.local_dev:
            return f"http://localhost:8090/realms/{self.keycloak_realm}"  # ✅ CORRECT - Keycloak port
        else:
            return self.jwt_authority
```

## OAuth2 Flow (Corrected)

```
1. Browser opens Swagger UI
   → http://localhost:8080/api/docs

2. User clicks "Authorize"
   → Swagger redirects to Keycloak
   → http://localhost:8090/realms/mario-pizzeria/protocol/openid-connect/auth
   → With redirect_uri=http://localhost:8080/api/docs/oauth2-redirect

3. User logs in to Keycloak
   → At http://localhost:8090

4. Keycloak redirects back with code
   → http://localhost:8080/api/docs/oauth2-redirect?code=...

5. Swagger UI exchanges code for token
   → POST http://localhost:8090/realms/mario-pizzeria/protocol/openid-connect/token

6. Token is stored and used in API calls
   → Authorization: Bearer <token>
```

## Keycloak Client Configuration

In Keycloak Admin Console (http://localhost:8090):

**Realm**: mario-pizzeria
**Client**: mario-app

**Settings**:

- **Valid Redirect URIs**:
  - `http://localhost:8080/*`
  - `http://localhost:8080/api/docs/oauth2-redirect`
- **Web Origins**:
  - `http://localhost:8080`
- **Access Type**: Public
- **Standard Flow Enabled**: ON
- **Direct Access Grants Enabled**: ON

## Key Points

1. **App Port 8080**: The application is accessible at `localhost:8080` (not 8000!)
2. **Keycloak Port 8090**: Keycloak is accessible at `localhost:8090` (not 8080!)
3. **Internal vs External**: Backend uses `http://keycloak:8080`, browser uses `http://localhost:8090`
4. **Redirect URI**: Must point to app port 8080: `http://localhost:8080/api/docs/oauth2-redirect`
5. **Authorization URL**: Must point to Keycloak port 8090: `http://localhost:8090/realms/.../auth`

## Changes Made

### application/settings.py

```python
# BEFORE (WRONG)
app_url: str = "http://localhost:8000"  # ❌ Wrong port
swagger_ui_jwt_authority = "http://localhost:8080/realms/..."  # ❌ Wrong - this is app port

# AFTER (CORRECT)
app_url: str = "http://localhost:8080"  # ✅ Matches Docker mapping
swagger_ui_jwt_authority = "http://localhost:8090/realms/..."  # ✅ Matches Keycloak mapping
```

### api/services/openapi.py

```python
# Added authorization and token URLs
app.swagger_ui_init_oauth = {
    "clientId": settings.swagger_ui_client_id,
    "appName": settings.app_name,
    "usePkceWithAuthorizationCodeGrant": True,
    "scopes": settings.required_scope,
    # These point to Keycloak at port 8090
    "authorizationUrl": settings.swagger_ui_authorization_url,
    "tokenUrl": settings.swagger_ui_token_url,
}
```

## Testing Checklist

- [ ] Restart Docker containers: `docker-compose down && docker-compose up`
- [ ] Open Swagger UI: http://localhost:8080/api/docs
- [ ] Click "Authorize" button (should be visible)
- [ ] Verify redirect to http://localhost:8090 (Keycloak)
- [ ] Login with test user
- [ ] Verify redirect back to http://localhost:8080 (app)
- [ ] Token should be stored in Swagger UI
- [ ] Call protected endpoint `/api/profile/me`
- [ ] Should return 200 OK with profile data (or 404 if no profile)

## Common Mistakes to Avoid

1. ❌ Using `localhost:8000` - **There is no service on port 8000**
2. ❌ Pointing browser to `http://keycloak:8080` - **This hostname only works inside Docker**
3. ❌ Setting redirect URI to Keycloak port (8090) instead of app port (8080)
4. ❌ Forgetting to configure Valid Redirect URIs in Keycloak client
5. ❌ Using the same port for both internal and external Keycloak URLs

## Production Configuration

For production, you'd use:

```python
# .env
APP_URL=https://pizza.example.com
LOCAL_DEV=false
KEYCLOAK_SERVER_URL=http://keycloak:8080  # Still internal Docker network
```

Then `swagger_ui_jwt_authority` would automatically use the public Keycloak URL based on `LOCAL_DEV=false`.
