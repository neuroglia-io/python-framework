# OAuth2 Swagger UI Integration

## Current Status

**Problem**: Swagger UI doesn't show the "Authorize" button or lock icons on protected endpoints.

**Root Cause**: The `oauth2_scheme.py` file references ApplicationSettings attributes that don't exist:

- `app_settings.jwt_audience`
- `app_settings.jwt_authority`
- `app_settings.jwt_signing_key`
- `app_settings.jwt_authorization_url`
- `app_settings.jwt_token_url`
- `app_settings.swagger_ui_authorization_url`
- `app_settings.swagger_ui_token_url`
- `app_settings.local_dev`
- `app_settings.oauth2_scheme`
- `app_settings.required_scope`

**Current ApplicationSettings** (`application/settings.py`) only has:

```python
class ApplicationSettings(BaseSettings):
    # JWT (for API)
    jwt_secret_key: str = "change-me-in-production-please-use-strong-jwt-key-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Keycloak (Authentication)
    keycloak_server_url: str = "http://keycloak:8080"
    keycloak_realm: str = "mario-pizzeria"
    keycloak_client_id: str = "mario-app"
    keycloak_client_secret: str = "mario-secret-123"

    # OAuth (optional - for future SSO)
    oauth_enabled: bool = False
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_authorization_url: str = ""
    oauth_token_url: str = ""
```

## Current Implementation

**ProfileController** has been updated to use OAuth2:

```python
from api.oauth2_scheme import validate_token
from fastapi import Depends

class ProfileController(ControllerBase):
    @get("/me", response_model=CustomerProfileDto)
    async def get_my_profile(self, token: dict = Depends(validate_token)):
        """Get current user's profile (requires authentication)"""
        user_id = self._get_user_id_from_token(token)  # Extracts token["sub"]
        # ... rest of logic
```

**Endpoints Updated**:

- ✅ `GET /api/profile/me` - Get current user profile
- ✅ `POST /api/profile` - Create profile
- ✅ `PUT /api/profile/me` - Update profile
- ✅ `GET /api/profile/me/orders` - Get user's orders

**main.py** has basic Swagger OAuth configuration:

```python
swagger_ui_init_oauth = None
if app_settings.oauth_enabled:
    swagger_ui_init_oauth = {
        "clientId": app_settings.keycloak_client_id,
        "appName": "Mario's Pizzeria API",
        "usePkceWithAuthorizationCodeGrant": True,
    }

api_app = FastAPI(
    title="Mario's Pizzeria API",
    description="Pizza ordering and management API with OAuth2/JWT authentication",
    version="1.0.0",
    docs_url="/docs",
    debug=True,
    swagger_ui_init_oauth=swagger_ui_init_oauth,
)
```

## Solution Options

### Option 1: Fix ApplicationSettings (RECOMMENDED)

Add missing OAuth2-related settings to `application/settings.py`:

```python
class ApplicationSettings(BaseSettings):
    # ... existing fields ...

    # JWT (for API) - Enhanced
    jwt_secret_key: str = "change-me-in-production-please-use-strong-jwt-key-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # OAuth2/Keycloak Configuration
    jwt_signing_key: str = ""  # Public key from Keycloak, auto-discovered if empty
    jwt_authority: str = "http://keycloak:8080/realms/mario-pizzeria"  # OIDC issuer
    jwt_audience: str = "mario-app"  # Expected audience in token
    jwt_authorization_url: str = "http://keycloak:8080/realms/mario-pizzeria/protocol/openid-connect/auth"
    jwt_token_url: str = "http://keycloak:8080/realms/mario-pizzeria/protocol/openid-connect/token"

    # Swagger UI OAuth Configuration
    swagger_ui_authorization_url: str = "http://localhost:8080/realms/mario-pizzeria/protocol/openid-connect/auth"
    swagger_ui_token_url: str = "http://localhost:8080/realms/mario-pizzeria/protocol/openid-connect/token"
    local_dev: bool = True  # Use localhost URLs for Swagger UI

    # OAuth2 Scheme
    oauth2_scheme: str = "authorization_code"  # or "client_credentials"
    required_scope: str = "openid profile email"  # Required OAuth2 scopes
```

**Benefits**:

- Works with existing `oauth2_scheme.py` without changes
- Full OAuth2 functionality with auto-discovery
- Swagger UI will automatically show "Authorize" button
- Lock icons will appear on protected endpoints

### Option 2: Simplify oauth2_scheme.py

Create a simplified version that works with current ApplicationSettings:

```python
# api/oauth2_scheme_simple.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from application.settings import app_settings

# Simple bearer token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def validate_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Simple JWT validation"""
    try:
        payload = jwt.decode(
            token,
            app_settings.jwt_secret_key,
            algorithms=[app_settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

**Tradeoffs**:

- Simpler but less secure (uses symmetric key, not Keycloak RSA)
- No Keycloak integration
- No OAuth2 Authorization Code flow
- Still shows Swagger UI "Authorize" button

### Option 3: Use Header-Based Auth (Current Workaround)

Revert to the original `X-User-Id` header approach:

```python
async def get_my_profile(self, x_user_id: str | None = Header(None, alias="X-User-Id")):
    """Get current user's profile"""
    user_id = self._get_user_id_from_header(x_user_id)
```

**Tradeoffs**:

- No real authentication (just trust the header)
- Swagger UI won't show OAuth2 features
- Simple for development/testing

## Recommended Next Steps

1. **Update ApplicationSettings** with missing OAuth2 fields (Option 1)
2. **Test oauth2_scheme.py** to ensure it works with updated settings
3. **Verify Swagger UI** shows "Authorize" button and lock icons
4. **Update remaining controllers** (OrdersController, KitchenController) to use OAuth2
5. **Test end-to-end authentication flow**:
   - Login to Keycloak
   - Get JWT token
   - Use token in Swagger UI "Authorize" button
   - Call protected endpoints
   - Verify token validation works

## Current Code Changes Made

### main.py

```python
# Added Swagger OAuth configuration (conditional on oauth_enabled flag)
swagger_ui_init_oauth = None
if app_settings.oauth_enabled:
    swagger_ui_init_oauth = {
        "clientId": app_settings.keycloak_client_id,
        "appName": "Mario's Pizzeria API",
        "usePkceWithAuthorizationCodeGrant": True,
    }
```

### profile_controller.py

- ✅ All 4 endpoints updated to use `token: dict = Depends(validate_token)`
- ✅ Changed `_get_user_id_from_header()` to `_get_user_id_from_token()` (extracts `token["sub"]`)
- ✅ Updated docstrings to indicate "(requires authentication)"

## Testing Checklist

Once ApplicationSettings is fixed:

- [ ] Application starts without errors
- [ ] Navigate to http://localhost:8000/api/docs
- [ ] **"Authorize" button visible** at top of Swagger UI
- [ ] **Lock icons visible** on protected endpoints (/api/profile/me, etc.)
- [ ] Click "Authorize" button
- [ ] Keycloak login flow works
- [ ] Token is stored in Swagger UI
- [ ] Protected endpoints can be called with token
- [ ] Endpoints without token return 401 Unauthorized
- [ ] Invalid tokens return 401 Unauthorized
- [ ] Expired tokens return 401 Unauthorized

## References

- **FastAPI OAuth2 Documentation**: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- **Keycloak Documentation**: https://www.keycloak.org/docs/latest/securing_apps/
- **JWT.io**: https://jwt.io/ (for token debugging)
- **oauth2_scheme.py**: Current OAuth2 implementation (needs matching settings)
- **ApplicationSettings**: `samples/mario-pizzeria/application/settings.py`
