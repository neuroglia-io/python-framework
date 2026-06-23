# OAuth2 Settings Simplification

## Overview

Simplified and cleaned up the OAuth2/Keycloak configuration to remove duplicates and clarify the distinction between internal (Docker network) and external (browser) URLs.

## Key Concepts

### Internal vs External URLs

**Internal URLs** (`keycloak_*` settings):

- Used by **backend services** running inside Docker containers
- Access Keycloak via Docker network hostname (e.g., `http://keycloak:8080`)
- Used for **server-side token validation** in `oauth2_scheme.py`

**External URLs** (`swagger_ui_*` computed fields):

- Used by **browser/Swagger UI** for OAuth2 flows
- Access Keycloak via localhost or public URL (e.g., `http://localhost:8080`)
- Controlled by `local_dev` flag:
  - `local_dev=True` → Browser uses `http://localhost:8080`
  - `local_dev=False` → Browser uses public Keycloak URL

### Why This Separation Matters

In Docker/Kubernetes environments:

```
┌─────────────────────────────────────────────────────┐
│  Docker Network                                      │
│                                                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │   Backend    │────────→│   Keycloak   │         │
│  │   (Python)   │  http:// │   (8080)     │         │
│  │              │  keycloak│              │         │
│  └──────────────┘         └──────────────┘         │
│         ↑                         ↑                  │
└─────────┼─────────────────────────┼──────────────────┘
          │                         │
          │ REST API       OAuth2 Flow (browser)
          │                         │
    ┌─────┴─────────────────────────┴─────┐
    │         Browser/Swagger UI           │
    │    http://localhost:8000/api/docs    │
    │    http://localhost:8080 (Keycloak)  │
    └──────────────────────────────────────┘
```

## Settings Structure

### Before (Duplicates & Confusion)

```python
# Multiple conflicting settings for same purpose
keycloak_server_url: str = "http://keycloak:8080"
keycloak_realm: str = "mario-pizzeria"
keycloak_client_id: str = "mario-app"

# Duplicate JWT settings with different realm!
jwt_authority: str = "http://localhost:8080/realms/mozart"  # ❌ Wrong realm
jwt_audience: str = "mario-pizzeria"  # ❌ Doesn't match client_id

# Duplicate Swagger settings
swagger_ui_jwt_authority: str = "http://localhost:9990/realms/mozart"  # ❌ Wrong realm & port
swagger_ui_client_id: str = "mario-pizzeria"  # ❌ Doesn't match client_id

# Unused OAuth settings
oauth_enabled: bool = False  # ❌ Not used
oauth_client_id: str = ""
oauth_authorization_url: str = ""
```

### After (Clean & Consistent)

```python
class MarioPizzeriaApplicationSettings(ApplicationSettings):
    # Base Configuration (source of truth)
    keycloak_server_url: str = "http://keycloak:8080"  # Internal Docker URL
    keycloak_realm: str = "mario-pizzeria"
    keycloak_client_id: str = "mario-app"
    keycloak_client_secret: str = "mario-secret-123"

    # JWT Validation
    jwt_signing_key: str = ""  # Auto-discovered from Keycloak
    jwt_audience: str = "mario-app"  # Must match client_id
    required_scope: str = "openid profile email"

    # OAuth2 Flow Type
    oauth2_scheme: str = "authorization_code"

    # Development vs Production
    local_dev: bool = True  # Browser uses localhost URLs

    # Swagger UI (for public clients)
    swagger_ui_client_id: str = "mario-app"  # Must match client_id
    swagger_ui_client_secret: str = ""  # Empty for public clients

    # Computed Fields (auto-generated, no duplication!)
    @computed_field
    def jwt_authority(self) -> str:
        """Internal: http://keycloak:8080/realms/mario-pizzeria"""
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}"

    @computed_field
    def swagger_ui_jwt_authority(self) -> str:
        """External: http://localhost:8080/realms/mario-pizzeria (dev)"""
        if self.local_dev:
            return f"http://localhost:8080/realms/{self.keycloak_realm}"
        else:
            return self.jwt_authority  # Production uses same as backend
```

## Removed Settings

**Deleted (not used anywhere):**

- ✂️ `oauth_enabled` - OAuth2 is always enabled now
- ✂️ `oauth_client_id` - Replaced by `keycloak_client_id`
- ✂️ `oauth_client_secret` - Replaced by `keycloak_client_secret`
- ✂️ `oauth_authorization_url` - Now computed
- ✂️ `oauth_token_url` - Now computed
- ✂️ `jwt_secret_key` - Not needed for RSA/Keycloak validation
- ✂️ `jwt_algorithm` - Always RS256 for Keycloak
- ✂️ `jwt_expiration_minutes` - Controlled by Keycloak

**Converted to computed fields:**

- ✅ `jwt_authority` - Generated from `keycloak_server_url` + `keycloak_realm`
- ✅ `jwt_authorization_url` - Generated from `jwt_authority`
- ✅ `jwt_token_url` - Generated from `jwt_authority`
- ✅ `swagger_ui_jwt_authority` - Generated with localhost when `local_dev=True`
- ✅ `swagger_ui_authorization_url` - Generated from `swagger_ui_jwt_authority`
- ✅ `swagger_ui_token_url` - Generated from `swagger_ui_jwt_authority`

## Usage in Code

### oauth2_scheme.py

```python
# Uses both internal (backend) and external (browser) URLs
auth_url = (
    app_settings.swagger_ui_authorization_url  # Browser redirects here
    if app_settings.local_dev
    else app_settings.jwt_authorization_url  # Production
)

# Backend validates tokens using internal URL
discovered_key = await get_public_key(app_settings.jwt_authority)

# Validates audience matches client_id
expected_audience = app_settings.jwt_audience
```

### openapi.py

```python
# Swagger UI OAuth configuration
app.swagger_ui_init_oauth = {
    "clientId": settings.swagger_ui_client_id,  # mario-app
    "appName": settings.app_name,
    "usePkceWithAuthorizationCodeGrant": True,
    "scopes": settings.required_scope.split(),  # ["openid", "profile", "email"]
}
```

### main.py

```python
# Simple - all configuration comes from settings
api_app = FastAPI(title="Mario's Pizzeria API", ...)
set_oas_description(api_app, app_settings)  # Configures OAuth2 from settings
```

## Environment Variables

To override defaults via `.env` file:

```bash
# Development (default)
LOCAL_DEV=true
KEYCLOAK_SERVER_URL=http://keycloak:8080
KEYCLOAK_REALM=mario-pizzeria
KEYCLOAK_CLIENT_ID=mario-app
KEYCLOAK_CLIENT_SECRET=mario-secret-123
JWT_AUDIENCE=mario-app
REQUIRED_SCOPE=openid profile email
OAUTH2_SCHEME=authorization_code

# Production
LOCAL_DEV=false
KEYCLOAK_SERVER_URL=https://keycloak.production.com
KEYCLOAK_REALM=mario-pizzeria
KEYCLOAK_CLIENT_ID=mario-production-client
JWT_SIGNING_KEY=<RSA-PUBLIC-KEY>  # Optional, auto-discovered if empty
```

## Testing Checklist

- [x] Application starts without errors
- [ ] Navigate to http://localhost:8000/api/docs
- [ ] **"Authorize" button visible** at top of Swagger UI
- [ ] **Lock icons visible** on protected endpoints
- [ ] Click "Authorize" → Redirects to Keycloak login (localhost:8080)
- [ ] After login → Token stored in Swagger UI
- [ ] Protected endpoints work with token
- [ ] Invalid/missing tokens return 401

## Key Improvements

1. **Single Source of Truth**: Base config (`keycloak_*`) drives everything
2. **No Duplicates**: All URLs computed from base config
3. **Clear Separation**: Internal vs external URLs clearly documented
4. **Consistency**: Client IDs, realms, and audiences all match
5. **Flexibility**: `local_dev` flag controls browser URL behavior
6. **Auto-Discovery**: JWT signing key fetched from Keycloak automatically
7. **Type Safety**: Computed fields ensure URL format consistency

## Migration Guide

If you have an existing `.env` file:

**Remove these (no longer used):**

```bash
OAUTH_ENABLED=
OAUTH_CLIENT_ID=
OAUTH_AUTHORIZATION_URL=
JWT_SECRET_KEY=
JWT_ALGORITHM=
SWAGGER_UI_JWT_AUTHORITY=
```

**Rename these:**

```bash
# Old → New
KEYCLOAK_CLIENT_ID → SWAGGER_UI_CLIENT_ID (if different)
```

**Add these if needed:**

```bash
LOCAL_DEV=true  # For development
JWT_AUDIENCE=mario-app  # Must match client_id
OAUTH2_SCHEME=authorization_code
```

## Related Files Changed

- ✅ `application/settings.py` - Simplified from 85 lines to 75 lines
- ✅ `api/services/openapi.py` - Fixed type annotations, removed manual URL config
- ✅ `main.py` - Removed duplicate `oauth_enabled` check
- ✅ `api/oauth2_scheme.py` - No changes needed (works with new settings)

## References

- **Keycloak Docker Network**: https://www.keycloak.org/getting-started/getting-started-docker
- **FastAPI OAuth2**: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- **OpenAPI OAuth Configuration**: https://swagger.io/docs/specification/authentication/oauth2/
