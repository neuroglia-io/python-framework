# Mario's Pizzeria - UI/API Separation Implementation Plan

## 📋 Current State Analysis

### What You've Done Well ✅

1. **UI Structure Setup**

   - Created `ui/` directory with proper separation
   - Set up Parcel bundler with `package.json` configuration
   - Created `ui/src/scripts/` for JavaScript modules
   - Started importing Bootstrap components selectively (good for bundle size)
   - Created `ui/templates/` for Jinja2 templates
   - Added `ui/controllers/home_controller.py` with session-based auth

2. **Multi-App Architecture**
   - Main app, API app, and UI app already separated in `main.py`
   - Services properly shared via `app.state.services`
   - Static files mounted on UI app

### Current Issues ⚠️

1. **Mixed Concerns**

   - `static/index.html` contains inline CSS and HTML (471 lines)
   - UI templates reference "Exam Record Manager" (copied from another project)
   - Session management in `home_controller.py` but no session middleware configured
   - No JWT setup for API authentication
   - Parcel build outputs not integrated into static serving

2. **Missing Infrastructure**

   - No session middleware (Starlette SessionMiddleware)
   - No JWT authentication for API
   - No auth controllers for login/logout/token endpoints
   - No Parcel build integration in deployment workflow
   - No `.gitignore` entries for node_modules, dist, .parcel-cache

3. **Architecture Confusion**
   - Both `static/index.html` and `ui/templates/home/index.html` exist
   - Unclear which should be used (static SPA vs SSR templates)
   - UI app mounted at `/ui/` but main app also serves root `/`

## 🎯 Recommended Architecture

### Option A: Hybrid Approach (RECOMMENDED)

**UI App (Session Cookies + SSR)**

- Server-side rendered Jinja2 templates
- Session-based authentication (HttpOnly cookies)
- Protected by session middleware
- Endpoints: `/`, `/orders`, `/menu`, `/kitchen`
- Uses: Customer-facing ordering interface

**API App (JWT Tokens + JSON)**

- Pure REST API with JSON responses
- JWT Bearer token authentication
- Protected by JWT middleware
- Endpoints: `/api/pizzas`, `/api/orders`, `/api/kitchen`
- Uses: Mobile apps, kiosks, external integrations, admin tools

**Why This Works:**

- ✅ Clear separation of concerns
- ✅ Optimal for different client types
- ✅ Security best practices (HttpOnly cookies for browsers, JWT for APIs)
- ✅ Future-proof (can serve both web and mobile clients)

## 📐 Detailed Implementation Plan

### Phase 1: Project Cleanup & Build Setup (1-2 hours)

#### 1.1 Configure Parcel Build Pipeline

```bash
# In samples/mario-pizzeria/ui/
npm install
```

**Update `ui/package.json`:**

```json
{
  "name": "mario-pizzeria-ui",
  "version": "1.0.0",
  "description": "UI for Mario's Pizzeria",
  "scripts": {
    "dev": "parcel watch 'src/scripts/app.js' 'src/styles/main.scss' --dist-dir ../static/dist --public-url /static/dist",
    "build": "parcel build 'src/scripts/app.js' 'src/styles/main.scss' --dist-dir ../static/dist --public-url /static/dist --no-source-maps",
    "clean": "rm -rf ../static/dist .parcel-cache"
  },
  "dependencies": {
    "bootstrap": "^5.3.2"
  },
  "devDependencies": {
    "@parcel/transformer-sass": "^2.10.3",
    "parcel": "^2.10.3",
    "sass": "^1.69.5"
  }
}
```

**Why:**

- Single entry point `app.js` and `main.scss`
- Outputs to `static/dist/` for easy FastAPI serving
- Public URL ensures correct asset paths

#### 1.2 Create Entry Point Files

**Create `ui/src/scripts/app.js`:**

```javascript
/**
 * Main entry point for Mario's Pizzeria UI
 */

// Import Bootstrap (tree-shaken)
import bootstrap from "./bootstrap.js";

// Import utilities
import * as utils from "./common.js";

// Import styles
import "../styles/main.scss";

// Make utilities available globally
window.pizzeriaUtils = utils;
window.bootstrap = bootstrap;

console.log("🍕 Mario's Pizzeria UI loaded");
```

**Create `ui/src/styles/main.scss`:**

```scss
// Import Bootstrap
@import "bootstrap/scss/bootstrap";

// Custom variables
$primary-color: #d32f2f;
$secondary-color: #2e7d32;

// Mario's Pizzeria custom styles
:root {
  --primary-color: #{$primary-color};
  --secondary-color: #{$secondary-color};
}

body {
  font-family: "Arial", sans-serif;
}

.navbar {
  background-color: var(--primary-color);
}

// Add more custom styles here
```

#### 1.3 Update `.gitignore`

**Add to root `.gitignore`:**

```gitignore
# Node/Parcel
node_modules/
.parcel-cache/
samples/mario-pizzeria/static/dist/
samples/mario-pizzeria/ui/dist/

# Static build artifacts
*.js.map
*.css.map
```

### Phase 2: Authentication Infrastructure (2-3 hours)

#### 2.1 Create Application Settings

**Create `application/settings.py`:**

```python
"""Application settings and configuration"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    """Application configuration"""

    # Application
    app_name: str = "Mario's Pizzeria"
    app_version: str = "1.0.0"
    debug: bool = True

    # Session (for UI)
    session_secret_key: str = "change-me-in-production-please-use-strong-key"
    session_max_age: int = 3600  # 1 hour

    # JWT (for API)
    jwt_secret_key: str = "change-me-in-production-please-use-strong-jwt-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # OAuth (optional - for future SSO)
    oauth_enabled: bool = False
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_authorization_url: str = ""
    oauth_token_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


app_settings = ApplicationSettings()
```

#### 2.2 Create Authentication Service

**Create `application/services/auth_service.py`:**

```python
"""Authentication service for both session and JWT"""
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext

from application.settings import app_settings


class AuthService:
    """Handles authentication for both UI (sessions) and API (JWT)"""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Password hashing
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    # JWT Token Management (for API)
    def create_jwt_token(
        self,
        user_id: str,
        username: str,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a JWT access token for API authentication"""
        payload = {
            "sub": user_id,
            "username": username,
            "exp": datetime.now(timezone.utc) + timedelta(
                minutes=app_settings.jwt_expiration_minutes
            ),
            "iat": datetime.now(timezone.utc),
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(
            payload,
            app_settings.jwt_secret_key,
            algorithm=app_settings.jwt_algorithm
        )

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token,
                app_settings.jwt_secret_key,
                algorithms=[app_settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    # User Authentication (placeholder - implement with real user repo)
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with username/password.

        TODO: Replace with real user repository lookup
        """
        # Placeholder - in production, query user repository
        if username == "demo" and password == "demo123":
            return {
                "id": "demo-user-id",
                "username": "demo",
                "email": "demo@mariospizzeria.com",
                "role": "customer"
            }
        return None
```

**Add dependencies to `pyproject.toml`:**

```toml
[tool.poetry.dependencies]
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.6"  # For form data
starlette = "^0.27.0"  # For SessionMiddleware
```

#### 2.3 Create API Authentication Middleware

**Create `api/middleware/jwt_middleware.py`:**

```python
"""JWT authentication middleware for API endpoints"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from application.services.auth_service import AuthService


security = HTTPBearer(auto_error=False)


class JWTAuthMiddleware:
    """Middleware to validate JWT tokens on API endpoints"""

    def __init__(self):
        self.auth_service = AuthService()

    async def __call__(self, request: Request, credentials: Optional[HTTPAuthorizationCredentials]):
        """Validate JWT token from Authorization header"""

        # Skip auth for docs and auth endpoints
        if request.url.path in ["/api/docs", "/api/openapi.json", "/api/auth/token"]:
            return None

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
        payload = self.auth_service.verify_jwt_token(token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Attach user info to request state
        request.state.user = payload
        return payload
```

#### 2.4 Create UI Session Middleware

**Create `ui/middleware/session_middleware.py`:**

```python
"""Session middleware for UI endpoints"""
from starlette.middleware.sessions import SessionMiddleware
from application.settings import app_settings


def get_session_middleware():
    """Get configured session middleware"""
    return SessionMiddleware(
        secret_key=app_settings.session_secret_key,
        max_age=app_settings.session_max_age,
        session_cookie="mario_session",  # Custom cookie name
        https_only=not app_settings.debug,  # HTTPS only in production
        same_site="lax",
    )
```

### Phase 3: Authentication Endpoints (2-3 hours)

#### 3.1 Create API Auth Controller

**Create `api/controllers/auth_controller.py`:**

```python
"""API authentication endpoints (JWT)"""
from classy_fastapi.decorators import post
from fastapi import HTTPException, status, Form
from pydantic import BaseModel

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase
from application.services.auth_service import AuthService


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthController(ControllerBase):
    """API authentication controller - JWT tokens"""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator
    ):
        super().__init__(service_provider, mapper, mediator)
        self.auth_service = AuthService()

    @post("/token", response_model=TokenResponse, tags=["Authentication"])
    async def login(
        self,
        username: str = Form(...),
        password: str = Form(...),
    ) -> TokenResponse:
        """
        OAuth2-compatible token endpoint for API authentication.

        Returns JWT access token for API requests.
        """
        user = await self.auth_service.authenticate_user(username, password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = self.auth_service.create_jwt_token(
            user_id=user["id"],
            username=user["username"],
            extra_claims={"role": user.get("role")}
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=3600
        )
```

#### 3.2 Create UI Auth Controller

**Create `ui/controllers/auth_controller.py`:**

```python
"""UI authentication endpoints (sessions)"""
from classy_fastapi.decorators import get, post
from fastapi import Request, Form, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase
from application.services.auth_service import AuthService


class UIAuthController(ControllerBase):
    """UI authentication controller - session cookies"""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator
    ):
        super().__init__(service_provider, mapper, mediator)
        self.auth_service = AuthService()

    @get("/login", response_class=HTMLResponse)
    async def login_page(self, request: Request) -> HTMLResponse:
        """Render login page"""
        return request.app.state.templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "title": "Login"}
        )

    @post("/login")
    async def login(
        self,
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        next_url: str = Form("/")
    ) -> RedirectResponse:
        """Process login form and create session"""
        user = await self.auth_service.authenticate_user(username, password)

        if not user:
            # Re-render login with error
            return request.app.state.templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "title": "Login",
                    "error": "Invalid username or password"
                },
                status_code=401
            )

        # Create session
        request.session["user_id"] = user["id"]
        request.session["username"] = user["username"]
        request.session["authenticated"] = True

        return RedirectResponse(url=next_url, status_code=303)

    @get("/logout")
    async def logout(self, request: Request) -> RedirectResponse:
        """Clear session and redirect to home"""
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)
```

### Phase 4: Template Integration (1-2 hours)

#### 4.1 Update Base Template

**Update `ui/templates/layouts/base.html`:**

```html
<!doctype html>
<html lang="en" data-bs-theme="light">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{ title }} - Mario's Pizzeria</title>
    <link rel="icon" href="/static/favicon.ico" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" />
    <link rel="stylesheet" href="/static/dist/main.css" />
    {% block head %}{% endblock %}
  </head>
  <body class="bg-light text-dark">
    <header>
      <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
          <a class="navbar-brand" href="/"> 🍕 Mario's Pizzeria </a>
          <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
          </button>
          <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto">
              <li class="nav-item">
                <a class="nav-link {% if active_page == 'home' %}active{% endif %}" href="/">Home</a>
              </li>
              <li class="nav-item">
                <a class="nav-link {% if active_page == 'menu' %}active{% endif %}" href="/menu">Menu</a>
              </li>
              {% if authenticated %}
              <li class="nav-item">
                <a class="nav-link {% if active_page == 'orders' %}active{% endif %}" href="/orders">My Orders</a>
              </li>
              {% endif %}
            </ul>
            <div class="d-flex align-items-center">
              <span class="navbar-text me-3 text-white">
                <i class="bi bi-person-fill"></i> {{ username if authenticated else 'Guest' }}
              </span>
              {% if authenticated %}
              <a href="/auth/logout" class="btn btn-outline-light btn-sm">Logout</a>
              {% else %}
              <a href="/auth/login" class="btn btn-outline-light btn-sm">Login</a>
              {% endif %}
            </div>
          </div>
        </div>
      </nav>
    </header>

    <main class="container py-4">{% block content %}{% endblock %}</main>

    <footer class="footer bg-dark text-light py-3 mt-auto">
      <div class="container text-center">
        <p class="mb-0">© 2025 Mario's Pizzeria - v{{ app_version }}</p>
      </div>
    </footer>

    <script src="/static/dist/app.js"></script>
    {% block scripts %}{% endblock %}
  </body>
</html>
```

#### 4.2 Create Login Template

**Create `ui/templates/auth/login.html`:**

```html
{% extends "layouts/base.html" %} {% block content %}
<div class="row justify-content-center mt-5">
  <div class="col-md-6 col-lg-4">
    <div class="card shadow">
      <div class="card-body">
        <h2 class="card-title text-center mb-4">🍕 Login</h2>

        {% if error %}
        <div class="alert alert-danger" role="alert">{{ error }}</div>
        {% endif %}

        <form method="POST" action="/auth/login">
          <div class="mb-3">
            <label for="username" class="form-label">Username</label>
            <input type="text" class="form-control" id="username" name="username" required autofocus />
          </div>

          <div class="mb-3">
            <label for="password" class="form-label">Password</label>
            <input type="password" class="form-control" id="password" name="password" required />
          </div>

          <input type="hidden" name="next_url" value="{{ request.query_params.get('next', '/') }}" />

          <div class="d-grid">
            <button type="submit" class="btn btn-primary">Login</button>
          </div>
        </form>

        <div class="mt-3 text-center">
          <small class="text-muted">Demo: username=demo, password=demo123</small>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

### Phase 5: Update main.py (1 hour)

**Update `main.py` with authentication middleware:**

```python
def create_pizzeria_app(data_dir: Optional[str] = None, port: int = 8000):
    # ... existing setup ...

    # Build service provider
    service_provider = builder.services.build()

    # Create main app
    from fastapi import FastAPI
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from starlette.middleware.sessions import SessionMiddleware
    from fastapi.templating import Jinja2Templates

    app = FastAPI(
        title="Mario's Pizzeria",
        description="Complete pizza ordering and management system",
        version="1.0.0",
        debug=True,
    )
    app.state.services = service_provider

    # Create API app (JWT authentication)
    api_app = FastAPI(
        title="Mario's Pizzeria API",
        description="REST API for external integrations",
        version="1.0.0",
        docs_url="/docs",
        debug=True,
    )
    api_app.state.services = service_provider

    # Register API controllers (including auth)
    builder.add_controllers(["api.controllers"], app=api_app)
    builder.add_exception_handling(api_app)

    # Create UI app (session authentication)
    ui_app = FastAPI(
        title="Mario's Pizzeria UI",
        description="Web interface for customers",
        version="1.0.0",
        docs_url=None,
        debug=True,
    )
    ui_app.state.services = service_provider

    # Add session middleware to UI app
    from application.settings import app_settings
    ui_app.add_middleware(
        SessionMiddleware,
        secret_key=app_settings.session_secret_key,
        max_age=app_settings.session_max_age,
        session_cookie="mario_session",
        https_only=not app_settings.debug,
        same_site="lax",
    )

    # Configure templates for UI
    ui_app.state.templates = Jinja2Templates(
        directory=str(Path(__file__).parent / "ui" / "templates")
    )

    # Mount static files
    static_directory = Path(__file__).parent / "static"
    ui_app.mount("/static", StaticFiles(directory=str(static_directory)), name="static")

    # Register UI controllers
    builder.add_controllers(["ui.controllers"], app=ui_app)

    # Mount apps
    app.mount("/api", api_app, name="api")
    app.mount("/", ui_app, name="ui")  # UI at root

    # Health check on main app
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": datetime.datetime.now(datetime.timezone.utc)}

    return app
```

## 🚀 Deployment Workflow

### Development

```bash
# Terminal 1: Run Parcel in watch mode
cd samples/mario-pizzeria/ui
npm run dev

# Terminal 2: Run FastAPI application
cd samples/mario-pizzeria
python main.py
```

### Production Build

```bash
# Build UI assets
cd samples/mario-pizzeria/ui
npm run build

# Run FastAPI (serves pre-built assets)
cd samples/mario-pizzeria
python main.py
```

### Docker (Future)

```dockerfile
# Build stage for UI
FROM node:18 AS ui-builder
WORKDIR /app/ui
COPY ui/package*.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# Python app stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=ui-builder /app/static/dist ./static/dist
COPY . .
RUN pip install poetry && poetry install --no-dev
CMD ["poetry", "run", "python", "main.py"]
```

## 📝 Summary

### Clear Boundaries

**UI App (`/`)**

- **Purpose**: Customer-facing web interface
- **Auth**: Session cookies (HttpOnly, Secure in prod)
- **Responses**: HTML (Jinja2 templates)
- **Endpoints**: `/`, `/menu`, `/orders`, `/auth/login`, `/auth/logout`
- **Middleware**: SessionMiddleware
- **Assets**: Parcel-built JS/CSS from `/static/dist/`

**API App (`/api/`)**

- **Purpose**: External integrations, mobile apps
- **Auth**: JWT Bearer tokens
- **Responses**: JSON only
- **Endpoints**: `/api/auth/token`, `/api/pizzas`, `/api/orders`
- **Middleware**: JWT validation (custom or using FastAPI dependencies)
- **Docs**: `/api/docs` (Swagger UI)

### Security Best Practices

1. **UI Sessions**

   - HttpOnly cookies (prevent XSS)
   - Secure flag in production (HTTPS only)
   - SameSite=Lax (CSRF protection)
   - Short max_age (1 hour)

2. **API JWT**

   - Short expiration (1 hour)
   - Refresh tokens for long-lived sessions
   - Verify signature on every request
   - Include minimal claims

3. **Secrets Management**
   - Environment variables for production
   - Strong random keys (32+ characters)
   - Different keys for session vs JWT
   - Rotate keys periodically

### Next Steps

1. ✅ Phase 1: Build setup (you've started this)
2. ⏭️ Phase 2: Auth infrastructure
3. ⏭️ Phase 3: Auth endpoints
4. ⏭️ Phase 4: Templates
5. ⏭️ Phase 5: Integration

Would you like me to help implement any specific phase?
