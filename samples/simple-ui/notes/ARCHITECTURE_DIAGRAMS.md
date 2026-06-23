# Simple UI Architecture Overview

## Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Client)                     │
├─────────────────────────────────────────────────────────┤
│  Rendered HTML + CSS + JavaScript                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │ Components │  │  Modules   │  │   Styles   │       │
│  │ (Jinja2)   │  │   (ES6)    │  │   (SASS)   │       │
│  └────────────┘  └────────────┘  └────────────┘       │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP/HTTPS
                          ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Application Server                  │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌──────────────────────┐    │
│  │   UI Sub-App (/)    │  │  API Sub-App (/api)  │    │
│  ├─────────────────────┤  ├──────────────────────┤    │
│  │ - UIController      │  │ - AuthController     │    │
│  │ - UIAuthController  │  │ - TasksController    │    │
│  │ - Jinja2 Templates  │  │ - JWT Auth           │    │
│  │ - Session Auth      │  │ - JSON Responses     │    │
│  │ - Static Files      │  │ - OpenAPI Docs       │    │
│  └─────────────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ Service Layer
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Application Layer (CQRS)                    │
├─────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Commands     │  │   Queries   │  │  Handlers   │ │
│  │  - CreateTask  │  │ - GetTasks  │  │  - Mediator │ │
│  │  - UpdateTask  │  │ - GetTask   │  │  - Mapper   │ │
│  └────────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ Repository Pattern
                          ▼
┌─────────────────────────────────────────────────────────┐
│               Integration Layer                          │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │ InMemoryRepository   │  │   AuthService          │  │
│  │  - TaskRepository    │  │  - Keycloak Auth       │  │
│  └──────────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Frontend File Flow

```
┌─────────────────────────────────────────────────────────┐
│                  Client Request: GET /                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Routes → UIController.index()                   │
│  Returns: TemplateResponse("index.html")                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Jinja2 Template Engine                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ base.html (layout)                              │   │
│  │  ├─ components/navbar.html                      │   │
│  │  ├─ components/login_form.html                  │   │
│  │  ├─ components/tasks_section.html               │   │
│  │  ├─ modals/create_task_modal.html               │   │
│  │  └─ modals/task_details_modal.html              │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Rendered HTML with References                           │
│  <link href="/static/dist/styles/main.css">             │
│  <script src="/static/dist/scripts/main.js">            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Browser Requests Static Assets                          │
│  GET /static/dist/styles/main.css  → Parcel compiled    │
│  GET /static/dist/scripts/main.js  → Parcel bundled     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  JavaScript Modules Load                                 │
│  main.js → imports modules/auth.js                       │
│         → imports modules/tasks.js                       │
│         → imports modules/ui.js                          │
│         → imports modules/utils.js                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Application Initializes                                 │
│  1. checkAuth() → GET /auth/me                           │
│  2. Setup event listeners                                │
│  3. Show login or tasks section                          │
└─────────────────────────────────────────────────────────┘
```

## JavaScript Module Dependencies

```
main.js (Entry Point)
  │
  ├─→ modules/auth.js
  │     └─→ Exports: checkAuth(), login(), logout()
  │
  ├─→ modules/tasks.js
  │     ├─→ Imports: getAuthToken() from auth.js
  │     └─→ Exports: loadTasks(), createTask(), etc.
  │
  ├─→ modules/ui.js
  │     ├─→ Imports: escapeHtml() from utils.js
  │     └─→ Exports: showLoginSection(), displayTasks(), etc.
  │
  └─→ modules/utils.js
        └─→ Exports: escapeHtml(), debounce(), etc.
```

## SASS Compilation Flow

```
┌─────────────────────────────────────────────────────────┐
│  Source: src/styles/main.scss                            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Parcel SASS Processor                                   │
│  1. @import "_variables.scss"                            │
│  2. @import "~bootstrap/scss/bootstrap"                  │
│  3. @import "components/_navbar.scss"                    │
│  4. @import "components/_login.scss"                     │
│  5. @import "components/_tasks.scss"                     │
│  6. @import "components/_spinner.scss"                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Compiled CSS → static/dist/styles/main.css              │
│  - All SASS variables resolved                           │
│  - All @imports inlined                                  │
│  - Bootstrap styles included                             │
│  - Custom component styles appended                      │
└─────────────────────────────────────────────────────────┘
```

## Authentication Flow

```
┌─────────────────────────────────────────────────────────┐
│  User enters credentials in login form                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  JavaScript: login(username, password)                   │
│  → POST /auth/login (FormData)                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI: UIAuthController.login()                       │
│  → AuthService.authenticate()                            │
│    → Keycloak authentication                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Success: Returns JWT token + user info                  │
│  → Creates session cookie                                │
│  → Returns JSON with token                               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  JavaScript: Stores token in localStorage                │
│  → Shows tasks section                                   │
│  → Loads tasks with Bearer token                         │
└─────────────────────────────────────────────────────────┘
```

## Task Loading Flow

```
┌─────────────────────────────────────────────────────────┐
│  User logged in → JavaScript: loadTasks()                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  GET /api/tasks/                                         │
│  Headers: Authorization: Bearer <token>                  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI: TasksController.get_tasks()                    │
│  → Validates JWT token                                   │
│  → Executes GetTasksQuery                                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Mediator → GetTasksHandler                              │
│  → TaskRepository.get_all_async()                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Returns: List[Task] as JSON                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  JavaScript: displayTasks(tasks)                         │
│  → Renders task cards in grid                            │
│  → Escapes HTML for security                             │
└─────────────────────────────────────────────────────────┘
```

## Build & Deployment Flow

```
┌──────────────────────────────────────────────────────────┐
│  Developer edits source files                            │
│  - ui/templates/*.html                                   │
│  - ui/src/scripts/**/*.js                                │
│  - ui/src/styles/**/*.scss                               │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Parcel Watcher (in Docker)                              │
│  Detects file changes                                    │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Parcel Build Process                                    │
│  1. Transpile JavaScript (ES6 → ES5)                     │
│  2. Compile SASS → CSS                                   │
│  3. Bundle all modules                                   │
│  4. Generate source maps                                 │
│  5. Output to static/dist/                               │
└──────────────────────────────────────────────-───────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Built Assets Ready                                      │
│  - static/dist/scripts/main.js (~260KB)                  │
│  - static/dist/styles/main.css (~264KB)                  │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI serves static files                             │
│  StaticFiles mount at /static                            │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Browser requests and caches assets                      │
│  (with ETags for cache validation)                       │
└──────────────────────────────────────────────────────────┘
```
