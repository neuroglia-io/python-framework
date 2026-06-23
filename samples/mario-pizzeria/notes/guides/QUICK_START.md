# Mario's Pizzeria - Quick Start Guide

## 🎯 Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     Main FastAPI App                        │
│                    (Host Container)                         │
└─────────────────────────────────────────────────────────────┘
                    │                    │
      ┌─────────────┴──────┐  ┌─────────┴──────────┐
      │    UI App (/)      │  │   API App (/api)   │
      │  Session Cookies   │  │    JWT Tokens      │
      └────────────────────┘  └────────────────────┘
             │                         │
    ┌────────┴────────┐       ┌────────┴────────┐
    │  Jinja2 HTML    │       │   JSON Only     │
    │  Static Assets  │       │   OpenAPI Docs  │
    │  /menu, /orders │       │   /pizzas, ...  │
    └─────────────────┘       └─────────────────┘
```

## 🚀 Current Status

### ✅ What's Working

- ✅ Multi-app architecture (main, api_app, ui_app)
- ✅ Parcel build setup (`ui/package.json`)
- ✅ Bootstrap selective imports
- ✅ CQRS handlers and domain logic
- ✅ File-based repositories
- ✅ Dependency injection

### ⚠️ What Needs Work

- ⚠️ Session middleware not configured
- ⚠️ JWT authentication not implemented
- ⚠️ Parcel builds not integrated
- ⚠️ Templates reference wrong project
- ⚠️ Mixed static/template serving

## 🔧 Quick Setup

### 1. Install Dependencies

```bash
# Python dependencies
cd samples/mario-pizzeria
poetry install

# Node dependencies for UI build
cd ui
npm install
```

### 2. Run in Development

```bash
# Terminal 1: Build UI assets (watch mode)
cd samples/mario-pizzeria/ui
npm run dev

# Terminal 2: Run FastAPI app
cd samples/mario-pizzeria
python main.py
```

### 3. Access the Application

- **UI**: http://localhost:8000/
- **API Docs**: http://localhost:8000/api/docs
- **Health**: http://localhost:8000/health

## 📋 Implementation Checklist

Follow `IMPLEMENTATION_PLAN.md` for detailed steps:

- [ ] **Phase 1**: Build Setup (1-2 hours)

  - [ ] Configure Parcel entry points
  - [ ] Create app.js and main.scss
  - [ ] Update .gitignore
  - [ ] Test build pipeline

- [ ] **Phase 2**: Auth Infrastructure (2-3 hours)

  - [ ] Create application/settings.py
  - [ ] Create AuthService
  - [ ] Add JWT middleware
  - [ ] Add session middleware

- [ ] **Phase 3**: Auth Endpoints (2-3 hours)

  - [ ] Create api/controllers/auth_controller.py (JWT)
  - [ ] Create ui/controllers/auth_controller.py (sessions)
  - [ ] Test login/logout flows

- [ ] **Phase 4**: Template Integration (1-2 hours)

  - [ ] Update base.html
  - [ ] Create login.html
  - [ ] Update home_controller.py
  - [ ] Test UI rendering

- [ ] **Phase 5**: main.py Updates (1 hour)
  - [ ] Add SessionMiddleware to ui_app
  - [ ] Configure Jinja2Templates
  - [ ] Register auth controllers
  - [ ] Test end-to-end

## 🎨 Key Differences: UI vs API

### UI App (Customer-Facing Web)

**Authentication:**

```python
# Login creates session cookie
request.session["user_id"] = user["id"]
request.session["authenticated"] = True

# Middleware automatically validates session
# No headers needed in browser requests
```

**Endpoints:**

- `GET /` → Renders home.html
- `GET /menu` → Renders menu.html
- `POST /auth/login` → Form submission, sets session cookie
- `GET /auth/logout` → Clears session, redirects

**Response Format:**

```python
return request.app.state.templates.TemplateResponse(
    "home/index.html",
    {"request": request, "username": username}
)
```

### API App (External Integrations)

**Authentication:**

```python
# Client sends JWT in header
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

# Middleware validates JWT and injects user
request.state.user = {"sub": "user-id", "username": "demo"}
```

**Endpoints:**

- `POST /api/auth/token` → Returns JWT token
- `GET /api/pizzas` → Returns JSON list
- `POST /api/orders` → Accepts JSON, returns JSON
- `GET /api/docs` → Swagger UI

**Response Format:**

```python
return {
    "id": "123",
    "name": "Margherita",
    "price": 12.99
}
```

## 🔐 Security Model

### UI (Session Cookies)

```python
# Automatic CSRF protection via SameSite
SessionMiddleware(
    secret_key="strong-secret",
    session_cookie="mario_session",
    https_only=True,  # Production only
    same_site="lax",   # CSRF protection
    max_age=3600       # 1 hour
)
```

### API (JWT Tokens)

```python
# Stateless tokens, verified on each request
token = jwt.encode({
    "sub": user_id,
    "exp": datetime.now() + timedelta(hours=1)
}, secret_key, algorithm="HS256")

# Client includes in every request:
# Authorization: Bearer {token}
```

## 🐛 Common Issues

### Issue: "Session not found"

**Cause**: SessionMiddleware not added to ui_app
**Fix**: See Phase 5 in IMPLEMENTATION_PLAN.md

### Issue: "401 Unauthorized on API"

**Cause**: Missing or invalid JWT token
**Fix**: First call `POST /api/auth/token`, then use returned token

### Issue: "Static assets 404"

**Cause**: Parcel build not run
**Fix**: Run `cd ui && npm run build`

### Issue: "Template not found"

**Cause**: Templates not configured
**Fix**: Add `Jinja2Templates` to ui_app.state

## 📚 Next Steps

1. Read `IMPLEMENTATION_PLAN.md` for detailed architecture
2. Start with Phase 1 (Build Setup) if you haven't already
3. Test each phase before moving to the next
4. Update this checklist as you complete phases

## 🤝 Need Help?

The implementation plan provides:

- Complete code examples for each phase
- Security best practices
- Deployment workflows
- Docker configuration

Start with Phase 1 and work through systematically!
