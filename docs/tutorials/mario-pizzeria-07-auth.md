# Part 7: Authentication & Security

**Time: 30 minutes** | **Prerequisites: [Part 6](mario-pizzeria-06-persistence.md)**

In this tutorial, you'll secure your application with authentication and authorization. Mario's Pizzeria uses OAuth2/JWT for API authentication and Keycloak for SSO in the web UI.

## 🎯 What You'll Learn

- OAuth2 and JWT authentication basics
- Keycloak integration for SSO
- Role-based access control (RBAC)
- Protecting API endpoints
- Session vs token authentication

## 🔐 Authentication Strategies

Mario's Pizzeria uses **two authentication strategies**:

### API Authentication (JWT Tokens)

```
External Apps → JWT Token → API Endpoints
```

**Use case:** Mobile apps, external integrations

### UI Authentication (Keycloak SSO)

```
Web Users → Keycloak Login → Session Cookies → UI
```

**Use case:** Web interface, staff portal

## 🎫 JWT Authentication for API

### Step 1: Install Dependencies

```bash
poetry add python-jose[cryptography] passlib python-multipart
```

### Step 2: Create Authentication Service

Create `application/services/auth_service.py`:

```python
"""Authentication service"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext


class AuthService:
    """Handles authentication and token generation"""

    SECRET_KEY = "your-secret-key-here"  # Use environment variable in production!
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt

    def decode_token(self, token: str) -> Optional[dict]:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.SECRET_KEY,
                algorithms=[self.ALGORITHM]
            )
            return payload
        except JWTError:
            return None
```

### Step 3: Protect API Endpoints

Create `api/dependencies/auth.py`:

```python
"""Authentication dependencies"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from application.services import AuthService


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends()
):
    """
    Dependency to extract and verify JWT token.

    Usage:
        @get("/protected")
        async def protected_endpoint(user = Depends(get_current_user)):
            return {"user": user["username"]}
    """
    token = credentials.credentials
    payload = auth_service.decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def require_role(required_role: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @get("/admin")
        async def admin_endpoint(user = Depends(require_role("admin"))):
            return {"message": "Admin only"}
    """
    async def role_checker(user = Depends(get_current_user)):
        user_roles = user.get("roles", [])
        if required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return user

    return role_checker
```

### Step 4: Use in Controllers

```python
from fastapi import Depends
from api.dependencies.auth import get_current_user, require_role

class OrdersController(ControllerBase):

    @get(
        "/{order_id}",
        response_model=OrderDto,
        dependencies=[Depends(get_current_user)]  # Requires authentication
    )
    async def get_order(self, order_id: str):
        """Protected endpoint - requires valid JWT"""
        query = GetOrderByIdQuery(order_id=order_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @delete(
        "/{order_id}",
        dependencies=[Depends(require_role("admin"))]  # Requires admin role
    )
    async def delete_order(self, order_id: str):
        """Admin-only endpoint"""
        # Only admins can delete orders
        pass
```

## 🔑 Keycloak Integration for Web UI

### Step 1: Run Keycloak

```bash
# Using Docker
docker run -d \
  -p 8081:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:latest \
  start-dev
```

Access Keycloak admin: http://localhost:8081

### Step 2: Configure Keycloak Realm

1. Create realm: `mario-pizzeria`
2. Create client: `mario-pizzeria-web`
3. Create roles: `customer`, `staff`, `chef`, `admin`
4. Create test users with roles

### Step 3: Install Keycloak Client

```bash
poetry add python-keycloak
```

### Step 4: Keycloak Authentication Flow

Create `ui/middleware/keycloak_middleware.py`:

```python
"""Keycloak authentication middleware"""
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from fastapi import HTTPException, status


async def require_keycloak_auth(request: Request):
    """
    Middleware to enforce Keycloak authentication.

    Checks if user is authenticated via session.
    Redirects to Keycloak login if not.
    """
    user_id = request.session.get("user_id")
    authenticated = request.session.get("authenticated", False)

    if not authenticated or not user_id:
        # Redirect to Keycloak login
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/auth/login"}
        )

    return user_id
```

### Step 5: Session Configuration

In `main.py`:

```python
from starlette.middleware.sessions import SessionMiddleware

# UI sub-app with session support
builder.add_sub_app(
    SubAppConfig(
        path="/",
        name="ui",
        title="Mario's Pizzeria UI",
        middleware=[
            (
                SessionMiddleware,
                {
                    "secret_key": "your-secret-key",
                    "session_cookie": "mario_session",
                    "max_age": 3600,  # 1 hour
                    "same_site": "lax",
                    "https_only": False  # Set True in production
                }
            )
        ],
        controllers=["ui.controllers"],
    )
)
```

## 📝 Key Takeaways

1. **JWT for APIs**: Stateless authentication for external clients
2. **Keycloak for Web**: SSO with centralized user management
3. **RBAC**: Role-based access control with dependencies
4. **Session vs Token**: Sessions for web UI, tokens for API
5. **Security**: Always use HTTPS in production, rotate secrets

## 🚀 What's Next?

In [Part 8: Observability](mario-pizzeria-08-observability.md), you'll learn:

- OpenTelemetry integration
- Distributed tracing
- Metrics and monitoring
- Logging best practices

---

**Previous:** [← Part 6: Persistence](mario-pizzeria-06-persistence.md) | **Next:** [Part 8: Observability →](mario-pizzeria-08-observability.md)
